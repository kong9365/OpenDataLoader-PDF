from __future__ import annotations

import re
from typing import List

from .extractors import detect_raw_type, extract_common_fields, extract_raw_values, normalize_text
from .models import PageData, RawAttachment, TestSection


SECTION_KEYWORD = "시험항목"
ATTACHMENT_KEYWORD = "첨부파일"


def _is_journal_page(text: str) -> bool:
    """시험일지 본문 페이지 여부를 판단합니다."""

    return SECTION_KEYWORD in text and ("시험기준" in text or "시험결과" in text or "대분류" in text)


def _extract_item_name(text: str) -> str:
    """시험항목명을 보수적으로 추출합니다."""

    fields = extract_common_fields(text)
    item = fields.get("item_name") or ""
    if item:
        return str(item).strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for i, line in enumerate(lines):
        if line.startswith("시험항목"):
            tail = line.replace("시험항목", "", 1).strip(" :：")
            if tail:
                return tail
            if i + 1 < len(lines):
                return lines[i + 1]
    return "미확인 시험항목"


def _extract_attachment_name(text: str) -> str:
    """첨부파일 이름을 추출합니다."""

    for line in text.splitlines():
        if ATTACHMENT_KEYWORD in line:
            return line.split(":", 1)[-1].strip() if ":" in line else line.replace(ATTACHMENT_KEYWORD, "").strip()
    return ""


def parse_sections(pages: List[PageData]) -> List[TestSection]:
    """페이지 목록을 시험항목 단위 섹션으로 분리합니다.

    규칙:
    - `시험항목`이 포함된 페이지를 시험일지 시작으로 본다.
    - 다음 시험일지 페이지 전까지의 페이지를 해당 시험항목의 Raw 첨부로 묶는다.
    - Raw 데이터가 없는 경우 raw_pages는 빈 목록이다.
    """

    sections: List[TestSection] = []
    current: TestSection | None = None

    for page in pages:
        text = normalize_text(page.text)
        if not text:
            continue

        if _is_journal_page(text):
            if current is not None:
                current.end_page = page.page_number - 1
                sections.append(current)

            fields = extract_common_fields(text)
            item_name = str(fields.get("item_name") or _extract_item_name(text)).strip()
            category = str(fields.get("category") or "").strip()

            current = TestSection(
                item_name=item_name or "미확인 시험항목",
                category=category,
                start_page=page.page_number,
                end_page=page.page_number,
                journal_text=text,
                fields=fields,
            )
        else:
            if current is None:
                continue

            attachment_name = _extract_attachment_name(text)
            raw_type = detect_raw_type(text)
            extracted_values = extract_raw_values(text)
            current.raw_pages.append(
                RawAttachment(
                    page_number=page.page_number,
                    attachment_name=attachment_name,
                    text=text,
                    raw_type=raw_type,
                    extracted_values=extracted_values,
                )
            )
            current.end_page = page.page_number

    if current is not None:
        sections.append(current)

    return sections


def sections_to_dict(sections: List[TestSection]) -> list[dict]:
    """디버깅 저장용 dict 변환."""

    result: list[dict] = []
    for section in sections:
        result.append(
            {
                "item_name": section.item_name,
                "category": section.category,
                "start_page": section.start_page,
                "end_page": section.end_page,
                "fields": section.fields,
                "raw_pages": [
                    {
                        "page_number": raw.page_number,
                        "attachment_name": raw.attachment_name,
                        "raw_type": raw.raw_type,
                        "extracted_values": raw.extracted_values,
                    }
                    for raw in section.raw_pages
                ],
            }
        )
    return result
