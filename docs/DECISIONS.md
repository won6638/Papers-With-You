# Decisions / 결정 사항

- Working name: CiteWeave. Name conflicts found on 2026-09-30: https://citeweave.com/en and https://github.com/Youn-17/CiteWeave-RAG; also a search result for ruoyuanwang/citeweave. This is an exact/similar-name web check, not a trademark clearance. No code was copied from these projects. Keep private and revisit the name before public release.
- 작업명: CiteWeave. 2026-09-30 확인한 충돌: 위 서비스와 저장소 및 ruoyuanwang/citeweave 검색 결과. 웹 이름 조사이며 상표 등록·법적 사용 가능성 검증이 아닙니다. 해당 프로젝트의 코드를 복사하지 않았습니다. 비공개로 진행하고 public 전환 전에 이름을 재검토합니다.

- Core engine is independent of terminal prompts. CLI first; questionnaire-style desktop GUI next; web much later. Profiles have a versioned schema to support GUI/LLM input later. Purpose and free description are retained but not used to rank papers in alpha.
- 핵심 엔진과 터미널 입력을 분리합니다. CLI 다음은 설문형 데스크톱 GUI, 웹은 장기 계획입니다. 프로필 버전으로 GUI·LLM 입력 확장에 대비합니다. 목적·자유 설명은 알파에서 저장만 하며 순위에 반영하지 않습니다.

- Initial arXiv-only adapter; AI/CS examples, no hardcoded field restriction. No paid APIs. Exact-ID mode is for reproducible diagnostics and overrides search fields. Normal mode uses OR across categories, AND across phrases, ANDNOT for exclusions, first-submission date bounds, most-recently-updated sorting.
- 첫 연결은 arXiv만 사용하며 AI·CS 예시를 제공하지만 분야를 코드로 제한하지 않습니다. 유료 API는 없습니다. 정확한 ID 모드는 재현 진단용이며 검색 조건보다 우선합니다. 일반 모드는 분야 OR·구문 AND·제외 ANDNOT·최초 제출일 기간·최근 수정 순 정렬입니다.

- sync is an explicitly bounded rescan, NOT a complete incremental mirror. No "fully synchronized" watermark is advanced. New revisions get separate files. Byte-level partial download continuation is not implemented: unfinished files restart, completed jobs are reused after validation.
- sync는 제한된 재검색이며 완전한 증분 미러링이 아닙니다. 전체 동기화 완료 워터마크를 기록하지 않습니다. 수정본은 별도 저장합니다. 바이트 단위 이어받기는 미구현이며 미완료 파일은 재시작하고 완료 파일은 검증 후 재사용합니다.

- Citation expansion: later, opt-in, references/citing papers separate, one hop, proposed default 20 additional papers with an overall cap and separate preview/approval. arXiv Atom does not supply a complete citation graph. No recursive crawling in alpha.
- 인용 확장: 다음 단계, 선택 기능, 참고문헌·피인용 분리, 1단계, 추가 기본 20편 제안, 전체 상한 및 별도 목록·승인. arXiv Atom은 완전한 인용 그래프를 제공하지 않습니다. 알파에는 재귀 수집이 없습니다.

- Target: Python 3.12, Windows 10/11 x86-64, Ubuntu 22.04/24.04 x86-64. Windows Server CI is not evidence of Windows 10/11 validation. GUI framework remains intentionally undecided.
- 목표 환경: Python 3.12, Windows 10/11 x86-64, Ubuntu 22.04/24.04 x86-64. Windows Server CI는 Windows 10/11 검증을 대신하지 않습니다. GUI 프레임워크는 아직 결정하지 않습니다.
