from __future__ import annotations

import json
from pathlib import Path
from typing import List

import pandas as pd
from jinja2 import Template

from .models import CheckResult, TestSection
from .section_parser import sections_to_dict


HTML_TEMPLATE = """
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>시험성적서 자동 검토 보고서</title>
  <style>
    body { font-family: Arial, 'Malgun Gothic', sans-serif; margin: 24px; color: #222; }
    h1 { margin-bottom: 8px; }
    .summary { display: flex; gap: 12px; margin: 20px 0; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 12px 16px; min-width: 110px; }
    table { border-collapse: collapse; width: 100%; margin-top: 16px; }
    th, td { border: 1px solid #ddd; padding: 8px; vertical-align: top; font-size: 13px; }
    th { background: #f5f5f5; }
    .PASS { color: #0a7a2f; font-weight: bold; }
    .FAIL { color: #b00020; font-weight: bold; }
    .NO_RAW { color: #8a5a00; font-weight: bold; }
    .MANUAL_REVIEW { color: #0057b8; font-weight: bold; }
    pre { white-space: pre-wrap; word-break: break-all; max-width: 520px; }
  </style>
</head>
<body>
  <h1>시험성적서 자동 검토 보고서</h1>
  <p>시험항목별 시험일지와 Raw 데이터 비교 결과입니다.</p>

  <div class="summary">
    {% for key, value in summary.items() %}
    <div class="card"><strong>{{ key }}</strong><br>{{ value }}</div>
    {% endfor %}
  </div>

  <table>
    <thead>
      <tr>
        <th>시험항목</th>
        <th>대분류</th>
        <th>상태</th>
        <th>메시지</th>
        <th>근거 페이지</th>
        <th>상세</th>
      </tr>
    </thead>
    <tbody>
      {% for row in results %}
      <tr>
        <td>{{ row.item_name }}</td>
        <td>{{ row.category }}</td>
        <td class="{{ row.status }}">{{ row.status }}</td>
        <td>{{ row.message }}</td>
        <td>{{ row.evidence_pages }}</td>
        <td><pre>{{ row.details_json }}</pre></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
"""


def result_rows(results: List[CheckResult]) -> list[dict]:
    """CheckResult를 보고서용 행으로 변환합니다."""

    rows: list[dict] = []
    for result in results:
        rows.append(
            {
                "item_name": result.item_name,
                "category": result.category,
                "status": result.status,
                "message": result.message,
                "evidence_pages": ", ".join(map(str, result.evidence_pages)),
                "journal_values": json.dumps(result.journal_values, ensure_ascii=False, default=str),
                "raw_values": json.dumps(result.raw_values, ensure_ascii=False, default=str),
                "details_json": json.dumps(result.details, ensure_ascii=False, indent=2, default=str),
            }
        )
    return rows


def make_summary(results: List[CheckResult]) -> dict[str, int]:
    """상태별 집계."""

    summary = {"TOTAL": len(results), "PASS": 0, "FAIL": 0, "NO_RAW": 0, "MANUAL_REVIEW": 0}
    for result in results:
        summary[result.status] = summary.get(result.status, 0) + 1
    return summary


def write_excel_report(results: List[CheckResult], output_path: str | Path) -> Path:
    """Excel 검토 보고서를 생성합니다."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = result_rows(results)
    df = pd.DataFrame(rows)
    summary_df = pd.DataFrame([{"status": k, "count": v} for k, v in make_summary(results).items()])

    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="Summary", index=False)
        df.to_excel(writer, sheet_name="Review_Result", index=False)

        workbook = writer.book
        for sheet in workbook.worksheets:
            sheet.freeze_panes = "A2"
            for column_cells in sheet.columns:
                max_length = max(len(str(cell.value or "")) for cell in column_cells)
                sheet.column_dimensions[column_cells[0].column_letter].width = min(max(max_length + 2, 12), 60)

    return output_path


def write_html_report(results: List[CheckResult], output_path: str | Path) -> Path:
    """HTML 검토 보고서를 생성합니다."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = result_rows(results)
    html = Template(HTML_TEMPLATE).render(results=rows, summary=make_summary(results))
    output_path.write_text(html, encoding="utf-8")
    return output_path


def write_debug_files(sections: List[TestSection], output_dir: str | Path) -> None:
    """섹션 파싱 결과를 JSON으로 저장합니다."""

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "sections.json").write_text(
        json.dumps(sections_to_dict(sections), ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
