from __future__ import annotations

import math
from typing import Any, Dict, List

from .extractors import extract_data_values, extract_numbers, extract_range, extract_sample_values
from .models import CheckResult, TestSection


DEFAULT_ABS_TOLERANCE = 0.05
DEFAULT_REL_TOLERANCE = 0.001


def nearly_equal(a: float, b: float, abs_tol: float = DEFAULT_ABS_TOLERANCE, rel_tol: float = DEFAULT_REL_TOLERANCE) -> bool:
    """수치 비교용 허용오차 함수."""

    return math.isclose(a, b, abs_tol=abs_tol, rel_tol=rel_tol)


def _flatten_raw_data_values(section: TestSection) -> Dict[str, float]:
    """섹션의 모든 Raw Data xx 값을 평탄화합니다."""

    result: Dict[str, float] = {}
    index = 1
    for raw in section.raw_pages:
        data_values = raw.extracted_values.get("data_values", {})
        for _, value in data_values.items():
            result[f"Raw {index:02d}"] = float(value)
            index += 1
    return result


def _all_raw_numbers(section: TestSection) -> List[float]:
    """Raw 페이지에서 추출 가능한 모든 숫자를 모읍니다."""

    numbers: List[float] = []
    for raw in section.raw_pages:
        data_values = raw.extracted_values.get("data_values", {})
        numbers.extend(float(v) for v in data_values.values())
        sample_values = raw.extracted_values.get("sample_values", {})
        numbers.extend(float(v) for v in sample_values.values())
        numbers.extend(float(v) for v in raw.extracted_values.get("numbers", [])[:200])
    return numbers


def validate_section(section: TestSection) -> CheckResult:
    """시험항목별 검증을 수행합니다.

    1차 버전은 범용 검증 엔진입니다.
    - 전자저울 Raw 데이터가 있으면 시험일지의 Sample 값 또는 질량/용량 값과 비교합니다.
    - 시험기준에 범위가 있으면 시험결과 수치가 범위 내인지 확인합니다.
    - TLC/성상/붕해 사진처럼 이미지·육안 판정 성격은 수동검토로 분류합니다.
    """

    journal_text = section.journal_text
    journal_numbers = extract_numbers(journal_text)
    journal_samples = extract_sample_values(journal_text)
    journal_range = extract_range(journal_text)
    raw_values = _flatten_raw_data_values(section)
    raw_numbers = _all_raw_numbers(section)

    journal_values: Dict[str, Any] = {
        "fields": section.fields,
        "sample_values": journal_samples,
        "range": journal_range,
        "numbers_count": len(journal_numbers),
    }

    raw_values_dict: Dict[str, Any] = {
        "raw_data_values": raw_values,
        "raw_numbers_count": len(raw_numbers),
        "raw_pages": [raw.page_number for raw in section.raw_pages],
    }

    details: List[Dict[str, Any]] = []

    if not section.raw_pages:
        return CheckResult(
            item_name=section.item_name,
            category=section.category,
            status="NO_RAW",
            message="해당 시험항목 뒤에 Raw 데이터 페이지가 없습니다.",
            journal_values=journal_values,
            raw_values=raw_values_dict,
            evidence_pages=[section.start_page],
            details=details,
        )

    # 전자저울 Raw 데이터 비교: Raw Data 값이 시험일지 숫자 목록 안에 존재하는지 확인합니다.
    if raw_values:
        matched = 0
        failed_items: List[Dict[str, Any]] = []
        for raw_key, raw_value in raw_values.items():
            found = any(nearly_equal(raw_value, journal_value) for journal_value in journal_numbers)
            details.append(
                {
                    "rule": "balance_raw_value_in_journal",
                    "raw_key": raw_key,
                    "raw_value": raw_value,
                    "matched": found,
                }
            )
            if found:
                matched += 1
            else:
                failed_items.append({"raw_key": raw_key, "raw_value": raw_value})

        if matched == len(raw_values):
            status = "PASS"
            message = "전자저울 Raw 데이터 측정값이 시험일지 기재값과 모두 일치합니다."
        elif matched > 0:
            status = "FAIL"
            message = f"전자저울 Raw 데이터 {len(raw_values)}개 중 {matched}개만 시험일지와 일치합니다."
        else:
            status = "FAIL"
            message = "전자저울 Raw 데이터 측정값이 시험일지 기재값에서 확인되지 않습니다."

        # 범위 기준이 있으면 시험결과 대표값의 범위 적합성도 추가 확인합니다.
        if journal_range:
            low, high = journal_range
            in_range_values = [n for n in journal_numbers if low <= n <= high]
            details.append(
                {
                    "rule": "result_within_spec_range",
                    "range": [low, high],
                    "matched_values": in_range_values[:20],
                    "matched": bool(in_range_values),
                }
            )
        return CheckResult(
            item_name=section.item_name,
            category=section.category,
            status=status,
            message=message,
            journal_values=journal_values,
            raw_values=raw_values_dict,
            evidence_pages=[section.start_page] + [raw.page_number for raw in section.raw_pages],
            details=details,
        )

    # HPLC/UV 등 Raw 수치가 있으나 직접 매칭이 어려운 경우
    if raw_numbers:
        if journal_range:
            low, high = journal_range
            in_range_values = [n for n in journal_numbers if low <= n <= high]
            details.append(
                {
                    "rule": "journal_result_within_range",
                    "range": [low, high],
                    "matched_values": in_range_values[:20],
                    "matched": bool(in_range_values),
                }
            )
            status = "PASS" if in_range_values else "FAIL"
            message = "시험일지 결과값이 기준 범위 내에 있습니다." if in_range_values else "시험일지 결과값이 기준 범위 내에서 확인되지 않습니다."
        else:
            status = "MANUAL_REVIEW"
            message = "Raw 수치는 추출되었으나 시험법별 계산식 검증 규칙이 필요합니다."

        return CheckResult(
            item_name=section.item_name,
            category=section.category,
            status=status,
            message=message,
            journal_values=journal_values,
            raw_values=raw_values_dict,
            evidence_pages=[section.start_page] + [raw.page_number for raw in section.raw_pages],
            details=details,
        )

    return CheckResult(
        item_name=section.item_name,
        category=section.category,
        status="MANUAL_REVIEW",
        message="이미지, TLC 사진, 육안판정 등 자동 수치 비교가 어려워 수동검토가 필요합니다.",
        journal_values=journal_values,
        raw_values=raw_values_dict,
        evidence_pages=[section.start_page] + [raw.page_number for raw in section.raw_pages],
        details=details,
    )


def validate_sections(sections: List[TestSection]) -> List[CheckResult]:
    """전체 섹션 검증."""

    return [validate_section(section) for section in sections]
