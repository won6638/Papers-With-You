"""Portable, readable PDF filenames; arXiv version remains the folder identity."""
import re


_MAX_STEM = 136  # filename (including .pdf) <= 140 characters
_FORBIDDEN = re.compile(r'[<>:"/\\|?*\x00-\x1f\x7f]')


def _clean(text):
    text = _FORBIDDEN.sub('_', str(text))
    text = re.sub(r'\s+', ' ', text).strip(' .')
    return text or 'Untitled'


def pdf_filename(paper):
    """DOI__Title.pdf, or arxiv-ID-version__Title.pdf when DOI is absent."""
    doi = (paper.doi or '').strip()
    doi = re.sub(r'^https?://(?:dx\.)?doi\.org/', '', doi, flags=re.I)
    identifier = _clean(doi if doi else f'arxiv-{paper.stem}')[:60].rstrip(' .')
    capacity = _MAX_STEM - len(identifier) - len('__')
    title = _clean(paper.title)[:capacity].rstrip(' .') or 'Untitled'
    return f'{identifier}__{title}.pdf'
