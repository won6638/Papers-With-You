"""Naming and legacy PDF compatibility tests. Offline only."""
import json
import unittest
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from pypdf import PdfWriter

from PapersWithYou.model import Paper, Profile, digest
from PapersWithYou.naming import pdf_filename
from PapersWithYou.service import collect
from PapersWithYou.store import Run, Store
from PapersWithYou.net import TransferError


def fake_paper(doi='', title='Graph Neural Networks: A Survey?'):
    return Paper(
        provider='arxiv', paper_id='2601.00001', version='v1',
        title=title, authors=['Test Author'], abstract='', categories=['cs.AI'],
        published='2026-01-01', updated='2026-01-02',
        landing_url='https://arxiv.org/abs/2601.00001v1',
        pdf_url='https://arxiv.org/pdf/2601.00001v1', doi=doi,
    )


def pdf_bytes():
    writer=PdfWriter()
    writer.add_blank_page(width=72,height=72)
    b=BytesIO()
    writer.write(b)
    return b.getvalue()


class FakeClient:
    def __init__(self, content):
        self.content=content
        self.bytes_received=0
        self.total_limit=None
        self.calls=0

    def fetch(self, url, destination, max_bytes, stage):
        self.calls+=1
        Path(destination).write_bytes(self.content)
        self.bytes_received+=len(self.content)
        return len(self.content)


class NamingTests(unittest.TestCase):
    def test_doi_and_title(self):
        name=pdf_filename(fake_paper('10.1234/abc.567'))
        self.assertEqual(name, '10.1234_abc.567__Graph Neural Networks_ A Survey_.pdf')

    def test_missing_doi(self):
        name=pdf_filename(fake_paper())
        self.assertTrue(name.startswith('arxiv-2601.00001v1__'))
        self.assertTrue(name.endswith('.pdf'))

    def test_path_safety_and_length(self):
        name=pdf_filename(fake_paper('https://doi.org/10.9876/x/y', '<bad>'*200))
        self.assertLessEqual(len(name), 140)
        self.assertNotIn('/', name)
        self.assertNotIn('<', name)
        self.assertNotIn('>', name)

    def test_new_pdf_and_cache_and_legacy(self):
        with TemporaryDirectory() as tmp:
            store=Store(tmp)
            try:
                p=fake_paper('10.1234/test')
                profile=Profile(categories=['cs.AI'])
                run=Run(store,'test',digest(asdict(profile)))
                profile.save(run.directory/'profile.json')
                store.add(run.id,[p])
                store.select(run.id,[1])
                client=FakeClient(pdf_bytes())
                self.assertEqual(collect(store,run,client,profile),0)
                target=store.root/'papers'/p.stem/pdf_filename(p)
                self.assertTrue(target.is_file())
                self.assertEqual(client.calls,1)
                saved=json.loads((target.parent/'metadata.json').read_text())
                self.assertEqual(saved['file']['name'],target.name)
                self.assertEqual(collect(store,run,client,profile),0)
                self.assertEqual(client.calls,1)
                self.assertEqual(store.jobs(run.id)[0]['status'],'cached')
            finally:
                store.close()

    def test_legacy_pdf_reuse(self):
        with TemporaryDirectory() as tmp:
            store=Store(tmp)
            try:
                p=fake_paper()
                profile=Profile(categories=['cs.AI'])
                run=Run(store,'test',digest(asdict(profile)))
                profile.save(run.directory/'profile.json')
                store.add(run.id,[p])
                store.select(run.id,[1])
                legacy=store.root/'papers'/p.stem/'paper.pdf'
                legacy.parent.mkdir(parents=True)
                legacy.write_bytes(pdf_bytes())
                client=FakeClient(pdf_bytes())
                self.assertEqual(collect(store,run,client,profile),0)
                self.assertEqual(client.calls,0)
                self.assertEqual(store.jobs(run.id)[0]['status'],'recovered')
                self.assertEqual(json.loads((legacy.parent/'metadata.json').read_text())['file']['name'],'paper.pdf')
            finally:
                store.close()


if __name__=='__main__': unittest.main()
