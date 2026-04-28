from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class PageData:
    """PDF 1페이지의 텍스트 및 메타데이터."""

    page_number: int
    text: str
    source: str = "pymupdf"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RawAttachment:
    """시험항목 뒤에 첨부된 Raw 데이터 페이지."""

    page_number: int
    attachment_name: str
    text: str
    raw_type: str = "unknown"
    extracted_values: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestSection:
    """하나의 시험항목 검토 단위."""

    item_name: str
    category: str
    start_page: int
    end_page: int
    journal_text: str
    raw_pages: List[RawAttachment] = field(default_factory=list)
    fields: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CheckResult:
    """시험항목별 자동 검토 결과."""

    item_name: str
    category: str
    status: str
    message: str
    journal_values: Dict[str, Any] = field(default_factory=dict)
    raw_values: Dict[str, Any] = field(default_factory=dict)
    evidence_pages: List[int] = field(default_factory=list)
    details: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
