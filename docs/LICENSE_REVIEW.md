# License review / 라이선스 검토

Review date: 2026-09-30. Scope: declared pinned dependencies and provider policy. This is not a complete legal opinion, vulnerability audit, or approval to redistribute papers.

확인일: 2026-09-30. 범위: 고정된 의존성과 공급처 정책. 종합 법률 의견·취약점 감사·논문 재배포 허락을 의미하지 않습니다.

| Component | Version | License / policy | Handling |
|---|---|---|---|
| Original project code | 0.1.0a1 | PolyForm-Noncommercial-1.0.0 | Standard LICENSE; commercial use requires separate permission where not granted by the license |
| Python standard library | Python 3.12 target | PSF license and bundled component notices | User installs interpreter; not bundled here |
| pypdf | 6.10.0 | BSD-3-Clause | Only external runtime dependency; license copied unchanged to licenses/ |
| setuptools | 84.0.0 | MIT | Optional packaging build backend; license copied; not shipped as project source |
| arXiv metadata | API records | CC0 descriptive metadata per API terms | Provenance retained |
| arXiv PDF | Per article | Individual rights; redistribution not universally granted | Download locally, not committed or bundled |

Python 3.12 has no mandatory transitive runtime dependency for the pinned pypdf base installation. Crypto/image/dev extras are not enabled. Build tooling can contain separately licensed vendored components; a future bundled executable must audit and preserve their notices as well as Python/Tcl/Tk/GUI notices. MIT/BSD notices must remain even though original CiteWeave code is noncommercial. GPL/AGPL dependencies are not currently selected; do not assume compatibility with an added noncommercial restriction.

Python 3.12에서 고정한 pypdf 기본 설치에는 필수 전이 실행 의존성이 없습니다. 암호·이미지·개발 extra는 사용하지 않습니다. 빌드 도구에 별도 라이선스 구성요소가 포함될 수 있으므로 실행파일을 묶어 배포할 때 해당 고지와 Python·Tcl/Tk·GUI 고지를 다시 검토해야 합니다. CiteWeave 자체 코드가 비상업 라이선스여도 MIT/BSD 고지는 유지해야 합니다. 현재 GPL/AGPL 의존성은 선택하지 않았으며 비상업 제한과의 호환성을 가정하지 않습니다.

PolyForm explicitly permits specified noncommercial organizations regardless of funding. Do not summarize this as an unconditional ban on all business-funded academic work. Commercial permission is separate; contributor rights must be handled before granting it over their code.

PolyForm은 지정된 비상업 기관의 이용을 자금 출처와 관계없이 허용합니다. 기업 지원 학술 활동까지 전부 금지한다고 설명하면 안 됩니다. 상업적 허락은 별도이며 외부 기여 코드의 권한을 확인해야 합니다.

Sources / 출처:
- https://polyformproject.org/licenses/noncommercial/1.0.0
- https://github.com/polyformproject/polyform-licenses/blob/1.0.0/PolyForm-Noncommercial-1.0.0.md (LICENSE fetched unchanged)
- https://pypi.org/project/pypdf/6.10.0/ and installed wheel METADATA/LICENSE
- https://pypi.org/project/setuptools/84.0.0/ and installed METADATA/LICENSE
- https://docs.python.org/3/license.html
- https://info.arxiv.org/help/api/tou.html

Other providers, S2AG/S2ORC/peS2o, models and GUI libraries are NOT included. Review exact release/access terms before adding them. Source availability or OA discovery does not give blanket full-text redistribution rights.

다른 공급처, S2AG/S2ORC/peS2o, 모델, GUI 라이브러리는 포함하지 않습니다. 추가 전에 정확한 배포판·접근 조건을 검토합니다. 소스 공개나 OA 검색 결과가 원문 전체의 재배포 권리를 부여하지 않습니다.
