# 공개용 Anchor Bridge

- 원자료, 실제 지역별 수치·원장·회귀 기준값, 원본 제출 PDF를 넣지 않는다. 사용자와 정한 공개 범위는 공개용 재편집 PDF와 직접 작성한 합성 데모다.
- `analysis/synthetic.py`가 시연 예시의 원천이다. 실제 데이터에서 값이나 이미지를 복사·익명화하지 않는다.
- `web/`, `documents/`를 편집하고 `scripts/build.py`로 `site/`를 갱신한다. 데모는 외부 의존성 없는 HTML 하나로 유지한다.
- 후보 선정, 운영 승인, 실제 소비 효과를 구분한다. 원본 전체 파이프라인의 재현이라고 주장하지 않는다.
- 검증: unittest → Chrome 검색·필터·인쇄·모바일/오프라인 → PDF 페이지·링크·한글·공개 범위. 결과가 바뀌면 화면을 다시 캡처한다.
- 공개 웹 주소는 `https://soccz.github.io/projects/anchor-bridge/`. 호스팅을 임의로 바꾸지 않는다.
