# Contributing / 기여

This is a private alpha with a working name that conflicts with existing projects. Keep the repository private until the owner decides on branding and public release. Changes to features, commands, defaults, limitations or licensing must update README.md and README.ko.md together with equivalent meaning. Run `python scripts/check_readme.py`; a passing check does not prove translation equivalence.

기존 프로젝트와 이름이 겹치는 private 알파입니다. 소유자가 이름과 공개를 결정할 때까지 비공개를 유지합니다. 기능·명령·기본값·제한사항·라이선스가 바뀌면 README.md와 README.ko.md를 같은 의미로 함께 변경합니다. `python scripts/check_readme.py`를 실행하되, 통과가 의미의 동등성을 보장하지는 않습니다.

Submit only original or properly licensed changes under PolyForm-Noncommercial-1.0.0. Do not submit third-party PDFs, extracted full text, corpora, credentials or private logs. External contributors retain their rights: no blanket relicensing/commercial-permission authority is assumed. Establish a contribution agreement before promising commercial rights covering external contributions.

직접 작성했거나 적절한 권한이 있는 변경만 PolyForm-Noncommercial-1.0.0으로 제출합니다. 외부 PDF·추출 원문·코퍼스·인증 정보·개인 로그를 올리지 않습니다. 외부 기여자의 권리는 유지되며 일괄 재라이선스·상업적 허락 권한을 가정하지 않습니다. 외부 기여분을 포함한 상업적 허락을 약속하기 전에 기여 계약을 정해야 합니다.

Run `python -m unittest discover -s tests -v`. Routine tests use synthetic data and must not call live providers. Live experiments are explicit, limited, and produce local-only raw outputs. Share only sanitized aggregate measurements.

`python -m unittest discover -s tests -v`를 실행합니다. 일반 테스트는 합성 자료를 사용하고 외부 공급처에 요청하지 않습니다. 실제 수집 실험은 명시적으로 소규모로 실행하며 원시 출력은 로컬에만 보관합니다. 공개 기록에는 정리된 집계 수치만 사용합니다.
