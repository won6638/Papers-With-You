"""Unit tests for PapersWithYouApp against the existing engine (no network)."""
import json
import unittest
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from PapersWithYou.application import PapersWithYouApp
from PapersWithYou.model import Profile, Paper


class ApplicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.events = []
        self.app = PapersWithYouApp(app_dir=self.root, on_event=self.events.append)
        self.paper = Paper(
            provider='arxiv', paper_id='2601.00001', version='v1',
            title='Example', authors=['Author'], abstract='Abstract',
            categories=['cs.AI'], published='2026-01-01', updated='2026-01-02',
            landing_url='https://arxiv.org/abs/2601.00001v1',
            pdf_url='https://arxiv.org/pdf/2601.00001v1',
        )

    def test_profile_roundtrip(self):
        src = {'categories': ['cs.AI'], 'max_results': 3}
        saved = self.app.save_profile(src)
        self.assertTrue(Path(saved['path']).is_file())
        self.assertEqual(self.app.load_profile()['max_results'], 3)

    def test_search_and_list(self):
        with patch('PapersWithYou.application.arxiv_search', return_value=([self.paper], 10)):
            result = self.app.search({'categories': ['cs.AI']})
        self.assertEqual(result['status'], 'preview')
        self.assertEqual(result['reported_total'], 10)
        self.assertTrue(result['potentially_truncated'])
        self.assertEqual(result['candidates'][0]['position'], 1)
        self.assertEqual(self.app.list_runs()[0]['id'], result['run_id'])
        self.assertEqual(self.app.get_run(result['run_id'])['jobs'][0]['paper']['title'], 'Example')
        self.assertTrue(any(event['event'] == 'session_started' for event in self.events))
        json.dumps(result)

    def test_approval_and_resume(self):
        with patch('PapersWithYou.application.arxiv_search', return_value=([self.paper], 1)):
            run_id = self.app.search(Profile(categories=['cs.AI']))['run_id']
        with self.assertRaises(ValueError):
            self.app.download(run_id, [2])
        with self.assertRaises(ValueError):
            self.app.resume(run_id)
        with patch('PapersWithYou.application.collect', return_value=0) as collect:
            response = self.app.download(run_id, [1])
            self.assertEqual(response['status'], 'complete')
            self.assertTrue(self.app.get_run(run_id)['jobs'][0]['selected'])
            self.app.resume(run_id)
            self.assertEqual(collect.call_count, 2)
        json.dumps(response)

    def test_profile_path_and_output_override(self):
        p = self.root / 'custom' / 'profile.json'
        data = self.app.save_profile({'categories': ['cs.LG'], 'output_dir': 'output'}, path=p)
        with patch('PapersWithYou.application.arxiv_search', return_value=([], 0)):
            response = self.app.search(data['path'])
        self.assertEqual(Path(response['output_dir']), (p.parent / 'output').resolve())


if __name__ == '__main__':
    unittest.main()
