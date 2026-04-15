"""
Simple expectation suite for Day 10 pipeline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ExpectationResult:
    name: str
    passed: bool
    severity: str  # "warn" | "halt"
    detail: str


def run_expectations(cleaned_rows: List[Dict[str, Any]]) -> Tuple[List[ExpectationResult], bool]:
    """
    Return (results, should_halt).

    should_halt = True if any halt-severity expectation fails.
    """
    results: List[ExpectationResult] = []

    # E1: at least one row after clean
    ok = len(cleaned_rows) >= 1
    results.append(ExpectationResult("min_one_row", ok, "halt", f"cleaned_rows={len(cleaned_rows)}"))

    # E2: no empty doc_id
    bad_doc = [r for r in cleaned_rows if not (r.get("doc_id") or "").strip()]
    ok2 = len(bad_doc) == 0
    results.append(ExpectationResult("no_empty_doc_id", ok2, "halt", f"empty_doc_id_count={len(bad_doc)}"))

    # E3: refund policy should not contain stale 14-day window
    bad_refund = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4"
        and re.search(r"14\s+ng", (r.get("chunk_text") or "").lower())
    ]
    ok3 = len(bad_refund) == 0
    results.append(ExpectationResult("refund_no_stale_14d_window", ok3, "halt", f"violations={len(bad_refund)}"))

    # E4: minimum chunk length
    short = [r for r in cleaned_rows if len((r.get("chunk_text") or "")) < 8]
    ok4 = len(short) == 0
    results.append(ExpectationResult("chunk_min_length_8", ok4, "warn", f"short_chunks={len(short)}"))

    # E5: effective_date should be ISO format
    iso_bad = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", (r.get("effective_date") or "").strip())
    ]
    ok5 = len(iso_bad) == 0
    results.append(ExpectationResult("effective_date_iso_yyyy_mm_dd", ok5, "halt", f"non_iso_rows={len(iso_bad)}"))

    # E6: HR leave policy should not contain stale "10-day annual leave" marker
    bad_hr_annual = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "hr_leave_policy" and "10 ngÃ y phÃ©p nÄƒm" in (r.get("chunk_text") or "")
    ]
    ok6 = len(bad_hr_annual) == 0
    results.append(ExpectationResult("hr_leave_no_stale_10d_annual", ok6, "halt", f"violations={len(bad_hr_annual)}"))

    # E7: exported_at should be ISO datetime after clean (for reliable freshness/lineage)
    bad_exported_at = [
        r
        for r in cleaned_rows
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$", (r.get("exported_at") or "").strip())
    ]
    ok7 = len(bad_exported_at) == 0
    results.append(ExpectationResult("exported_at_iso_datetime", ok7, "halt", f"invalid_exported_at={len(bad_exported_at)}"))

    # E8: refund chunks should not retain migration notes in cleaned output
    bad_refund_note = [
        r
        for r in cleaned_rows
        if r.get("doc_id") == "policy_refund_v4" and "migration" in (r.get("chunk_text") or "").lower()
    ]
    ok8 = len(bad_refund_note) == 0
    results.append(ExpectationResult("refund_no_migration_note", ok8, "warn", f"violations={len(bad_refund_note)}"))

    halt = any(not r.passed and r.severity == "halt" for r in results)
    return results, halt
