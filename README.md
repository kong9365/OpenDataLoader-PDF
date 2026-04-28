# OpenDataLoader-PDF 기반 시험성적서 자동 검토 시스템

의약품 품질관리팀 시험성적서 PDF를 자동으로 분석하여, 각 시험항목의 시험일지 내용과 이후 첨부되는 Raw 데이터가 일치하는지 검토하는 Python 프로젝트입니다.

## 핵심 기능

- PDF를 페이지 단위로 파싱
- `시험항목` 기준으로 시험일지 섹션 자동 분리
- 각 시험항목 이후에 나오는 Raw 데이터 페이지 자동 매핑
- 전자저울 Raw 데이터의 `Data 01`, `Data 02` 등 측정값 추출
- 시험일지의 질량, 함량, 판정값, 시험결과 수치 추출
- 시험일지 값과 Raw 데이터 값 비교
- 시험항목별 일치, 불일치, 수동검토 필요 항목 분류
- Excel 및 HTML 검토 보고서 생성

## 첨부 PDF 구조 기준

본 프로젝트는 다음과 같은 구조를 우선 지원합니다.

1. 시험일지 페이지
   - 제조번호
   - 품목명
   - 대분류
   - 시험항목
   - 시험기준
   - 시험결과
   - 시험자 / 확인자
   - 시험방법 / 결과 / 비고
2. Raw 데이터 페이지
   - `첨부파일 : 시험항목명 / SP`
   - `첨부파일 : 시험항목명 / STD`
   - `첨부파일 : 시험항목명 / data`
3. 다음 시험항목 페이지가 나오면 새로운 검토 섹션으로 분리

## 설치

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

OpenDataLoader PDF를 사용하려면 Java가 필요할 수 있습니다. 스캔 PDF나 이미지 Raw 데이터까지 처리하려면 hybrid/OCR 옵션을 추가로 설정하세요.

## CLI 실행

```bash
python -m coa_reviewer.cli review "sample.pdf" --out "review_output"
```

실행 후 다음 파일이 생성됩니다.

```text
review_output/
  parsed_pages.json
  sections.json
  coa_review_report.xlsx
  coa_review_report.html
```

## Streamlit 화면 실행

```bash
streamlit run streamlit_app.py
```

## 검토 상태 정의

| 상태 | 의미 |
|---|---|
| PASS | 시험일지 값과 Raw 데이터 값이 허용오차 내 일치 |
| FAIL | Raw 데이터가 존재하지만 시험일지 값과 불일치 |
| NO_RAW | 해당 시험항목 뒤에 Raw 데이터가 없음 |
| MANUAL_REVIEW | 이미지 판독, TLC 사진, 육안 판정 등 자동 수치 비교가 어려움 |

## 권장 운영 방식

초기에는 자동 검토 결과를 최종 판정으로 사용하지 말고, 검토자를 보조하는 1차 점검 도구로 사용하세요. 실제 GMP 문서 검토에서는 PDF 추출 오류, OCR 오인식, 시험법별 예외 규칙이 존재할 수 있으므로 검토자 확인 단계가 필요합니다.

## 프로젝트 구조

```text
coa_reviewer/
  cli.py              # 명령행 실행 진입점
  pdf_loader.py       # OpenDataLoader PDF / PyMuPDF 기반 PDF 파서
  section_parser.py   # 시험항목별 섹션 분리
  extractors.py       # 시험일지 / Raw 데이터 값 추출
  validators.py       # 비교 검증 엔진
  report.py           # Excel / HTML 보고서 생성
  models.py           # 데이터 모델
streamlit_app.py      # 웹 UI
requirements.txt
```

## 향후 확장

- HPLC/UV 장비별 전용 파서 추가
- 시험법별 계산식 검증
- RSD, 평균, 판정값 재계산 검증
- 이미지 Raw 데이터 OCR 및 회전 보정
- QMS API 또는 Google Sheets 연동
