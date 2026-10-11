# Papers With You

[English](README.md)

Papers With You는 arXiv에서 논문을 검색하고 다운로드하는 로컬 CLI 프로그램이다.

사용자가 관심 분야, 키워드, 제외어, 검색 기간 등을 설정하면 조건에 맞는 논문을 검색한다. 검색 결과를 확인한 뒤 필요한 논문을 선택해 다운로드할 수 있다.

## 주요 기능

- arXiv 분야 및 키워드 기반 논문 검색
- 검색 결과 확인 및 다운로드할 논문 선택
- PDF 파일 검증 및 논문 메타데이터 저장
- 중단된 작업 재개 및 기존 다운로드 파일 재사용
- 다운로드 결과와 오류 로그 기록

## 설치

Python 3.12가 필요하며 Windows 10/11과 Ubuntu를 대상으로 개발했다.

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

## 사용 방법

아래 명령어는 가상환경의 Python으로 실행한다.

검색 조건 설정:

```bash
python PapersWithYou.py init
```

논문 검색 및 목록 확인:

```bash
python PapersWithYou.py search
```

논문 검색, 선택 및 다운로드:

```bash
python PapersWithYou.py run
```

실행 기록 확인 및 다운로드 재개:

```bash
python PapersWithYou.py status
python PapersWithYou.py resume --run-id RUN_ID
```

기본 다운로드 경로는 `downloads/`이며, 설정 예시는 [examples/profile.json](examples/profile.json)에서 확인할 수 있다.

## 참고 사항

- 현재는 arXiv만 지원한다.
- 분야는 `cs.AI`, `cs.LG` 등의 arXiv 분류 코드를 사용한다.
- 검색 키워드는 영어로 입력하는 것이 좋다.
- 검색 결과는 최근 수정 순으로 정렬되며 모든 논문의 검색을 보장하지는 않는다.
- 검색 목적과 자유 설명은 저장되지만 아직 논문 순위에 반영되지 않는다.
- GUI, 의미 검색, 개인화 추천 기능은 아직 구현되지 않았다.

## 라이선스

[PolyForm Noncommercial 1.0.0](LICENSE) 라이선스를 적용한다. 라이선스 허용 범위를 벗어나는 상업적 이용은 별도 허락이 필요하다.

외부 의존성의 라이선스는 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)를 참고한다.
