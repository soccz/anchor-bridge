# 앵커 브릿지 · Anchor Bridge

**빵집 다음엔 어디로?** 지역의 대표 업종과 연결할 후보를 고르고, 선정 근거·제외 이유·실행 조건을 함께 남기는 상권 마케팅 서비스 제안입니다.

[프로젝트 소개](https://soccz.github.io/projects/anchor-bridge/) · [합성 데이터 시연](https://soccz.github.io/projects/anchor-bridge/demo/) · [공개 소개서 PDF](site/documents/AnchorBridge_Public_Brief.pdf) · [공개 분석·서비스 설계서 PDF](site/documents/AnchorBridge_Public_Methods.pdf)

![합성 데이터로 후보 검색·판정·검토서를 체험하는 공개 시연](site/assets/demo-preview.png)

협심대의 BC카드 「제1회 AI금융빅데이터플랫폼 소비데이터 활용 분석·아이디어 공모전」 제안을 공개용으로 정리했습니다. 원본은 **4쪽 요약서·81쪽 보고서·단일 HTML MVP**로 구성했습니다. 여기에는 그 설명 흐름과 방법론, 서비스 기능을 담았습니다. 수상·도입·실제 할인 효과를 주장하지 않습니다.

## 무엇을 결정하는가

| 담당자의 질문 | 분석·설계 | 산출물 |
|---|---|---|
| 어디가 강한가? | 규모와 소비구성을 구분해 지역·업종 검토 | 진단과 분석 관점 |
| 무엇을 연결할까? | 앵커 제외 CLQ, 관측·역행·공급·거리 확인 | 후보 및 선정·제외 이유 |
| 효과를 어떻게 알까? | 일반할인과 연결할인의 무작위 비교 제안 | 효과·비용·확대 판단 기준 |

기본 연결, 생활재 예외, 연령 보정의 세 관점을 다룹니다. 후보 조건을 통과한 것과 소비 증가가 검증된 것은 구분합니다. 실제 실험은 수행하지 않았습니다.

## 직접 살펴보기

1. [소개 페이지](https://soccz.github.io/projects/anchor-bridge/)에서 제안과 대표 판단 과정을 읽습니다.
2. [시연](https://soccz.github.io/projects/anchor-bridge/demo/)에서 후보 검색·판정 필터·상세 근거를 살펴봅니다.
3. 후보를 선택해 **검토서 보기 → 인쇄 / PDF로 저장**을 실행합니다.

`site/demo/index.html`은 CSS·스크립트·합성 데이터가 모두 포함된 파일 하나입니다. 다운로드 후 브라우저로 열면 설치·로그인·서버·인터넷 없이 조회와 출력이 작동합니다. 프로젝트 소개 링크를 누를 때만 외부 사이트로 이동합니다.

## 문서

| 공개 문서 | 내용 |
|---|---|
| [아이디어 소개서 · 4쪽](site/documents/AnchorBridge_Public_Brief.pdf) | 제안 개요, 세 분석 관점, 서비스 활용, 실증 계획 |
| [분석·서비스 설계서 · 10쪽](site/documents/AnchorBridge_Public_Methods.pdf) | 입력 정의, LQ·CLQ 계산, 후보 조건, 불확실성, 시제품, 사업화, 비교 실험 |

제출 PDF의 구조와 편집을 살린 **공개용 재편집본**입니다. 원본 81쪽 PDF를 공개하거나 단순히 일부 수치만 가린 버전이 아닙니다. 실제 결과표·이미지·메타데이터를 옮기지 않고 새 문서 소스에서 만들었습니다.

## 공개 데이터와 구현의 범위

모든 시연 지명·수치·판정은 **직접 작성한 합성 예시**입니다. 실제 자료를 추출·익명화·교란한 값이 아닙니다. 공모전 원자료, 실제 파생 원장·회귀 기준값, 원본 제출 PDF는 포함하지 않습니다. [공식 안내](https://abp.bccard.com/dataContest/dataContestDetailPage?contestNo=9000001)는 제공 데이터의 제3자 제공·재배포를 제한합니다.

공개 코드는 제출 분석의 핵심 계산 정의를 옮긴 **작은 재현 예제**입니다. 비공개 전체 분석 파이프라인을 재현하는 패키지는 아닙니다. 시연의 역행 여부는 가정한 입력이며 통계 검정을 실행한 결과가 아닙니다. 혜택 발행·개인 동선 추적·실제 효과측정 기능도 구현하지 않았습니다.

## 실행과 검증

Python 3.10 이상에서 계산·판정 예제는 표준 라이브러리만 사용합니다.

```bash
python -m analysis.synthetic
python -m unittest discover -s tests -v
python scripts/build.py
python -m http.server 8000 --directory site
```

로컬 소개 페이지: `http://localhost:8000/`. 오프라인 MVP는 `site/demo/index.html`을 직접 열어도 됩니다.

공개 PDF 재생성에는 WeasyPrint와 Noto Sans CJK KR 한글 글꼴이 필요합니다. 브라우저 검증에는 Chrome/Chromium, `websocket-client`, `PyMuPDF`를 사용합니다. 화면 캡처 뒤 PDF를 생성합니다.

```bash
python scripts/check_browser.py
python scripts/build.py --pdf
python scripts/check_publication.py
```

검증은 합성 계산값, 잘못된 분모·결측 입력, 제외·보류 분기, 검색·필터·대화상자·출력, 모바일 넘침과 공개 파일 범위를 확인합니다. 실제 데이터 재계산이나 할인 효과 검증을 대신하지 않습니다.

## 구성

```text
analysis/    LQ·CLQ·연령 재가중과 축약 판정, 합성 예시
tests/       계산 정의·오류 입력·후보 분기 테스트
web/         소개 페이지·단일 HTML 데모의 편집 소스
documents/   공개용 소개서·설계서의 인쇄 소스
scripts/     빌드·브라우저·문서 및 공개 범위 검증
site/        배포되는 소개·데모·PDF·화면 이미지
```

본 저장소에는 재사용 라이선스를 별도로 부여하지 않았습니다. 코드·문서 권리와 공모전 데이터의 이용 조건은 별개입니다.
