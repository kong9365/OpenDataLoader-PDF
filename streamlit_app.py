from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from coa_reviewer.pdf_loader import load_pdf
from coa_reviewer.report import make_summary, result_rows, write_debug_files, write_excel_report, write_html_report
from coa_reviewer.section_parser import parse_sections
from coa_reviewer.validators import validate_sections


st.set_page_config(page_title="시험성적서 자동 검토", layout="wide")
st.title("시험성적서 자동 검토 시스템")
st.caption("PDF 시험성적서를 업로드하면 시험항목별 시험일지와 Raw 데이터를 비교합니다.")

uploaded_file = st.file_uploader("시험성적서 PDF 업로드", type=["pdf"])
use_opendataloader = st.checkbox("OpenDataLoader PDF 우선 사용", value=True)
use_hybrid = st.checkbox("Hybrid/OCR 모드 사용", value=False)

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        pdf_path = tmp_dir / uploaded_file.name
        pdf_path.write_bytes(uploaded_file.getbuffer())
        output_dir = tmp_dir / "review_output"

        with st.spinner("PDF 분석 및 검토 중입니다..."):
            pages = load_pdf(
                pdf_path,
                output_dir,
                prefer_opendataloader=use_opendataloader,
                use_hybrid=use_hybrid,
            )
            sections = parse_sections(pages)
            results = validate_sections(sections)
            write_debug_files(sections, output_dir)
            excel_path = write_excel_report(results, output_dir / "coa_review_report.xlsx")
            html_path = write_html_report(results, output_dir / "coa_review_report.html")

        summary = make_summary(results)
        cols = st.columns(len(summary))
        for col, (key, value) in zip(cols, summary.items()):
            col.metric(key, value)

        rows = result_rows(results)
        st.subheader("시험항목별 검토 결과")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

        st.download_button(
            "Excel 보고서 다운로드",
            data=excel_path.read_bytes(),
            file_name="coa_review_report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        st.download_button(
            "HTML 보고서 다운로드",
            data=html_path.read_bytes(),
            file_name="coa_review_report.html",
            mime="text/html",
        )

        with st.expander("파싱된 시험항목 구조 확인"):
            for section in sections:
                st.markdown(f"### {section.item_name}")
                st.write(
                    {
                        "대분류": section.category,
                        "시작 페이지": section.start_page,
                        "종료 페이지": section.end_page,
                        "Raw 페이지": [raw.page_number for raw in section.raw_pages],
                    }
                )
else:
    st.info("왼쪽 또는 위 영역에서 PDF 파일을 업로드하세요.")
