"""UI-independent synchronous application API for Papers With You.

Use in a NiceGUI worker via run.io_bound. No GUI or CLI dependencies.
"""
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from collections.abc import Mapping, Sequence
import json

from .arxiv import search as arxiv_search
from .model import Profile, atomic_json, digest
from .net import Client, file_lock
from .service import collect
from .store import Run, Store


class _ObservedRun(Run):
    def __init__(self, store, kind, callback, profile_hash='', existing=None):
        self._callback = callback
        super().__init__(store, kind, profile_hash, existing)

    def emit(self, event, **values):
        super().emit(event, **values)
        if self._callback is not None:
            try:
                self._callback({'event': event, 'run_id': self.id,
                                'session_id': self.session, **values})
            except Exception:
                # Observation must never make a persisted job fail.
                pass


@contextmanager
def _store(root):
    with file_lock(root / '.store.lock'):
        db = Store(root)
        try:
            yield db
        finally:
            db.close()


class PapersWithYouApp:
    """One instance may be used by a GUI, but calls are synchronous.

    Optional on_event callback runs on the calling worker thread; it must
    marshal updates to the GUI event loop. Do not run concurrent jobs against
    the same output directory: the engine serializes them with a file lock.
    """

    def __init__(self, app_dir=None, output_dir=None, on_event=None):
        self.app_dir = Path(app_dir or Path(__file__).resolve().parent.parent).resolve()
        self.output_dir = Path(output_dir).expanduser().resolve() if output_dir is not None else None
        self.on_event = on_event

    def _profile_path(self, path=None):
        return (Path(path).expanduser().resolve() if path is not None
                else self.app_dir / 'profiles' / 'default.json')

    def _read_profile(self, value):
        if isinstance(value, Profile):
            return value.validate(), None
        if isinstance(value, Mapping):
            return Profile(**dict(value)).validate(), None
        if isinstance(value, (str, Path)):
            source = self._profile_path(value)
            return Profile.load(source), source
        raise TypeError('profile must be a Profile, dict, or JSON path')

    def _root(self, profile=None, profile_path=None, output_dir=None):
        if output_dir is not None:
            return Path(output_dir).expanduser().resolve()
        if self.output_dir is not None:
            return self.output_dir
        if profile is not None and profile.output_dir:
            root = Path(profile.output_dir).expanduser()
            if not root.is_absolute():
                root = (profile_path.parent if profile_path else self.app_dir) / root
            return root.resolve()
        return (self.app_dir / 'downloads').resolve()

    @staticmethod
    def _require_run(db, run_id):
        if not isinstance(run_id, str) or not run_id:
            raise ValueError('run_id must be a nonempty string')
        row = db.db.execute('SELECT id, kind, status, started, finished '
                            'FROM runs WHERE id=?', (run_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown run ID')
        return row

    @staticmethod
    def _handle_failure(run, error):
        if run is not None:
            try:
                run.emit('operation_failed', reason=type(error).__name__)
                run.finish('interrupted' if isinstance(error, KeyboardInterrupt) else 'failed')
            except Exception:
                pass

    def save_profile(self, profile, path=None):
        """Profile/dict -> {'path': str, 'profile': dict}; atomic JSON write."""
        data, _ = self._read_profile(profile)
        target = self._profile_path(path)
        data.save(target)
        return {'path': str(target), 'profile': asdict(data)}

    def load_profile(self, path=None):
        """JSON profile path -> validated dict."""
        return asdict(Profile.load(self._profile_path(path)))

    def search(self, profile, *, output_dir=None):
        """Profile/dict/path -> preview dict. No PDF downloads, no prompts."""
        p, source = self._read_profile(profile)
        root = self._root(p, source, output_dir)
        with _store(root) as db:
            job = None
            try:
                job = _ObservedRun(db, 'search', self.on_event, digest(asdict(p)))
                p.save(job.directory / 'profile.json')
                client = Client(job.emit, p.contact)
                with job.stage('search'):
                    papers, total = arxiv_search(p, client, job.directory, job.emit)
                db.add(job.id, papers)
                atomic_json(job.directory / 'candidates.json', {
                    'schema_version': 1, 'provider': 'arxiv',
                    'reported_total': total, 'bounded_rescan': True,
                    'potentially_truncated': total > len(papers),
                    'papers': [paper.data() for paper in papers],
                })
                job.finish('preview')
                return {
                    'run_id': job.id, 'output_dir': str(root), 'status': 'preview',
                    'reported_total': total, 'potentially_truncated': total > len(papers),
                    'candidates': [{'position': i, **paper.data()}
                                   for i, paper in enumerate(papers, 1)],
                }
            except BaseException as exc:
                self._handle_failure(job, exc)
                raise

    def download(self, run_id, positions, *, output_dir=None):
        """Explicitly approve 1-based candidate positions in an existing run.

        Approval is additive, as with the original CLI. Raises ValueError for
        missing or invalid selections. A valid call may yield partial status.
        """
        if (isinstance(positions, (str, bytes))
                or not isinstance(positions, Sequence)):
            raise TypeError('positions must be a sequence of 1-based integers')
        if not positions or any(type(n) is not int for n in positions):
            raise ValueError('positions must contain 1-based integers')
        root = self._root(output_dir=output_dir)
        with _store(root) as db:
            self._require_run(db, run_id)
            jobs = db.jobs(run_id)
            allowed = {row['position'] for row in jobs}
            if any(n not in allowed for n in positions):
                raise ValueError('Selection out of range')
            p = Profile.load(root / 'runs' / run_id / 'profile.json')
            job = None
            try:
                job = _ObservedRun(db, 'download', self.on_event,
                                   digest(asdict(p)), existing=run_id)
                db.select(run_id, sorted(set(positions)))
                client = Client(job.emit, p.contact)
                with job.stage('collection'):
                    failures = collect(db, job, client, p)
                return self._complete(root, job, failures)
            except BaseException as exc:
                self._handle_failure(job, exc)
                raise

    def resume(self, run_id, *, output_dir=None):
        """Resume previously selected papers without searching again."""
        root = self._root(output_dir=output_dir)
        with _store(root) as db:
            self._require_run(db, run_id)
            if not any(row['selected'] for row in db.jobs(run_id)):
                raise ValueError('No approved papers in run')
            p = Profile.load(root / 'runs' / run_id / 'profile.json')
            job = None
            try:
                job = _ObservedRun(db, 'resume', self.on_event,
                                   digest(asdict(p)), existing=run_id)
                client = Client(job.emit, p.contact)
                with job.stage('collection'):
                    failures = collect(db, job, client, p)
                return self._complete(root, job, failures)
            except BaseException as exc:
                self._handle_failure(job, exc)
                raise

    @staticmethod
    def _complete(root, job, failures):
        summary = job.finish('partial' if failures else 'complete')
        return {'run_id': job.id, 'session_id': job.session,
                'output_dir': str(root), 'status': summary['status'],
                'summary': summary}

    def list_runs(self, limit=20, *, output_dir=None):
        """Return recent run objects. No database -> empty list."""
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('limit must be an integer from 1 to 100')
        root = self._root(output_dir=output_dir)
        if not (root / 'state.sqlite3').is_file():
            return []
        with _store(root) as db:
            rows = db.db.execute(
                'SELECT id, kind, status, started, finished FROM runs '
                'ORDER BY started DESC LIMIT ?', (limit,)).fetchall()
            return [dict(row) for row in rows]

    def get_run(self, run_id, *, output_dir=None):
        """Return run with paper metadata, selection/state and existing PDFs."""
        root = self._root(output_dir=output_dir)
        if not (root / 'state.sqlite3').is_file():
            raise ValueError('Unknown run ID')
        with _store(root) as db:
            row = self._require_run(db, run_id)
            jobs = []
            for item in db.jobs(run_id):
                paper = json.loads(item['metadata'])
                artifact = db.artifact(item['key'])
                path = None
                if artifact is not None:
                    candidate = root / artifact['path']
                    if candidate.is_file():
                        path = str(candidate)
                jobs.append({
                    'position': item['position'], 'selected': bool(item['selected']),
                    'status': item['status'], 'reason': item['reason'],
                    'paper': paper, 'pdf_path': path,
                })
            return {'run_id': run_id, 'output_dir': str(root),
                    **dict(row), 'jobs': jobs}
