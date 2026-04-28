from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from .pdf_loader import load_pdf
from .report import write_debug_files, write_excel_report, write_html_report
from .section_parser import parse_sections
from .validators import validate_sections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="시험성적서 PDF 자동 검토 시스템")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="PDF 시험성적서를 검토합니다.")
    review.add_argument("pdf", help="검토할 PDF 파일 경로")
    review.add_argument("--out", default="review_output", help="결과 저장 폴더")
    review.add_argument("--no-opendataloader", action="store_true", help="OpenDataLoader PDF를 사용하지 않고 PyMuPDF만 사용")
    review.add_argument("--hybrid", action="store_true", help="OpenDataLoader hybrid 모드 사용")
    review.add_argument("--log-level", default="INFO", help="로그 레벨")
    return parser


def run_review(args: argparse.Namespace) -> None:
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    pdf_path = Path(args.pdf)
    output_dir = Path(args.out)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = load_pdf(
        pdf_path,
        output_dir,
        prefer_opendataloader=not args.no_opendataloader,
        use_hybrid=args.hybrid,
    )

    (output_dir / "parsed_pages.json").write_text(
        json.dumps([page.__dict__ for page in pages], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    sections = parse_sections(pages)
    results = validate_sections(sections)

    write_debug_files(sections, output_dir)
    excel_path = write_excel_report(results, output_dir / "coa_review_report.xlsx")
    html_path = write_html_report(results, output_dir / "coa_review_report.html")

    print(f"검토 완료: {len(results)}개 시험항목")
    print(f"Excel 보고서: {excel_path}")
    print(f"HTML 보고서: {html_path}")


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "review":
        run_review(args)


if __name__ == "__main__":
    main()
