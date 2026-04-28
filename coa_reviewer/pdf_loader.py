from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF

from .models import PageData

logger = logging.getLogger(__name__)


def load_pdf_with_pymupdf(pdf_path: str | Path) -> List[PageData]:
    """PyMuPDF로 PDF 텍스트를 페이지 단위로 추출합니다.

    OpenDataLoader PDF가 설치되지 않은 환경에서도 동작하도록 기본 파서로 사용합니다.
    첨부 시험성적서처럼 디지털 텍스트가 포함된 PDF는 이 방식만으로도 1차 검토가 가능합니다.
    """

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF 파일을 찾을 수 없습니다: {pdf_path}")

    pages: List[PageData] = []
    with fitz.open(pdf_path) as doc:
        for index, page in enumerate(doc, start=1):
            text = page.get_text("text") or ""
            pages.append(PageData(page_number=index, text=text, source="pymupdf"))
    return pages


def load_pdf_with_opendataloader(
    pdf_path: str | Path,
    output_dir: str | Path,
    use_hybrid: bool = False,
) -> Optional[List[PageData]]:
    """OpenDataLoader PDF를 사용해 JSON/Markdown으로 변환합니다.

    설치 또는 실행 오류가 있으면 None을 반환하고, 상위 로직에서 PyMuPDF로 fallback합니다.
    opendataloader-pdf의 버전별 출력 구조가 다를 수 있어, 결과 JSON은 가능한 범용적으로 읽습니다.
    """

    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import opendataloader_pdf  # type: ignore
    except Exception as exc:  # pragma: no cover
        logger.warning("OpenDataLoader PDF import 실패: %s", exc)
        return None

    try:
        kwargs = {
            "input_path": [str(pdf_path)],
            "output_dir": str(output_dir),
            "format": "json,markdown",
        }
        if use_hybrid:
            kwargs["hybrid"] = "docling-fast"
        opendataloader_pdf.convert(**kwargs)
    except Exception as exc:  # pragma: no cover
        logger.warning("OpenDataLoader PDF 변환 실패: %s", exc)
        return None

    json_files = sorted(output_dir.glob("*.json"))
    if not json_files:
        logger.warning("OpenDataLoader PDF 결과 JSON을 찾지 못했습니다: %s", output_dir)
        return None

    return _pages_from_opendataloader_json(json_files[0])


def _pages_from_opendataloader_json(json_path: Path) -> List[PageData]:
    """OpenDataLoader JSON을 PageData 목록으로 정규화합니다."""

    data = json.loads(json_path.read_text(encoding="utf-8"))
    pages_map: dict[int, list[str]] = {}

    def visit(obj):
        if isinstance(obj, dict):
            page_no = obj.get("page number") or obj.get("page_number") or obj.get("page")
            content = obj.get("content") or obj.get("text")
            if page_no and content:
                try:
                    pages_map.setdefault(int(page_no), []).append(str(content))
                except ValueError:
                    pass
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for value in obj:
                visit(value)

    visit(data)

    if not pages_map:
        # 출력 구조가 예상과 다르면 전체 JSON을 단일 텍스트로 보존합니다.
        return [PageData(page_number=1, text=json.dumps(data, ensure_ascii=False), source="opendataloader")]

    return [
        PageData(page_number=page_no, text="\n".join(texts), source="opendataloader")
        for page_no, texts in sorted(pages_map.items())
    ]


def load_pdf(
    pdf_path: str | Path,
    work_dir: str | Path,
    prefer_opendataloader: bool = True,
    use_hybrid: bool = False,
) -> List[PageData]:
    """PDF를 페이지 단위 PageData로 로드합니다."""

    if prefer_opendataloader:
        pages = load_pdf_with_opendataloader(pdf_path, Path(work_dir) / "opendataloader", use_hybrid)
        if pages:
            return pages

    return load_pdf_with_pymupdf(pdf_path)
