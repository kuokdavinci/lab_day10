"""
Cleaning rules: raw export -> cleaned rows + quarantine.

This module keeps baseline behavior and adds measurable rule impacts
for Sprint 2 (non-trivial cleaning rules).

BONUS: Integrated Pydantic for schema validation.
DISTINCTION: Flexible versioning cutoff from environment.
"""

from __future__ import annotations

import csv
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from pydantic import BaseModel, Field, field_validator

# Keep allowlist aligned with contracts/data_contract.yaml
ALLOWED_DOC_IDS = frozenset(
    {
        "policy_refund_v4",
        "sla_p1_2026",
        "it_helpdesk_faq",
        "hr_leave_policy",
    }
)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DMY_SLASH = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_ISO_DATETIME = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
_SPACEY = re.compile(r"\s+")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_NON_WORD = re.compile(r"[^\w\s]+")
_REFUND_14D_PATTERN = re.compile(r"14\s+ng\S*(?:\s+l\S*m)?\s+vi\S*c", flags=re.IGNORECASE)


class CleanedRow(BaseModel):
    """Pydantic model for final stage validation (Bonus)."""
    chunk_id: str = Field(..., min_length=4)
    doc_id: str
    chunk_text: str = Field(..., min_length=8)
    effective_date: str
    exported_at: str

    @field_validator("doc_id")
    @classmethod
    def validate_doc_id(cls, v: str) -> str:
        if v not in ALLOWED_DOC_IDS:
            raise ValueError(f"Unknown doc_id: {v}")
        return v

    @field_validator("effective_date")
    @classmethod
    def validate_iso_date(cls, v: str) -> str:
        if not _ISO_DATE.match(v):
            raise ValueError(f"Date must be YYYY-MM-DD: {v}")
        return v

    @field_validator("exported_at")
    @classmethod
    def validate_iso_datetime(cls, v: str) -> str:
        if not _ISO_DATETIME.match(v):
            raise ValueError(f"Datetime must be ISO format: {v}")
        return v


def _norm_text(s: str) -> str:
    return " ".join((s or "").strip().split()).lower()


def _semantic_text_key(s: str) -> str:
    lowered = _norm_text(s)
    no_punc = _NON_WORD.sub(" ", lowered)
    return _SPACEY.sub(" ", no_punc).strip()


def _stable_chunk_id(doc_id: str, chunk_text: str, seq: int) -> str:
    h = hashlib.sha256(f"{doc_id}|{chunk_text}|{seq}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_{seq}_{h}"


def _normalize_effective_date(raw: str) -> Tuple[str, str]:
    """Return (iso_date, error_reason)."""
    s = (raw or "").strip()
    if not s:
        return "", "empty_effective_date"
    if _ISO_DATE.match(s):
        return s, ""
    m = _DMY_SLASH.match(s)
    if m:
        dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
        return f"{yyyy}-{mm}-{dd}", ""
    return "", "invalid_effective_date_format"


def _normalize_doc_id(raw: str) -> Tuple[str, bool]:
    s = (raw or "").strip().lower()
    aliases = {
        "policy_refund_v4.txt": "policy_refund_v4",
        "refund_policy_v4": "policy_refund_v4",
        "sla_p1_2026.txt": "sla_p1_2026",
        "it_helpdesk_faq.txt": "it_helpdesk_faq",
        "hr_leave_policy.txt": "hr_leave_policy",
    }
    mapped = aliases.get(s, s)
    return mapped, mapped != (raw or "")


def _normalize_exported_at(raw: str) -> Tuple[str, str]:
    s = (raw or "").strip()
    if not s:
        return "", "missing_exported_at"
    if _ISO_DATETIME.match(s):
        return s, ""
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%dT%H:%M:%S"), ""
        except ValueError:
            continue
    return "", "invalid_exported_at_format"


def _normalize_chunk_text(raw: str) -> Tuple[str, bool]:
    s = (raw or "").replace("\ufeff", "")
    s = _CONTROL_CHARS.sub(" ", s)
    s = _SPACEY.sub(" ", s).strip()
    return s, s != (raw or "")


def _strip_refund_migration_note(doc_id: str, text: str) -> Tuple[str, bool]:
    if doc_id != "policy_refund_v4":
        return text, False
    patterns = [
        r"\s*\(ghi ch[úu].*?migration.*?\)\s*",
        r"\s*\(ghi ch[úu].*?policy-v3.*?\)\s*",
    ]
    out = text
    changed = False
    for p in patterns:
        nxt = re.sub(p, " ", out, flags=re.IGNORECASE)
        if nxt != out:
            out = nxt
            changed = True
    out = _SPACEY.sub(" ", out).strip()
    return out, changed


def load_raw_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({k: (v or "").strip() for k, v in r.items()})
    return rows


def clean_rows(
    rows: List[Dict[str, str]],
    *,
    apply_refund_window_fix: bool = True,
    return_impact: bool = False,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]] | Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int]]:
    """
    Return (cleaned, quarantine) or (cleaned, quarantine, impact).
    """
    quarantine: List[Dict[str, Any]] = []
    seen_text: set[str] = set()
    cleaned: List[Dict[str, Any]] = []
    seq = 0

    # Distinction: Read versioning cutoff from ENV instead of hardcoding
    hr_cutoff = os.environ.get("HR_LEAVE_STALE_CUTOFF", "2026-01-01")

    impact: Dict[str, int] = {
        "rule_doc_id_normalized": 0,
        "rule_exported_at_normalized": 0,
        "rule_chunk_text_normalized": 0,
        "rule_refund_migration_note_removed": 0,
        "rule_quarantine_missing_exported_at": 0,
        "rule_quarantine_invalid_exported_at_format": 0,
        "rule_quarantine_short_chunk_text": 0,
        "rule_quarantine_semantic_duplicate_chunk_text": 0,
        "rule_fix_stale_refund_window": 0,
        "rule_pydantic_validation_error": 0,  # New bonus metric
    }

    for raw in rows:
        doc_id_raw = raw.get("doc_id", "")
        doc_id, changed_doc_id = _normalize_doc_id(doc_id_raw)
        if changed_doc_id:
            impact["rule_doc_id_normalized"] += 1

        text_raw = raw.get("chunk_text", "")
        text, text_changed = _normalize_chunk_text(text_raw)
        if text_changed:
            impact["rule_chunk_text_normalized"] += 1

        eff_raw = raw.get("effective_date", "")
        exported_raw = raw.get("exported_at", "")
        exported_at, exported_err = _normalize_exported_at(exported_raw)
        if exported_at and exported_at != exported_raw:
            impact["rule_exported_at_normalized"] += 1

        if exported_err == "missing_exported_at":
            impact["rule_quarantine_missing_exported_at"] += 1
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text, "reason": exported_err})
            continue
        if exported_err == "invalid_exported_at_format":
            impact["rule_quarantine_invalid_exported_at_format"] += 1
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text, "reason": exported_err})
            continue

        if doc_id not in ALLOWED_DOC_IDS:
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text, "reason": "unknown_doc_id"})
            continue

        eff_norm, eff_err = _normalize_effective_date(eff_raw)
        if eff_err == "empty_effective_date":
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text, "reason": "missing_effective_date"})
            continue
        if eff_err == "invalid_effective_date_format":
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text, "reason": eff_err, "effective_date_raw": eff_raw})
            continue

        # Distinction rule: use environmental cutoff
        if doc_id == "hr_leave_policy" and eff_norm < hr_cutoff:
            quarantine.append(
                {
                    **raw,
                    "doc_id": doc_id,
                    "chunk_text": text,
                    "reason": "stale_hr_policy_effective_date",
                    "effective_date_normalized": eff_norm,
                    "cutoff_used": hr_cutoff
                }
            )
            continue

        if not text:
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text, "reason": "missing_chunk_text"})
            continue

        if len(text) < 24:
            impact["rule_quarantine_short_chunk_text"] += 1
            quarantine.append(
                {
                    **raw,
                    "doc_id": doc_id,
                    "chunk_text": text,
                    "reason": "chunk_text_too_short",
                    "chunk_text_len": len(text),
                }
            )
            continue

        key = _semantic_text_key(text)
        if key in seen_text:
            impact["rule_quarantine_semantic_duplicate_chunk_text"] += 1
            quarantine.append({**raw, "doc_id": doc_id, "chunk_text": text, "reason": "duplicate_chunk_text"})
            continue
        seen_text.add(key)

        fixed_text = text
        fixed_text, removed_note = _strip_refund_migration_note(doc_id, fixed_text)
        if removed_note:
            impact["rule_refund_migration_note_removed"] += 1

        if apply_refund_window_fix and doc_id == "policy_refund_v4":
            if _REFUND_14D_PATTERN.search(fixed_text):
                fixed_text = _REFUND_14D_PATTERN.sub("7 ngÃ y lÃ m viá»‡c", fixed_text, count=1)
                fixed_text += " [cleaned: stale_refund_window]"
                impact["rule_fix_stale_refund_window"] += 1

        seq += 1
        
        # Pydantic Final Validation (Bonus point logic)
        try:
            row_dict = {
                "chunk_id": _stable_chunk_id(doc_id, fixed_text, seq),
                "doc_id": doc_id,
                "chunk_text": fixed_text,
                "effective_date": eff_norm,
                "exported_at": exported_at,
            }
            # This will raise ValidationError if failed
            validated = CleanedRow(**row_dict)
            cleaned.append(validated.model_dump())
        except Exception as e:
            impact["rule_pydantic_validation_error"] += 1
            quarantine.append({
                **raw, 
                "doc_id": doc_id, 
                "reason": "pydantic_validation_failed",
                "error_detail": str(e)
            })

    if return_impact:
        return cleaned, quarantine, impact
    return cleaned, quarantine


def write_cleaned_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at\n", encoding="utf-8")
        return
    fieldnames = ["chunk_id", "doc_id", "chunk_text", "effective_date", "exported_at"]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_quarantine_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("chunk_id,doc_id,chunk_text,effective_date,exported_at,reason\n", encoding="utf-8")
        return
    keys: List[str] = []
    seen_k: set[str] = set()
    for r in rows:
        for k in r.keys():
            if k not in seen_k:
                seen_k.add(k)
                keys.append(k)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore", restval="")
        w.writeheader()
        for r in rows:
            w.writerow(r)
