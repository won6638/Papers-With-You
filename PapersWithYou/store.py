"""Local durable jobs and private execution telemetry."""
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
import csv
import json
import sqlite3
import hashlib
import platform
import importlib.metadata
import time
import uuid
from . import __version__
from .model import atomic_json


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self,root):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.root/'state.sqlite3')
        self.db.row_factory=sqlite3.Row
        self.db.executescript('''
          PRAGMA foreign_keys=ON;
          CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY,kind TEXT,started TEXT,finished TEXT,status TEXT,profile_hash TEXT);
          CREATE TABLE IF NOT EXISTS papers(key TEXT PRIMARY KEY,metadata TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS jobs(run_id TEXT REFERENCES runs(id),key TEXT REFERENCES papers(key),position INTEGER,
            selected INTEGER DEFAULT 0,status TEXT DEFAULT 'candidate',reason TEXT,
            PRIMARY KEY(run_id,key));
          CREATE TABLE IF NOT EXISTS artifacts(key TEXT PRIMARY KEY REFERENCES papers(key),path TEXT,sha256 TEXT,bytes INTEGER,validated_at TEXT);
          PRAGMA user_version=1;
        ''')
        self.db.commit()

    def close(self): self.db.close()

    def add(self,run_id,papers):
        with self.db:
            for pos,p in enumerate(papers,1):
                self.db.execute('INSERT INTO papers VALUES(?,?) ON CONFLICT(key) DO UPDATE SET metadata=excluded.metadata',(p.key,json.dumps(p.data(),ensure_ascii=False)))
                self.db.execute('INSERT INTO jobs(run_id,key,position) VALUES(?,?,?)',(run_id,p.key,pos))

    def jobs(self,run_id):
        return self.db.execute('SELECT j.*,p.metadata FROM jobs j JOIN papers p USING(key) WHERE run_id=? ORDER BY position',(run_id,)).fetchall()

    def select(self,run_id,positions):
        with self.db:
            for pos in positions:
                self.db.execute("UPDATE jobs SET selected=1,status=CASE WHEN status='candidate' THEN 'pending' ELSE status END WHERE run_id=? AND position=?",(run_id,pos))

    def state(self,run_id,key,status,reason=None):
        with self.db: self.db.execute('UPDATE jobs SET status=?,reason=? WHERE run_id=? AND key=?',(status,reason,run_id,key))

    def artifact(self,key):
        return self.db.execute('SELECT * FROM artifacts WHERE key=?',(key,)).fetchone()

    def save_artifact(self,key,path,sha,size):
        with self.db:
            self.db.execute('INSERT INTO artifacts VALUES(?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET path=excluded.path,sha256=excluded.sha256,bytes=excluded.bytes,validated_at=excluded.validated_at',(key,str(path.relative_to(self.root)),sha,size,now()))

    def export(self,run_id):
        directory=self.root/'runs'/run_id
        directory.mkdir(parents=True,exist_ok=True)
        rows=self.jobs(run_id)
        with (directory/'papers.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f)
            writer.writerow(['position','key','title','selected','status','reason'])
            for row in rows:
                title=json.loads(row['metadata'])['title']
                if title.startswith(('=','+','-','@','\t','\r')): title="'"+title
                writer.writerow([row['position'],row['key'],title,row['selected'],row['status'],row['reason'] or ''])


class Run:
    def __init__(self,store,kind,profile_hash='',existing=None):
        self.store=store
        self.id=existing or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S-')+uuid.uuid4().hex[:8]
        self.session=uuid.uuid4().hex[:8]
        self.directory=store.root/'runs'/self.id
        self.started=time.monotonic()
        self.records=[]
        self.kind=kind
        if existing:
            if not store.db.execute('SELECT 1 FROM runs WHERE id=?',(existing,)).fetchone():
                raise ValueError('Unknown run ID')
        else:
            with store.db: store.db.execute('INSERT INTO runs VALUES(?,?,?,?,?,?)',(self.id,kind,now(),None,'running',profile_hash))
        self.directory.mkdir(parents=True,exist_ok=True)
        source_hash=hashlib.sha256()
        for source in sorted(Path(__file__).parent.glob('*.py')):
            source_hash.update(source.name.encode()); source_hash.update(source.read_bytes())
        self.emit('session_started',kind=kind,software_version=__version__,profile_hash=profile_hash,
                  source_sha256=source_hash.hexdigest(),python=platform.python_version(),
                  platform=platform.system(),pypdf=importlib.metadata.version('pypdf'))

    def emit(self,event,**values):
        record=dict(time_utc=now(),run_id=self.id,session_id=self.session,event=event,**values)
        self.records.append(record)
        with (self.directory/'events.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps(record,ensure_ascii=False)+'\n'); f.flush()

    @contextmanager
    def stage(self,name,**fields):
        start=time.monotonic()
        try: yield
        finally: self.emit('stage',stage=name,duration_s=time.monotonic()-start,**fields)

    def finish(self,status):
        elapsed=time.monotonic()-self.started
        self.emit('session_finished',status=status,duration_s=elapsed)
        with self.store.db:
            self.store.db.execute('UPDATE runs SET finished=?,status=? WHERE id=?',(now(),status,self.id))
        rows=self.store.jobs(self.id)
        counts={}
        for row in rows: counts[row['status']]=counts.get(row['status'],0)+1
        requests=[r for r in self.records if r['event']=='request']
        timing=sorted(r['duration_s'] for r in requests)
        selected=sum(r['selected'] for r in rows)
        valid=sum(r['selected'] and r['status'] in ('complete','cached','recovered') for r in rows)
        attempts=[r for r in self.records if r['event']=='paper_result' and r.get('attempted')]
        metrics={
            'schema_version':1,'run_id':self.id,'session_id':self.session,'status':status,
            'software_version':__version__,'elapsed_s':elapsed,'candidate_count':len(rows),
            'selected_count':selected,'valid_selected_count':valid,
            'acquisition_ratio':valid/selected if selected else None,'job_status_counts':counts,
            'request_count':len(requests),'bytes_received':sum(r.get('bytes',0) for r in requests),
            'request_p50_s':timing[len(timing)//2] if timing else None,
            'request_p95_s':timing[min(len(timing)-1,int((len(timing)-1)*.95+.5))] if timing else None,
            'rate_wait_s':sum(r['duration_s'] for r in self.records if r['event']=='rate_wait'),
            'retry_wait_s':sum(r['duration_s'] for r in self.records if r['event']=='retry_wait'),
            'download_attempted_papers':len(attempts),
            'download_validated_papers':sum(r.get('outcome')=='complete' for r in attempts),
            'download_validation_ratio':sum(r.get('outcome')=='complete' for r in attempts)/len(attempts) if attempts else None,
            'scope':'job states are current for this run; timings/attempts are this session only',
        }
        atomic_json(self.directory/f'summary-{self.session}.json',metrics)
        atomic_json(self.directory/'summary.json',metrics)
        self.store.export(self.id)
        return metrics
