"""arXiv Atom search. Citation edges and license grants are not inferred."""
from urllib.parse import urlencode, urlsplit
import re
import xml.etree.ElementTree as ET
from .model import Paper, ARXIV_ID
from .net import TransferError

ATOM = '{http://www.w3.org/2005/Atom}'
ARXIV = '{http://arxiv.org/schemas/atom}'
OPENSEARCH = '{http://a9.com/-/spec/opensearch/1.1/}'


def query(profile):
    if profile.ids:
        return {'id_list': ','.join(profile.ids)}
    pieces=['('+' OR '.join('cat:'+x for x in profile.categories)+')']
    pieces += ['all:"'+x+'"' for x in profile.keywords]
    if profile.since or profile.until:
        start=(profile.since or '1991-01-01').replace('-','')+'0000'
        end=(profile.until or '2999-12-31').replace('-','')+'2359'
        pieces.append(f'submittedDate:[{start} TO {end}]')
    value=' AND '.join(pieces)
    for x in profile.exclude:
        value += ' ANDNOT all:"'+x+'"'
    return {'search_query': value}


def parse_feed(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise TransferError('unsafe_xml')
    try: root=ET.fromstring(data)
    except ET.ParseError as e: raise TransferError('invalid_atom') from e
    if root.tag != ATOM+'feed': raise TransferError('invalid_atom')
    try: total=int(root.findtext(OPENSEARCH+'totalResults','0'))
    except ValueError as e: raise TransferError('invalid_total') from e
    papers=[]
    for entry in root.findall(ATOM+'entry'):
        full_id=entry.findtext(ATOM+'id','')
        u=urlsplit(full_id)
        if u.hostname not in {'arxiv.org','export.arxiv.org'} or not u.path.startswith('/abs/'):
            raise TransferError('invalid_paper_id')
        ident=u.path[len('/abs/'):]
        if not ARXIV_ID.fullmatch(ident): raise TransferError('arxiv_api_error')
        match=re.fullmatch(r'(.+?)(v[1-9]\d*)',ident)
        if not match: raise TransferError('missing_version')
        pid,version=match.groups()
        papers.append(Paper(
            provider='arxiv',paper_id=pid,version=version,
            title=' '.join(entry.findtext(ATOM+'title','').split()),
            authors=[a.findtext(ATOM+'name','') for a in entry.findall(ATOM+'author')],
            abstract=' '.join(entry.findtext(ATOM+'summary','').split()),
            categories=[c.attrib['term'] for c in entry.findall(ATOM+'category')],
            published=entry.findtext(ATOM+'published',''),updated=entry.findtext(ATOM+'updated',''),
            landing_url='https://arxiv.org/abs/'+ident,
            pdf_url='https://arxiv.org/pdf/'+ident,
            doi=entry.findtext(ARXIV+'doi','')))
    return papers,total


def search(profile,client,temp_dir,emit):
    """Fetch at most max_results. This is a bounded rescan, not complete harvesting."""
    results={}
    total=0
    expected=min(len(profile.ids),profile.max_results) if profile.ids else profile.max_results
    start=0
    while start<expected:
        params=query(profile)
        params.update(start=start,max_results=min(50,expected-start),sortBy='lastUpdatedDate',sortOrder='descending')
        target=temp_dir/'feed.part'
        try:
            client.fetch('https://export.arxiv.org/api/query?'+urlencode(params),target,4*1024*1024,'search')
            papers,total=parse_feed(target.read_bytes())
        finally:
            target.unlink(missing_ok=True)
        for paper in papers: results[paper.key]=paper
        emit('search_page',offset=start,received=len(papers),total_reported=total)
        if not papers: break
        start+=len(papers)
        if start>=total: break
    return list(results.values())[:profile.max_results],total
