# Verification / 검증 기록

Date / 일자: 2026-09-30 UTC. Environment / 환경: Ubuntu 24.04.3 LTS, Python 3.12.14, pypdf 6.10.0.

| Check / 확인 | Result / 결과 |
|---|---|
| Offline recovery/transport/validation/approval tests / 오프라인 복구·전송·검증·승인 테스트 | 19 passed / 19개 통과 |
| Paired README structure/commands / 한영 README 구조·명령 | Passed + manual semantic review / 통과 및 의미 수동 검토 |
| Python compilation / 파이썬 컴파일 | Passed / 통과 |
| Wheel build (no dependencies bundled) / 의존성 미포함 wheel 빌드 | Passed / 통과 |
| Exact-ID live download: 1706.03762v7, 1609.02907v4 | 2/2 valid PDFs, 27.7556 s, 3 requests, 3,093,607 bytes including Atom |
| Same approved run resumed / 동일 승인 실행 재개 | 2 cached, 0 requests, 0.0172 s |
| Live cs.AI OR cs.LG search / 실제 분야 검색 | 3 candidates, 409,425 total reported, bounded window; approximately 9.55 s |
| Latest candidate PDF: 2609.38178v1 | HTTP 404, correctly failed; 9.8785 s collection session |

The 404 is an observed response, not proof that the paper is permanently unavailable. It demonstrates why metadata discovery and successful PDF acquisition are separate states. No automatic retry is made for 404; an explicit resume can retry later. The cause beyond the HTTP response has not been established. No PDF or full text is committed.

404는 관측된 응답이며 해당 논문이 영구적으로 제공되지 않는다는 증거는 아닙니다. 메타데이터 발견과 PDF 확보를 구분해야 하는 사례입니다. 404에는 자동 재시도하지 않으며 사용자가 resume하면 나중에 다시 시도할 수 있습니다. HTTP 응답 이상의 원인은 확인하지 않았습니다. PDF·원문은 커밋하지 않습니다.

These are small live smoke measurements, not statistically representative benchmarks, quality scores or a freshness guarantee. The category preview's remaining two papers were not downloaded. Source-fingerprint logging was added after the first two-paper download, and is present in later sessions. Aggregate evidence is in measurements.json; detailed profiles, feeds, PDFs and logs remain local and excluded.

소규모 실제 스모크 측정이며 대표 벤치마크·품질 점수·최신성 보장이 아닙니다. 분야 검색의 나머지 두 편은 다운로드하지 않았습니다. 첫 2편 다운로드 후 소스 지문 로깅을 추가했으며 이후 세션에 기록됩니다. 집계 근거는 measurements.json에 있고 상세 프로필·피드·PDF·로그는 로컬에만 보관하며 제외합니다.

Not yet verified / 미검증:
- Windows 10/11 desktop execution and live downloads on Ubuntu 22.04; Windows Server CI does not substitute for desktop validation.
- Windows 10/11 데스크톱 실행과 Ubuntu 22.04의 실제 다운로드. Windows Server CI는 데스크톱 검증을 대신하지 않습니다.
- Broad provider reliability, scale, complete update coverage, ranking quality and malicious-PDF isolation.
- 폭넓은 공급처 안정성·규모·전체 갱신 누락률·추천 품질·악성 PDF 격리.


## Remote verification update / 원격 검증 갱신

2026-09-30 KST: All 28 initial source/document paths are present in the private GitHub repository. Initial Windows Server CI failed on Korean output through a legacy encoding. CLI output now uses backslashreplace for unsupported characters; a regression test was added. Local suite: 20 passed. Remote run #3 at commit 5c683db5fc0ac6ac2a2db33e271ed234363df4a3 passed all three jobs: Ubuntu 22.04, Ubuntu 24.04 and Windows Server 2022, Python 3.12. Each job runs the offline tests and bilingual README check. This is not live arXiv or Windows 10/11 desktop validation.

2026-09-30 한국 시간: 초기 소스·문서 28개 경로를 비공개 저장소에서 확인했습니다. 첫 Windows Server CI에서는 한글의 레거시 인코딩 출력 오류가 발생했습니다. 표현 불가능한 문자를 backslashreplace 처리하고 회귀 테스트를 추가했습니다. 로컬 테스트 20개 통과. 위 커밋의 CI #3에서 Ubuntu 22.04·24.04 및 Windows Server 2022 / Python 3.12의 오프라인 테스트·한영 README 검사 작업 3개가 모두 통과했습니다. 실제 arXiv 다운로드나 Windows 10/11 데스크톱 검증은 아닙니다.

Evidence / 근거: https://github.com/won6638/CiteWeave/actions/runs/36682215749

Remaining CI warnings: checkout@v4 and setup-python@v5 target Node 20 and GitHub ran them on Node 24. Review action upgrades in the next maintenance change. Remote archive download did not complete, so a full byte-for-byte source comparison is not claimed.

남은 CI 경고: checkout@v4·setup-python@v5의 Node 20 대상으로 인해 GitHub가 Node 24에서 실행했습니다. 다음 유지보수에서 액션 버전 갱신을 검토합니다. 원격 압축파일 다운로드가 완료되지 않았으므로 전체 파일 바이트 단위 대조 완료를 주장하지 않습니다.
