# CiteWeave

[한국어](README.ko.md) · Private alpha · 0.1.0a1

<!-- section: status -->
## Status and name

A local-first arXiv paper collector with a questionnaire, preview/approval, validated downloads, resume, SQLite state and execution telemetry. The working name conflicts with existing services/projects, including [citeweave.com](https://citeweave.com/en) and [CiteWeave-RAG](https://github.com/Youn-17/CiteWeave-RAG). This is an independent implementation with no affiliation. Keep this repository private and revisit the name before public release. No package has been published.

Targets: Python 3.12, Windows 10/11 x86-64 and Ubuntu 22.04/24.04 x86-64. Tested locally on Ubuntu 24.04.3, Python 3.12.14. Windows 10/11 and Ubuntu 22.04 are not yet verified. CI targets Ubuntu and Windows Server; passing Server CI is not a desktop OS certification.

<!-- section: setup -->
## Install

Use a Python 3.12 virtual environment from the repository root. The only external runtime dependency is pypdf 6.10.0 (BSD-3-Clause), pinned for reproducibility. No API key, LLM, GPU or paid API is required. Start with the portable launcher; its directory determines the default downloads directory. The optional package build backend is setuptools 84.0.0.

```text
# Windows PowerShell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe citeweave.py init
.venv\Scripts\python.exe citeweave.py run

# Ubuntu
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python citeweave.py init
.venv/bin/python citeweave.py run
```

<!-- section: commands -->
## Commands and approval

Use the virtual environment's Python for all commands. Search saves a preview without downloading. Run and sync print candidates and ask for selection and confirmation. Select numbers/ranges or all; blank cancels. In a noninteractive terminal, downloads require explicit approval or an enabled profile setting.

Resume continues the same approved jobs, not a new search. Without a selection override, prior approval remains valid. It verifies existing files without re-downloading valid ones. Unfinished files restart from the beginning; byte-range continuation is not implemented. An override adds to the approved set rather than removing old selections. Specify the custom output directory again when using resume or status.

```text
python citeweave.py init --profile profiles/default.json
python citeweave.py search --profile profiles/default.json
python citeweave.py run --profile profiles/default.json
python citeweave.py run --profile profiles/default.json --select 1,3-5 --yes
python citeweave.py sync --profile profiles/default.json
python citeweave.py resume --run-id RUN_ID
python citeweave.py status
python citeweave.py run --profile profiles/default.json --output /path/to/library
python citeweave.py resume --run-id RUN_ID --output /path/to/library
```

<!-- section: profile -->
## Questionnaire and settings

The questionnaire collects categories, purpose, keyword phrases, excluded phrases, free description, date range, maximum count, output folder and an optional request-identification contact. Edit the resulting JSON or start from [the example](examples/profile.json). Categories are ORed; keyword phrases are ANDed; exclusions use ANDNOT. Use English phrases for arXiv search; there is no automatic translation. Categories are not restricted to AI/CS, but examples and initial validation focus there.

Dates filter first submission, not revision date; results are sorted by last update. Purpose and free description are stored locally but do NOT affect ranking yet. If exact IDs are supplied for diagnostics, they override categories, keywords, exclusions and dates.

Defaults: maximum 20 candidates (allowed 1–100), 50 MiB per file, 250 MiB received PDF traffic per collection session. Retries count toward the session traffic budget. Limits may be exceeded by at most one read block before stopping. This is not a lifetime disk quota. Automatic download is disabled. To deliberately skip future base-paper confirmation, edit the setting below; set it back to false to restore prompts. Future citation-expansion approval will be separate.

```text
"auto_download": false
```

<!-- section: storage -->
## Storage and recovery

Default: downloads beside the launcher (not the shell's current directory). A relative profile output path resolves against the profile's directory; a relative command-line output path resolves against the current directory. Unwritable locations produce an error; no elevation or silent fallback occurs.

SQLite is the job-state authority. Each version has its own PDF and JSON sidecar with provider, identifiers, metadata, checksum and validation time. Revisions never overwrite earlier versions. A completed but uncommitted file can be revalidated and recovered. Interrupted partial files are removed or overwritten on retry. Per-store OS locks prevent concurrent writers; an OS-released per-user arXiv lock serializes this application's requests across stores, leaving at least 3.1 seconds after each request. Other programs/machines must coordinate separately.

<!-- section: freshness -->
## Freshness and known limitations

Sync is a bounded rescan of the configured search, not a complete incremental mirror. The candidate file records reported total and possible truncation. There is no full-sync watermark, background scheduler, guaranteed 24-hour freshness or guarantee of finding every revision. A large category can exceed the configured window. Results depend on provider indexing and availability.

The alpha has no desktop GUI, web server, semantic ranking, LLM interpretation, recommendations model, citation expansion, S2AG/OpenAlex integration, RAG, KG or GNN. Citation expansion will be opt-in, one hop, separately previewed and capped. arXiv Atom does not provide a complete citation graph.

PDF validation checks the header, page tree and readable streams, then calculates SHA-256. It is neither a malware scan nor a guarantee of visual correctness/full-text identity. Identity is based on the provider's versioned URL, and article license is unknown when the feed does not supply it. Parsing is not sandboxed. Files are never automatically opened.

<!-- section: telemetry -->
## Logs and measurements

Each run stores events.jsonl, candidates.json, profile.json, papers.csv and session summaries. Events include run/session IDs, UTC time, software/source fingerprint, Python/pypdf versions, phase timing, provider host, HTTP status, retry, transferred bytes and outcomes. Search query strings and request headers are not copied into event logs. Profile/candidate files still contain private interests and metadata: do not upload the output directory.

Summary separates selected-paper acquisition from attempted-download validation and cached/recovered files. Timings, traffic and retries describe the current session; job states describe the run's current state across resumes. Previous session summaries remain available. CSV titles are escaped against spreadsheet formula injection. Exit codes: 0 success/preview, 1 operation error, 2 partial download failure, 130 interruption.

The HTTP client uses a 20-second socket timeout, a 60-second transfer deadline check and at most 3 attempts for transient errors. Retry-After over 60 seconds defers work with an error instead of retrying early. PDF redirects are restricted to approved HTTPS arXiv hosts.

<!-- section: tests -->
## Tests and evidence

Offline tests use generated PDFs and synthetic metadata, not bundled papers. The documentation check compares section IDs, command blocks and inline technical tokens; human semantic review is also required. CI does not call arXiv. Sanitized real measurements and platform gaps are in [verification](docs/VERIFICATION.md). The initial two-paper experiment is a smoke test, not a representative success-rate benchmark.

```text
python -m unittest discover -s tests -v
python scripts/check_readme.py
```

<!-- section: license -->
## License and contact

Original code is source-available under PolyForm Noncommercial 1.0.0; this is not an OSI-approved open-source license. The standard [LICENSE](LICENSE) governs. It permits specified organizations under its own terms; commercial use outside its grants requires separate permission from relevant rights holders. See [contact](CONTACT.md), [third-party notices](THIRD_PARTY_NOTICES.md) and [license review](docs/LICENSE_REVIEW.md).

Use this repository's Issues for questions and permission requests after the remote exists. While private, only invited collaborators can use it. No personal email has been invented. A confidential contact channel remains to be chosen before public release. An issue does not grant permission.

arXiv PDFs and future corpora/models retain separate rights; our code license grants no paper redistribution rights. Do not commit downloaded PDFs, corpora, private profiles/logs or keys. Paying a future API provider does not automatically license paywalled papers. No paid provider is enabled.

<!-- section: roadmap -->
## Roadmap

1. Broaden collection/recovery measurements and validate Windows 10/11 and Ubuntu 22.04.
2. Add transparent keyword relevance baselines, then title/abstract semantic ranking.
3. Diversify providers and implement one-hop citation expansion after policy review.
4. Add a questionnaire-style desktop GUI over the same engine/profile schema.
5. Explore LLM input, RAG, KG and GNN; consider a web service only after stabilization.

Read [decisions](docs/DECISIONS.md) and [contribution rules](CONTRIBUTING.md). English and Korean README changes must ship together with the same features, defaults, limitations and evidence.
