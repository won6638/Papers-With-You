# CiteWeave

[English](README.md) · 비공개 알파 · 0.1.0a1

<!-- section: status -->
## 상태와 이름

설문, 목록 확인·승인, 검증된 다운로드, 재개, SQLite 상태 관리, 실행 기록을 제공하는 로컬 arXiv 논문 수집기입니다. 작업명은 [citeweave.com](https://citeweave.com/en), [CiteWeave-RAG](https://github.com/Youn-17/CiteWeave-RAG) 등 기존 서비스·프로젝트와 겹칩니다. 독립적으로 작성했으며 이들과 관련이 없습니다. 저장소를 비공개로 유지하고 public 전환 전에 이름을 다시 검토해야 합니다. 패키지는 공개 배포하지 않았습니다.

목표 환경: Python 3.12, Windows 10/11 x86-64, Ubuntu 22.04/24.04 x86-64. 현재 로컬 검증 환경은 Ubuntu 24.04.3, Python 3.12.14입니다. Ubuntu 22.04/24.04와 Windows Server 2022의 오프라인 CI를 통과했습니다. Windows 10/11 데스크톱 실행은 아직 검증하지 않았습니다. CI는 Ubuntu와 Windows Server를 대상으로 하며 Server CI 통과가 데스크톱 OS 검증을 대신하지 않습니다.

<!-- section: setup -->
## 설치

저장소 루트에서 Python 3.12 가상환경을 사용합니다. 외부 실행 의존성은 재현성을 위해 고정한 pypdf 6.10.0(BSD-3-Clause) 하나입니다. API 키·LLM·GPU·유료 API가 필요하지 않습니다. 기본 실행은 휴대형 런처를 사용하며 런처 위치가 기본 다운로드 폴더를 결정합니다. 선택적인 패키지 빌드 백엔드는 setuptools 84.0.0입니다.

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
## 명령과 승인

모든 명령에 가상환경의 Python을 사용합니다. Search는 다운로드 없이 목록을 저장합니다. Run과 sync는 후보를 표시하고 번호 선택과 승인을 받습니다. 번호·범위 또는 all로 선택하며 빈 입력은 취소입니다. 비대화형 터미널에서는 명시적인 승인이나 활성화된 프로필 설정이 있어야 다운로드합니다.

Resume은 새로운 검색이 아니라 같은 승인 작업을 이어갑니다. 선택 재지정이 없으면 이전 승인이 유지됩니다. 기존 파일을 검증하고 유효한 파일은 다시 받지 않습니다. 미완료 파일은 처음부터 받으며 바이트 단위 이어받기는 미구현입니다. 선택 재지정은 기존 승인 목록을 지우지 않고 추가합니다. 사용자 지정 저장 폴더는 resume·status에서도 다시 지정해야 합니다.

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
## 설문과 설정

설문은 분야, 목적, 키워드 구문, 제외 구문, 자유 설명, 기간, 최대 편수, 저장 폴더와 선택적인 요청 식별용 연락처를 받습니다. 생성한 JSON을 수정하거나 [예제](examples/profile.json)에서 시작할 수 있습니다. 분야는 OR, 키워드 구문은 AND, 제외는 ANDNOT으로 검색합니다. arXiv 검색 구문은 영어를 사용하며 자동 번역은 없습니다. 분야는 AI·CS로 제한하지 않지만 예제와 초기 검증은 해당 분야에 집중합니다.

기간은 수정일이 아니라 최초 제출일 기준이며 결과는 최근 수정 순입니다. 목적과 자유 설명은 로컬 저장만 하며 아직 순위에 영향을 주지 않습니다. 진단용 정확한 ID를 지정하면 분야·키워드·제외·기간보다 우선합니다.

기본값: 후보 최대 20편(허용 1–100), 파일당 50 MiB, 수집 중 검사하는 공유 수신 트래픽 예산 250 MiB. 같은 실행에서 앞서 받은 검색 응답과 PDF 재시도 바이트도 예산에 포함됩니다. 중단 전에 최대 한 번의 읽기 블록만큼 한도를 넘을 수 있습니다. 누적 디스크 용량 제한은 아닙니다. 자동 다운로드는 꺼져 있습니다. 기본 논문 확인을 다음부터 생략하려면 아래 설정을 의도적으로 변경하고, false로 돌리면 확인이 복원됩니다. 향후 인용 확장 승인은 별도입니다.

```text
"auto_download": false
```

<!-- section: storage -->
## 저장과 복구

기본값은 셸의 현재 폴더가 아닌 런처 옆 downloads입니다. 프로필의 상대 저장 경로는 프로필 폴더 기준, 명령행 상대 경로는 현재 폴더 기준입니다. 쓰기 불가 위치에서는 오류를 내며 관리자 권한 상승이나 조용한 대체 저장을 하지 않습니다.

작업 상태의 기준은 SQLite입니다. 버전마다 PDF와 공급처·식별자·메타데이터·해시·검증 시각을 담은 JSON을 보관합니다. 수정본이 이전 버전을 덮어쓰지 않습니다. 파일 저장 후 DB 반영 전에 중단된 경우 재검증으로 복구할 수 있습니다. 부분 파일은 재시도 때 삭제하거나 덮어씁니다. 저장소별 OS 잠금으로 동시 쓰기를 막고, 사용자별 arXiv 잠금은 이 프로그램의 서로 다른 저장소 요청도 직렬화하며 각 요청 후 최소 3.1초를 둡니다. 다른 프로그램·기기는 별도로 요청 속도를 조율해야 합니다.

<!-- section: freshness -->
## 최신성과 알려진 제한

Sync는 설정한 검색의 제한된 재조회이며 완전한 증분 미러가 아닙니다. 후보 파일에 보고된 전체 수와 잘림 가능성을 기록합니다. 전체 동기화 워터마크·백그라운드 스케줄러·24시간 최신성 보장·모든 수정본 발견 보장은 없습니다. 넓은 분야는 설정한 범위를 넘을 수 있습니다. 결과는 공급처의 색인과 가용성에 좌우됩니다.

알파에는 데스크톱 GUI·웹 서버·의미 순위·LLM 해석·추천 모델·인용 확장·S2AG/OpenAlex 연결·RAG·KG·GNN이 없습니다. 인용 확장은 선택 기능, 1단계, 별도 미리보기와 상한으로 도입할 예정입니다. arXiv Atom은 완전한 인용 그래프를 제공하지 않습니다.

PDF 검증은 헤더·페이지 트리·읽을 수 있는 스트림을 확인하고 SHA-256을 계산합니다. 악성코드 검사나 시각적 정확성·본문 동일성 보장은 아닙니다. 논문 동일성은 공급처의 버전 URL을 근거로 하며 피드에 없으면 논문 라이선스는 미확인입니다. 파싱은 샌드박스화하지 않았습니다. 파일은 자동으로 열지 않습니다.

<!-- section: telemetry -->
## 로그와 측정

실행마다 events.jsonl, candidates.json, profile.json, papers.csv와 세션 요약을 저장합니다. 이벤트에는 실행·세션 ID, UTC 시각, 소프트웨어·소스 지문, Python/pypdf 버전, 단계 시간, 공급처 호스트, HTTP 상태, 재시도, 전송량, 결과를 기록합니다. 검색 쿼리와 요청 헤더는 이벤트 로그에 복사하지 않습니다. 프로필·후보 파일에는 여전히 관심사와 메타데이터가 있으므로 출력 폴더를 업로드하지 마세요.

요약은 선정 논문 확보율, 실제 시도한 다운로드 검증률, 캐시·복구 파일을 구분합니다. 시간·트래픽·재시도는 현재 세션 기준이며 작업 상태는 재개를 포함한 해당 실행의 현재 상태입니다. 이전 세션 요약도 보존됩니다. CSV 제목에는 수식 삽입 방지를 적용합니다. 종료 코드: 0 성공·미리보기, 1 작업 오류, 2 일부 다운로드 실패, 130 중단.

HTTP 클라이언트는 소켓 제한 20초, 전송 제한 확인 60초, 일시적 오류 최대 3회 시도를 사용합니다. Retry-After가 60초를 넘으면 조기 재시도 대신 오류로 작업을 미룹니다. PDF 리다이렉트는 승인된 HTTPS arXiv 호스트로 제한합니다.

<!-- section: tests -->
## 테스트와 근거

오프라인 테스트는 동봉 논문 대신 생성한 PDF와 합성 메타데이터를 사용합니다. 문서 검사는 섹션 ID·명령 블록·인라인 기술 토큰을 비교하며 의미의 동등성은 별도 검토가 필요합니다. CI는 arXiv에 요청하지 않습니다. 정리한 실제 측정과 플랫폼 미검증 범위는 [검증 기록](docs/VERIFICATION.md)에 있습니다. 첫 2편 실험은 스모크 테스트이며 대표 성공률 벤치마크가 아닙니다.

```text
python -m unittest discover -s tests -v
python scripts/check_readme.py
```

<!-- section: license -->
## 라이선스와 연락처

자체 코드는 PolyForm Noncommercial 1.0.0의 소스 공개형이며 OSI 승인 오픈소스 라이선스가 아닙니다. 표준 [LICENSE](LICENSE)가 적용됩니다. 지정된 기관에는 라이선스 자체의 허용 조항이 적용되며 허용 범위 밖의 상업적 사용은 해당 권리자의 별도 허락이 필요합니다. [연락처](CONTACT.md), [외부 고지](THIRD_PARTY_NOTICES.md), [라이선스 검토](docs/LICENSE_REVIEW.md)를 참고하세요.

원격 저장소 생성 후 질문·허락 요청은 저장소 Issues를 사용합니다. 비공개 중에는 초대한 협업자만 사용할 수 있습니다. 개인 이메일은 임의로 만들지 않았습니다. public 전환 전에 비공개 연락 수단을 추가로 정해야 합니다. 이슈 등록 자체가 허락은 아닙니다.

arXiv PDF와 향후 코퍼스·모델에는 별도 권리가 적용되며 코드 라이선스가 논문 재배포를 허용하지 않습니다. PDF·코퍼스·개인 프로필·로그·키를 커밋하지 마세요. 향후 API 비용을 지불해도 유료 논문 이용권이 자동 제공되지 않습니다. 유료 공급처는 활성화하지 않았습니다.

<!-- section: roadmap -->
## 개발 순서

1. 수집·복구 측정을 확대하고 Windows 10/11과 Ubuntu 22.04를 검증합니다.
2. 설명 가능한 키워드 관련성 기준선 다음 제목·초록 의미 순위를 추가합니다.
3. 정책 확인 후 공급처를 다각화하고 1단계 인용 확장을 구현합니다.
4. 같은 엔진·프로필 구조 위에 설문형 데스크톱 GUI를 추가합니다.
5. LLM 입력·RAG·KG·GNN을 탐색하고 안정화 이후에만 웹서비스를 고려합니다.

[결정 사항](docs/DECISIONS.md)과 [기여 규칙](CONTRIBUTING.md)을 참고하세요. 한영 README는 기능·기본값·제한사항·검증 근거가 동일하도록 함께 변경해야 합니다.

<!-- section: compass -->
## 프로젝트 기준서

상세 명세, 결정 사항, 검증 근거, 한계와 다음 작업은 [프로젝트 기준서](docs/PROJECT_COMPASS.ko.md)를 읽어주세요. 레거시 출력 인코딩에서 표현할 수 없는 문자는 중단 대신 이스케이프하여 출력합니다. 현재 오프라인 테스트는 20개입니다.
