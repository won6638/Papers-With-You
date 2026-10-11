"""Bilingual local CLI. Profiles can later be created by a desktop questionnaire."""
import argparse
from dataclasses import asdict
from pathlib import Path
import json
import sys
from . import __version__
from .arxiv import search
from .model import Profile, atomic_json, digest
from .net import Client, TransferError, file_lock
from .service import collect
from .store import Store, Run


def ask(label,default=''):
    suffix=f' [{default}]' if default else ''
    return input(label+suffix+': ').strip() or default


def wizard(path):
    if path.exists() and ask('Overwrite profile? / 설정을 덮어쓸까? y/N','n').lower()!='y':
        return 0
    print('Papers With You — initial profile / 초기 설정')
    print('Free description and purpose are stored only; no LLM or semantic ranking yet.\n자유 설명과 목적은 저장만 하며 아직 의미 검색에 사용하지 않아.')
    print('Use English query phrases; comma separates phrases. / 검색 구문은 영어로, 쉼표로 구분해줘.')
    split=lambda value:[s.strip() for s in value.split(',') if s.strip()]
    profile=Profile(
        categories=split(ask('arXiv categories / 분야 코드','cs.AI,cs.LG')),
        purpose=ask('Purpose / 목적','research'),
        keywords=split(ask('Required phrases (AND) / 필수 구문')),
        exclude=split(ask('Excluded phrases / 제외 구문')),
        description=ask('Description (local only) / 자유 설명 (로컬 저장)'),
        since=ask('First submission date from YYYY-MM-DD / 최초 제출일 시작'),
        until=ask('First submission date through YYYY-MM-DD / 최초 제출일 끝'),
        max_results=int(ask('Maximum papers 1..100 / 최대 편수','20')),
        output_dir=ask('Output folder (blank: downloads beside launcher) / 저장 폴더'),
        contact=ask('Optional user contact for User-Agent / 요청 식별용 연락처 (선택)'),
    ).validate()
    profile.save(path)
    print(f'Saved / 저장: {path}')
    return 0


def positions(text,count):
    if text.strip().lower()=='all': return list(range(1,count+1))
    if not text.strip(): return []
    result=set()
    for item in text.split(','):
        item=item.strip()
        if '-' in item:
            a,b=map(int,item.split('-'))
            if not 1<=a<=b<=count: raise ValueError('Selection out of range')
            result.update(range(a,b+1))
        else:
            v=int(item)
            if not 1<=v<=count: raise ValueError('Selection out of range')
            result.add(v)
    return sorted(result)


def confirm(store,run,args,profile):
    jobs=store.jobs(run.id)
    if not jobs: return []
    print('\nCandidates / 후보 (most recently updated / 최근 수정 순):')
    for j in jobs:
        p=json.loads(j['metadata'])
        print(f"{j['position']:3}. {p['paper_id']}{p['version']} | {p['title']}")
    if args.select:
        chosen=positions(args.select,len(jobs))
    elif args.yes or profile.auto_download:
        chosen=list(range(1,len(jobs)+1))
    elif not sys.stdin.isatty():
        print('No interactive terminal: preview only. Use --select and --yes to authorize.\n비대화형 실행: 목록만 저장. 다운로드하려면 --select 및 --yes를 사용해줘.')
        return []
    else:
        while True:
            try:
                chosen=positions(ask('Select 1,3-5 / all; blank cancels / 번호 선택'),len(jobs)); break
            except ValueError:
                print('Invalid selection / 선택 범위를 확인해줘.')
    if chosen and not(args.yes or profile.auto_download):
        if not sys.stdin.isatty() or ask(f'Download {len(chosen)} papers? / 다운로드할까? y/N','n').lower()!='y':
            return []
    return chosen


def parser(app_dir):
    p=argparse.ArgumentParser(description='Papers With You — Research Paper Collector')
    p.add_argument('--version',action='version',version=__version__)
    subs=p.add_subparsers(dest='command',required=True)
    q=subs.add_parser('init',help='Questionnaire / 설문 설정')
    q.add_argument('--profile',type=Path,default=app_dir/'profiles'/'default.json')
    for name in ('search','run','sync'):
        q=subs.add_parser(name,help={'search':'Preview only / 목록만','run':'Search and choose / 검색 후 선택','sync':'Bounded rescan and choose / 제한된 재검색 후 선택'}[name])
        q.add_argument('--profile',type=Path,default=app_dir/'profiles'/'default.json')
        q.add_argument('--output',type=Path)
        q.add_argument('--select',default='')
        q.add_argument('--yes',action='store_true',help='Approve selected/all candidates for this invocation / 이번 실행 승인')
    q=subs.add_parser('resume',help='Resume an existing run / 기존 실행 이어받기')
    q.add_argument('--run-id',required=True)
    q.add_argument('--output',type=Path)
    q.add_argument('--select',default='')
    q.add_argument('--yes',action='store_true')
    q=subs.add_parser('status',help='Recent local runs / 최근 실행 상태')
    q.add_argument('--output',type=Path)
    return p


def main(argv=None,app_dir=None):
    # Legacy redirected Windows streams may not encode Korean output.
    # Preserve the selected encoding but escape unsupported characters safely.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    app_dir=Path(app_dir or Path(__file__).resolve().parent.parent)
    args=parser(app_dir).parse_args(argv)
    store=None
    run=None
    try:
        if args.command=='init': return wizard(args.profile)
        if args.command in ('run','search','sync'):
            profile=Profile.load(args.profile)
            # Relative output paths resolve against the profile location, not the shell cwd.
            configured=Path(profile.output_dir).expanduser() if profile.output_dir else app_dir/'downloads'
            if profile.output_dir and not configured.is_absolute(): configured=args.profile.resolve().parent/configured
            output=Path(args.output).expanduser() if args.output else configured
        else:
            output=Path(args.output).expanduser() if args.output else app_dir/'downloads'
            if not (output/'state.sqlite3').exists():
                raise ValueError('No existing store at this output directory')
        output=output.resolve()
        with file_lock(output/'.store.lock'):
            store=Store(output)
            if args.command=='status':
                rows=store.db.execute('SELECT id,kind,status,started FROM runs ORDER BY started DESC LIMIT 20').fetchall()
                for row in rows: print(' | '.join(str(x) for x in row))
                return 0
            if args.command=='resume':
                # Resolve only IDs recorded in DB; never use arbitrary user paths.
                found=store.db.execute('SELECT id FROM runs WHERE id=?',(args.run_id,)).fetchone()
                if not found: raise ValueError('Unknown run ID')
                profile=Profile.load(output/'runs'/found['id']/'profile.json')
                run=Run(store,'resume',digest(asdict(profile)),existing=found['id'])
            else:
                run=Run(store,args.command,digest(asdict(profile)))
                profile.save(run.directory/'profile.json')
            print(f'Run / 실행: {run.id}')
            client=Client(run.emit,profile.contact)
            if args.command!='resume':
                with run.stage('search'):
                    papers,total=search(profile,client,run.directory,run.emit)
                store.add(run.id,papers)
                atomic_json(run.directory/'candidates.json',{
                    'schema_version':1,'provider':'arxiv','reported_total':total,
                    'bounded_rescan':True,'potentially_truncated':total>len(papers),
                    'papers':[p.data() for p in papers]})
                print(f'Candidates {len(papers)} / reported {total}. Bounded scan; no completeness claim.\n후보 {len(papers)}편 / 보고된 전체 {total}편. 전체 수집을 보장하지 않는 제한된 검색이야.')
                if args.command=='search':
                    for i,paper in enumerate(papers,1): print(f'{i:3}. {paper.paper_id}{paper.version} | {paper.title}')
                    run.finish('preview'); return 0
            existing=[j for j in store.jobs(run.id) if j['selected']]
            if args.command=='resume' and existing and not args.select:
                print(f'Resuming {len(existing)} previously approved papers / 이전 승인 항목 재개')
            else:
                selected=confirm(store,run,args,profile)
                if not selected:
                    run.finish('preview'); return 0
                store.select(run.id,selected)
            with run.stage('collection'):
                failed=collect(store,run,client,profile)
            report=run.finish('partial' if failed else 'complete')
            print(json.dumps({k:report[k] for k in ('status','selected_count','valid_selected_count','elapsed_s','download_validation_ratio')},ensure_ascii=False,indent=2))
            print(f'Logs / 기록: {run.directory}')
            return 2 if failed else 0
    except KeyboardInterrupt:
        if run: run.finish('interrupted')
        print('Interrupted; resume the run to continue. / 중단됨. resume으로 이어갈 수 있어.',file=sys.stderr)
        return 130
    except (ValueError,TypeError,OSError,TransferError) as e:
        reason=e.reason if isinstance(e,TransferError) else type(e).__name__
        if run:
            run.emit('operation_failed',reason=reason)
            run.finish('failed')
        print(f'Failed / 실패: {reason}. {str(e) if isinstance(e,(ValueError,TypeError)) else "Check logs, network and folder permissions / 로그·네트워크·폴더 권한을 확인해줘."}',file=sys.stderr)
        return 1
    finally:
        if store: store.close()
