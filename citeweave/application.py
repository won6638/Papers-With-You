"""GUI-independent application layer. Synchronous calls; use a GUI worker thread."""
from contextlib import contextmanager
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
import json

from .arxiv import search as arxiv_search
from .model import Profile, atomic_json, digest
from .net import Client, file_lock
from .service import collect
from .store import Store, Run


class _ObservedRun(Run):
    def __init__(self, store, kind, callback, profile_hash='', existing=None):
        self.callback = callback
        super().__init__(store, kind, profile_hash, existing)

    def emit(self, event, **fields):
        super().emit(event, **fields)
        if self.callback:
            try:
                self.callback({'event': event, 'run_id': self.id,
                               'session_id': self.session, **fields})
            except Exception:
                # A UI callback must not invalidate persisted downloads.
                pass


@contextmanager
def _open_store(root):
    with file_lock(root / '.store.lock'):
        db = Store(root)
        try:
            yield db
        finally:
            db.close()


class CiteWeaveApp:
    """UI-independent API; methods return JSON-serializable values.

    The event callback runs on the caller's thread, not the GUI event loop.
    Work against the same store is serialized by the existing file lock.
    """

    def __init__(self, app_dir=None, output_dir=None, on_event=None):
        self.app_dir = Path(app_dir or Path(__file__).resolve().parent.parent).resolve()
        self.output_dir = Path(output_dir).expanduser().resolve() if output_dir is not None else None
        self.on_event = on_event

    def _profile_path(self, path=None):
        return (Path(path).expanduser().resolve() if path is not None
                else self.app_dir / 'profiles' / 'default.json')

    def _profile(self, value):
        if isinstance(value, Profile):
            return value.validate(), None
        if isinstance(value, Mapping):
            return Profile(**dict(value)).validate(), None
        if isinstance(value, (str, Path)):
            source = self._profile_path(value)
            return Profile.load(source), source
        raise TypeError('profile must be Profile, mapping, or JSON path')

    def _root(self, profile=None, profile_path=None, output_dir=None):
        if output_dir is not None:
            return Path(output_dir).expanduser().resolve()
        if self.output_dir is not None:
            return self.output_dir
        if profile is not None and profile.output_dir:
            configured = Path(profile.output_dir).expanduser()
            if not configured.is_absolute():
                configured = (profile_path.parent if profile_path else self.app_dir) / configured
            return configured.resolve()
        return (self.app_dir / 'downloads').resolve()

    @staticmethod
    def _require_run(db, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('run_id must be a nonempty string')
        row = db.db.execute(
            'SELECT id,kind,status,started,finished FROM runs WHERE id=?', (run_id,)
        ).fetchone()
        if row is None:
            raise ValueError('Unknown run ID')
        return row

    @staticmethod
    def _fail(run, exc):
        if run is not None:
            try:
                run.emit('operation_failed', reason=type(exc).__name__)
                run.finish('interrupted' if isinstance(exc, KeyboardInterrupt) else 'failed')
            except Exception:
                pass

    def save_profile(self, profile, path=None):
        """Profile/dict -> {'path': str, 'profile': dict}."""
        validated, _ = self._profile(profile)
        target = self._profile_path(path)
        validated.save(target)
        return {'path': str(target), 'profile': asdict(validated)}

    def load_profile(self, path=None):
        """File path -> profile dict, validated against the existing schema."""
        return asdict(Profile.load(self._profile_path(path)))

    def search(self, profile, *, output_dir=None):
        """Profile/dict/file -> search preview. No PDF downloads or prompts."""
        p, path = self._profile(profile)
        root = self._root(p, path, output_dir)
        with _open_store(root) as db:
            run = None
            try:
                run = _ObservedRun(db, 'search', self.on_event, digest(asdict(p)))
                p.save(run.directory / 'profile.json')
                client = Client(run.emit, p.contact)
                with run.stage('search'):
                    papers, total = arxiv_search(p, client, run.directory, run.emit)
                db.add(run.id, papers)
                atomic_json(run.directory / 'candidates.json', {
                    'schema_version': 1, 'provider': 'arxiv',
                    'reported_total': total, 'bounded_rescan': True,
                    'potentially_truncated': total > len(papers),
                    'papers': [paper.data() for paper in papers]})
                run.finish('preview')
                return {'run_id': run.id, 'output_dir': str(root),
                        'status': 'preview', 'reported_total': total,
                        'potentially_truncated': total > len(papers),
                        'candidates': [{'position': i, **paper.data()}
                                       for i, paper in enumerate(papers, 1)]}
            except BaseException as exc:
                self._fail(run, exc)
                raise

    def download(self, run_id, positions, *, output_dir=None):
        """Approve selected 1-based positions in a search run and download.

        Approval is additive, matching the existing CLI behavior.
        """
        if isinstance(positions, (str, bytes)) or not isinstance(positions, Sequence):
            raise TypeError('positions must be a sequence of 1-based integers')
        if not positions or any(type(n) is not int for n in positions):
            raise ValueError('positions must contain 1-based integers')
        root = self._root(output_dir=output_dir)
        with _open_store(root) as db:
            self._require_run(db, run_id)
            if any(n not in {row['position'] for row in db.jobs(run_id)} for n in positions):
                raise ValueError('Selection out of range')
            p = Profile.load(root / 'runs' / run_id / 'profile.json')
            run = None
            try:
                run = _ObservedRun(db, 'download', self.on_event,
                                   digest(asdict(p)), existing=run_id)
                db.select(run_id, sorted(set(positions)))
                client = Client(run.emit, p.contact)
                with run.stage('collection'):
                    failures = collect(db, run, client, p)
                return self._complete(root, run, failures)
            except BaseException as exc:
                self._fail(run, exc)
                raise

    def resume(self, run_id, *, output_dir=None):
        """Recheck and resume already approved papers; no fresh search."""
        root = self._root(output_dir=output_dir)
        with _open_store(root) as db:
            self._require_run(db, run_id)
            if not any(row['selected'] for row in db.jobs(run_id)):
                raise ValueError('No approved papers in run')
            p = Profile.load(root / 'runs' / run_id / 'profile.json')
            run = None
            try:
                run = _ObservedRun(db, 'resume', self.on_event,
                                   digest(asdict(p)), existing=run_id)
                client = Client(run.emit, p.contact)
                with run.stage('collection'):
                    failures = collect(db, run, client, p)
                return self._complete(root, run, failures)
            except BaseException as exc:
                self._fail(run, exc)
                raise

    @staticmethod
    def _complete(root, run, failures):
        summary = run.finish('partial' if failures else 'complete')
        return {'run_id': run.id, 'session_id': run.session,
                'output_dir': str(root), 'status': summary['status'],
                'summary': summary}

    def list_runs(self, limit=20, *, output_dir=None):
        """List recent runs; return [] if output store does not exist."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('limit must be 1..100')
        root = self._root(output_dir=output_dir)
        if not (root / 'state.sqlite3').is_file():
            return []
        with _open_store(root) as db:
            rows = db.db.execute('SELECT id,kind,status,started,finished FROM runs '
                                 'ORDER BY started DESC LIMIT ?', (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_run(self, run_id, *, output_dir=None):
        """Run details with jobs, parsed paper metadata, existing PDF paths."""
        root = self._root(output_dir=output_dir)
        if not (root / 'state.sqlite3').is_file():
            raise ValueError('Unknown run ID')
        with _open_store(root) as db:
            record = self._require_run(db, run_id)
            jobs = []
            for row in db.jobs(run_id):
                artifact = db.artifact(row['key'])
                pdf_path = None
                if artifact:
                    candidate = root / artifact['path']
                    if candidate.is_file():
                        pdf_path = str(candidate)
                jobs.append({'position': row['position'],
                             'selected': bool(row['selected']),
                             'status': row['status'], 'reason': row['reason'],
                             'paper': json.loads(row['metadata']),
                             'pdf_path': pdf_path})
            return {'run_id': run_id, 'output_dir': str(root),
                    **dict(record), 'jobs': jobs}
