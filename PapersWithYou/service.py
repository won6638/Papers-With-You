"""Collection engine independent of terminal input."""
from pathlib import Path
import hashlib
import json
import os
import time
from pypdf import PdfReader
from .model import Paper, atomic_json
from .net import TransferError
from .store import now


def validate_pdf(path):
    path=Path(path)
    with path.open('rb') as f:
        if f.read(5) != b'%PDF-': raise TransferError('not_pdf')
        f.seek(0)
        try:
            reader=PdfReader(f,strict=True)
            if reader.is_encrypted: raise TransferError('encrypted_pdf')
            if not len(reader.pages): raise TransferError('empty_pdf')
            for page in reader.pages:
                # Resolve page trees and content streams; does not render or execute PDF code.
                contents=page.get_contents()
                if contents is not None: contents.get_data()
            pages=len(reader.pages)
        except TransferError: raise
        except Exception as e: raise TransferError('invalid_pdf') from e
    sha=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(65536),b''): sha.update(block)
    return sha.hexdigest(),path.stat().st_size,pages


def validate_paper(paper):
    # Reuse provider parser validation to protect local state corruption from path traversal.
    from .model import ARXIV_ID
    if paper.provider!='arxiv' or not ARXIV_ID.fullmatch(paper.paper_id+paper.version):
        raise TransferError('invalid_paper_id')
    if paper.pdf_url!='https://arxiv.org/pdf/'+paper.paper_id+paper.version:
        raise TransferError('invalid_paper_url')


def collect(store,run,client,profile):
    failures=0
    client.total_limit=profile.max_total_mb*1024*1024
    for job in store.jobs(run.id):
        if not job['selected']: continue
        paper=Paper(**json.loads(job['metadata']))
        validate_paper(paper)
        directory=store.root/'papers'/paper.stem
        directory.mkdir(parents=True,exist_ok=True)
        target=directory/'paper.pdf'
        part=directory/'paper.pdf.part'
        attempted=False
        started=time.monotonic()
        try:
            old=store.artifact(paper.key)
            if target.exists():
                try:
                    with run.stage('validation',paper_key=paper.key): sha,size,pages=validate_pdf(target)
                    if old and old['sha256']!=sha: raise TransferError('hash_mismatch')
                    outcome='cached' if old else 'recovered'
                except TransferError:
                    # Re-fetch; the old file is kept until its replacement validates.
                    outcome=None
            else: outcome=None
            if not outcome:
                if client.bytes_received>=client.total_limit:
                    raise TransferError('run_byte_limit')
                attempted=True
                store.state(run.id,paper.key,'downloading')
                run.emit('download_started',paper_key=paper.key)
                client.fetch(paper.pdf_url,part,profile.max_file_mb*1024*1024,'download')
                with run.stage('validation',paper_key=paper.key): sha,size,pages=validate_pdf(part)
                os.replace(part,target)
                outcome='complete'
            metadata={**paper.data(),'schema_version':1,'file':{'name':'paper.pdf','sha256':sha,'bytes':size,'pages':pages},
                      'validated_at':now(),'identity_status':'provider_link_only',
                      'license_status':'unknown' if not paper.license_url else 'reported',
                      'note':'Structural validation is not a malware scan or full-text identity verification.'}
            atomic_json(directory/'metadata.json',metadata)
            store.save_artifact(paper.key,target,sha,size)
            store.state(run.id,paper.key,outcome)
            run.emit('paper_result',paper_key=paper.key,outcome=outcome,attempted=attempted,duration_s=time.monotonic()-started)
        except (TransferError,OSError) as e:
            failures+=1
            reason=e.reason if isinstance(e,TransferError) else 'filesystem_error'
            store.state(run.id,paper.key,'failed',reason)
            run.emit('paper_result',paper_key=paper.key,outcome='failed',reason=reason,attempted=attempted,duration_s=time.monotonic()-started)
        finally:
            part.unlink(missing_ok=True)
    return failures
