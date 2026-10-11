"""Application API regression tests; no network requests."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from citeweave.application import CiteWeaveApp
from citeweave.model import Profile, Paper


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.events = []
        self.app = CiteWeaveApp(app_dir=self.root, on_event=self.events.append)
        self.paper = Paper(
            provider='arxiv', paper_id='2601.00001', version='v1',
            title='Example', authors=['Author'], abstract='Abstract',
            categories=['cs.AI'], published='2026-01-01', updated='2026-01-02',
            landing_url='https://arxiv.org/abs/2601.00001v1',
            pdf_url='https://arxiv.org/pdf/2601.00001v1')

    def test_profile_roundtrip(self):
        saved = self.app.save_profile({'categories': ['cs.AI'], 'max_results': 3})
        self.assertTrue(Path(saved['path']).is_file())
        self.assertEqual(self.app.load_profile()['max_results'], 3)

    def test_search_and_list(self):
        with patch('citeweave.application.arxiv_search', return_value=([self.paper], 10)):
            result = self.app.search({'categories': ['cs.AI']})
        self.assertEqual(result['status'], 'preview')
        self.assertEqual(result['reported_total'], 10)
        self.assertTrue(result['potentially_truncated'])
        self.assertEqual(result['candidates'][0]['position'], 1)
        self.assertEqual(self.app.list_runs()[0]['id'], result['run_id'])
        self.assertEqual(self.app.get_run(result['run_id'])['jobs'][0]['paper']['title'], 'Example')
        self.assertTrue(any(e['event'] == 'session_started' for e in self.events))
        json.dumps(result)

    def test_approval_and_resume(self):
        with patch('citeweave.application.arxiv_search', return_value=([self.paper], 1)):
            run_id = self.app.search(Profile(categories=['cs.AI']))['run_id']
        with self.assertRaises(ValueError):
            self.app.download(run_id, [2])
        with self.assertRaises(ValueError):
            self.app.resume(run_id)
        with patch('citeweave.application.collect', return_value=0) as collect:
            result = self.app.download(run_id, [1])
            self.assertEqual(result['status'], 'complete')
            self.assertTrue(self.app.get_run(run_id)['jobs'][0]['selected'])
            self.app.resume(run_id)
            self.assertEqual(collect.call_count, 2)
        json.dumps(result)

    def test_relative_output_path(self):
        path = self.root / 'custom' / 'profile.json'
        self.app.save_profile({'categories': ['cs.LG'], 'output_dir': 'data'}, path)
        with patch('citeweave.application.arxiv_search', return_value=([], 0)):
            result = self.app.search(path)
        self.assertEqual(Path(result['output_dir']), (path.parent / 'data').resolve())

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.app.list_runs(0)
        with self.assertRaises(TypeError):
            self.app.search(None)
        with self.assertRaises(ValueError):
            self.app.get_run('missing')


if __name__ == '__main__':
    unittest.main()
