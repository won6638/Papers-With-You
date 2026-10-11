# Papers With You

[한국어](README.ko.md)

Papers With You is a local command-line tool for finding and downloading research papers from arXiv.

Users can search by category, keywords, excluded terms, and submission dates, then select which papers to download.

## Features

- Search arXiv using custom search conditions
- Preview and select papers before downloading
- Validate downloaded PDFs and save paper metadata
- Resume interrupted jobs and reuse previously downloaded files
- Record download results and errors locally

## Installation

Requires Python 3.12. Designed for Windows 10/11 and Ubuntu.

**Windows (PowerShell)**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Ubuntu**

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## Usage

Run the following commands with your virtual environment's Python interpreter.

Create a search profile:

```bash
python PapersWithYou.py init
```

Search and preview papers:

```bash
python PapersWithYou.py search
```

Search, select, and download papers:

```bash
python PapersWithYou.py run
```

Check previous runs or resume a download:

```bash
python PapersWithYou.py status
python PapersWithYou.py resume --run-id RUN_ID
```

The default download directory is `downloads/`. An example search profile is available in [examples/profile.json](examples/profile.json).

## Notes

- Currently supports arXiv only.
- Search categories use arXiv category codes, such as `cs.AI` and `cs.LG`.
- Search keywords should be in English.
- Search results are sorted by the last update date. Complete coverage of all papers is not guaranteed.
- The purpose and free-description fields are saved but are not yet used for ranking.
- GUI, semantic search, and personalized recommendations are not implemented yet.

## License

Licensed under [PolyForm Noncommercial 1.0.0](LICENSE). Commercial use outside the license terms requires separate permission.

See [Third-party notices](THIRD_PARTY_NOTICES.md) for dependency licenses.
