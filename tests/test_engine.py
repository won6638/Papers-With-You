"""Generated PDFs and synthetic Atom only; no external requests."""
from contextlib import contextmanager
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
import json
import unittest
from unittest.mock import patch
from pypdf import PdfWriter
from citeweave.arxiv import parse_feed,query
from citeweave.cli import positions, main
from citeweave.model import Profile,Paper,digest
from citeweave.net import Client,TransferError,allowed_url
from citeweave.service import collect,validate_pdf
from citeweave.store import Store,Run

ATOM=b'''<feed xmlns="http://www.w3.org/2005/Atom" xmlns:o="http://a9.com/-/spec/opensearch/1.1/">
<o:totalResults>1</o:totalResults><entry><id>http://arxiv.org/abs/2601.00001v2</id>
<title>Synthetic test paper</title><summary>Not a real paper</summary><author><name>Test Author</name></author>
<published>2026-01-01T00:00:00Z</published><updated>2026-01-02T00:00:00Z</updated><category term="cs.AI"/></entry></feed>'''
def pdf_bytes():
    w=PdfWriter(); w.add_blank_page(width=72,height=72)
    f=BytesIO(); w.write(f); return f.getvalue()
class Gate:
    @contextmanager
    def enter(self): yield 0
class Response(BytesIO):
    status=200
    def __init__(self,data,headers=None,url='https://arxiv.org/pdf/2601.00001v2'):
        super().__init__(data); self.headers=headers or {}; self.url=url
    def geturl(self): return self.url
class Opener:
    def __init__(self,*items): self.items=list(items); self.calls=0
    def open(self,request,timeout):
        self.calls+=1; result=self.items.pop(0)
        if isinstance(result,BaseException): raise result
        return result
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.store=Store(self.root); self.profile=Profile(categories=['cs.AI'])
    def tearDown(self): self.store.close(); self.tmp.cleanup()
    def run_with(self):
        r=Run(self.store,'test',digest(asdict(self.profile)))
        self.profile.save(r.directory/'profile.json'); paper=parse_feed(ATOM)[0][0]
        self.store.add(r.id,[paper]); self.store.select(r.id,[1]); return r,paper
    def client(self,run,*items):
        o=Opener(*items); return Client(run.emit,gate=Gate(),opener=o,sleep=lambda _:None),o
    def test_profile_validation(self):
        for p in [Profile(keywords=['" OR all:*']),Profile(since='2026-02-01',until='2026-01-01'),Profile(max_results=0),Profile(categories=['../bad']),Profile(auto_download='false')]:
            with self.assertRaises(ValueError): p.validate()
    def test_query(self):
        q=query(Profile(keywords=['graph networks'],exclude=['biology'],since='2025-01-01'))['search_query']
        self.assertIn('all:"graph networks"',q); self.assertIn('ANDNOT all:"biology"',q); self.assertIn('202501010000',q)
        self.assertEqual(query(Profile(ids=['1706.03762'])),{'id_list':'1706.03762'})
    def test_atom(self):
        papers,total=parse_feed(ATOM)
        self.assertEqual(total,1); self.assertEqual(papers[0].version,'v2'); self.assertIsNone(papers[0].license_url)
    def test_invalid_xml(self):
        for value in [b'<html/>',b'<!DOCTYPE feed [<!ENTITY a "x">]><feed/>',b'<']:
            with self.assertRaises(TransferError): parse_feed(value)
    def test_url_allowlist(self):
        for url in ['http://arxiv.org/pdf/a','https://arxiv.org.evil.test/x','https://user@arxiv.org/a','https://localhost/a','file:///etc/passwd']:
            with self.assertRaises(TransferError): allowed_url(url)
    def test_selection(self):
        self.assertEqual(positions('1,3-5,3',5),[1,3,4,5])
        for value in ['0','1-9','5-2','a']:
            with self.assertRaises(ValueError): positions(value,5)
    def test_pdf_validation(self):
        p=self.root/'test.pdf'; p.write_bytes(pdf_bytes()); self.assertEqual(validate_pdf(p)[2],1)
        p.write_bytes(b'<html>login</html>')
        with self.assertRaises(TransferError): validate_pdf(p)
    def test_download_cache_and_metadata(self):
        r,p=self.run_with(); c,o=self.client(r,Response(pdf_bytes()))
        self.assertEqual(collect(self.store,r,c,self.profile),0)
        self.assertEqual(collect(self.store,r,c,self.profile),0); self.assertEqual(o.calls,1)
        meta=json.loads((self.root/'papers'/p.stem/'metadata.json').read_text())
        self.assertEqual(meta['identity_status'],'provider_link_only')
        self.assertEqual(self.store.jobs(r.id)[0]['status'],'cached')
        summary=r.finish('complete'); self.assertEqual(summary['download_attempted_papers'],1); self.assertEqual(summary['download_validation_ratio'],1)
    def test_html_never_complete(self):
        r,p=self.run_with(); c,o=self.client(r,Response(b'<html>blocked</html>'))
        self.assertEqual(collect(self.store,r,c,self.profile),1); self.assertIsNone(self.store.artifact(p.key))
        self.assertEqual(self.store.jobs(r.id)[0]['reason'],'not_pdf')
        self.assertFalse((self.root/'papers'/p.stem/'paper.pdf.part').exists())
    def test_retry_429(self):
        r,p=self.run_with(); e=HTTPError('https://arxiv.org',429,'limited',{'Retry-After':'3'},None)
        c,o=self.client(r,e,Response(pdf_bytes())); self.assertEqual(collect(self.store,r,c,self.profile),0)
        summary=r.finish('complete'); self.assertEqual(summary['request_count'],2); self.assertEqual(summary['retry_wait_s'],3)
    def test_long_retry_after(self):
        r,p=self.run_with(); c,o=self.client(r,HTTPError('https://arxiv.org',429,'limited',{'Retry-After':'600'},None))
        self.assertEqual(collect(self.store,r,c,self.profile),1); self.assertEqual(o.calls,1)
    def test_404(self):
        r,p=self.run_with(); c,o=self.client(r,HTTPError('https://arxiv.org',404,'missing',{},None))
        self.assertEqual(collect(self.store,r,c,self.profile),1); self.assertEqual(o.calls,1)
    def test_crash_after_replace(self):
        r,p=self.run_with(); d=self.root/'papers'/p.stem; d.mkdir(parents=True); (d/'paper.pdf').write_bytes(pdf_bytes())
        self.store.state(r.id,p.key,'downloading'); c,o=self.client(r)
        self.assertEqual(collect(self.store,r,c,self.profile),0); self.assertEqual(o.calls,0)
        self.assertEqual(self.store.jobs(r.id)[0]['status'],'recovered')
    def test_corruption_refetch(self):
        r,p=self.run_with(); c,o=self.client(r,Response(pdf_bytes()),Response(pdf_bytes()))
        collect(self.store,r,c,self.profile); (self.root/'papers'/p.stem/'paper.pdf').write_bytes(b'broken')
        self.assertEqual(collect(self.store,r,c,self.profile),0); self.assertEqual(o.calls,2)
    def test_interrupt_resume(self):
        r,p=self.run_with(); c,o=self.client(r,KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt): collect(self.store,r,c,self.profile)
        self.assertEqual(self.store.jobs(r.id)[0]['status'],'downloading'); r.finish('interrupted')
        r2=Run(self.store,'resume',existing=r.id); c,o=self.client(r2,Response(pdf_bytes()))
        self.assertEqual(collect(self.store,r2,c,self.profile),0)
    def test_size_limit(self):
        r,p=self.run_with(); c,o=self.client(r,Response(b'abc',{'Content-Length':str(300*1024*1024)}))
        self.assertEqual(collect(self.store,r,c,self.profile),1); self.assertEqual(self.store.jobs(r.id)[0]['reason'],'size_limit')
    def test_versions(self):
        r,p=self.run_with(); c,o=self.client(r,Response(pdf_bytes())); collect(self.store,r,c,self.profile)
        other=Paper(**{**p.data(),'version':'v3','pdf_url':p.pdf_url.replace('v2','v3')})
        r2=Run(self.store,'test'); self.store.add(r2.id,[other]); self.store.select(r2.id,[1])
        c,o=self.client(r2,Response(pdf_bytes())); collect(self.store,r2,c,self.profile)
        for paper in (p,other): self.assertTrue((self.root/'papers'/paper.stem/'paper.pdf').exists())
    def test_noninteractive_no_download(self):
        profile=self.root/'profile.json'; self.profile.save(profile)
        with patch('citeweave.cli.search',return_value=(parse_feed(ATOM)[0],1)),patch('citeweave.cli.collect') as download,patch('sys.stdin.isatty',return_value=False):
            code=main(['run','--profile',str(profile),'--output',str(self.root/'cli')],app_dir=self.root)
        self.assertEqual(code,0); download.assert_not_called()
    def test_logs_hide_query_and_headers(self):
        r,p=self.run_with(); c,o=self.client(r,Response(pdf_bytes())); collect(self.store,r,c,self.profile); r.finish('complete')
        events=(r.directory/'events.jsonl').read_text(); self.assertNotIn('search_query',events); self.assertNotIn('User-Agent',events)
if __name__=='__main__': unittest.main()
