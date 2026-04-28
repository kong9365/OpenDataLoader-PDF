from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def normalize_text(text: str) -> str:
    """공백과 특수 공백을 정규화합니다."""

    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_after_label(text: str, label: str, stop_labels: Optional[List[str]] = None) -> str:
    """라벨 뒤 값을 추출합니다.

    PDF 추출 결과는 라벨과 값이 줄바꿈으로 분리될 수 있어 보수적으로 처리합니다.
    """

    stop_labels = stop_labels or []
    pattern = re.compile(rf"{re.escape(label)}\s*[:：]?\s*(.*)", re.IGNORECASE)
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        m = pattern.search(line)
        if m:
            value = m.group(1).strip()
            if value:
                return value
            collected: List[str] = []
            for next_line in lines[i + 1 :]:
                if any(next_line.startswith(stop) for stop in stop_labels):
                    break
                collected.append(next_line)
                if len(collected) >= 3:
                    break
            return " ".join(collected).strip()
    return ""


def extract_common_fields(text: str) -> Dict[str, Any]:
    """시험일지에서 공통 필드를 추출합니다."""

    text = normalize_text(text)
    stop = ["시험기준", "시험결과", "시험자", "확인자", "대분류", "시험항목", "●"]

    fields: Dict[str, Any] = {
        "item_name": extract_after_label(text, "시험항목", stop),
        "category": extract_after_label(text, "대분류", stop),
        "specification": extract_after_label(text, "시험기준", ["시험결과", "시험자", "확인자", "대분류", "●"]),
        "result": extract_after_label(text, "시험결과", ["시험자", "확인자", "대분류", "시험항목", "●"]),
        "analyst": extract_after_label(text, "시험자", ["시험일자", "확인자", "확인일자", "대분류"]),
        "reviewer": extract_after_label(text, "확인자", ["확인일자", "대분류", "시험항목"]),
    }

    # 날짜는 문서 내 위치가 일정하지 않을 수 있으므로 전체에서 추출합니다.
    dates = re.findall(r"20\d{2}[-./]\d{2}[-./]\d{2}", text)
    if dates:
        fields["dates"] = dates

    return fields


def extract_numbers(text: str) -> List[float]:
    """텍스트에서 숫자 목록을 추출합니다."""

    values: List[float] = []
    for match in re.finditer(r"(?<![A-Za-z0-9])[-+]?\d+(?:\.\d+)?(?![A-Za-z0-9])", text):
        try:
            values.append(float(match.group()))
        except ValueError:
            continue
    return values


def extract_data_values(text: str) -> Dict[str, float]:
    """전자저울 Raw 데이터의 Data 01, Data 02 값을 추출합니다."""

    values: Dict[str, float] = {}
    for m in re.finditer(r"Data\s*(\d{1,3})\s*[:：]\s*([-+]?\d+(?:\.\d+)?)", text, re.IGNORECASE):
        values[f"Data {int(m.group(1)):02d}"] = float(m.group(2))
    return values


def extract_sample_values(text: str) -> Dict[str, float]:
    """시험일지의 Sample 1, Sample 2 값을 추출합니다."""

    values: Dict[str, float] = {}
    for m in re.finditer(r"Sample\s*(\d{1,3})\s+([-+]?\d+(?:\.\d+)?)", text, re.IGNORECASE):
        values[f"Sample {int(m.group(1))}"] = float(m.group(2))
    return values


def extract_range(text: str) -> Optional[tuple[float, float]]:
    """427.0 ~ 473.0 형태의 범위를 추출합니다."""

    m = re.search(r"([-+]?\d+(?:\.\d+)?)\s*[~～]\s*([-+]?\d+(?:\.\d+)?)", text)
    if not m:
        return None
    return float(m.group(1)), float(m.group(2))


def detect_raw_type(text: str) -> str:
    """Raw 데이터 종류를 대략 분류합니다."""

    lower = text.lower()
    if "balance" in lower or "전자저울" in text or re.search(r"Data\s*\d+\s*:", text):
        return "balance"
    if "sequence summary report" in lower or "hplc" in lower or "sample statistics" in lower:
        return "hplc"
    if "abs" in lower or "wavelength" in lower or "photometric" in lower:
        return "uv"
    if "camag" in lower or "tlc" in lower:
        return "tlc"
    if "첨부파일" in text:
        return "image_or_attachment"
    return "unknown"


def extract_raw_values(text: str) -> Dict[str, Any]:
    """Raw 페이지에서 검증에 사용할 값을 추출합니다."""

    raw_type = detect_raw_type(text)
    values: Dict[str, Any] = {"raw_type": raw_type}

    data_values = extract_data_values(text)
    if data_values:
        values["data_values"] = data_values

    sample_values = extract_sample_values(text)
    if sample_values:
        values["sample_values"] = sample_values

    if raw_type in {"hplc", "uv"}:
        values["numbers"] = extract_numbers(text)

    return values
