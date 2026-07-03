"""Post-process and validate generated proposal JSON (v2)."""

from __future__ import annotations

import re
from typing import Any

from apps.intelligence.services.proposal_schemas import VENDOR_PLACEHOLDER

VALID_COMPLIANCE = frozenset(
    {"compliant", "partial", "gap", "planned", "na", "fully", "fully compliant"}
)
VALID_GAP_STATUS = frozenset({"none", "vendor_to_complete", "rfp_only"})
PLACEHOLDER_RE = re.compile(
    r"\[(?:Vendor To Complete|TO BE COMPLETED)[^\]]*\]", re.IGNORECASE
)


def _normalize_compliance(value: Any) -> str:
    raw = str(value or "planned").strip().lower()
    mapping = {
        "fully": "compliant",
        "fully compliant": "compliant",
        "yes": "compliant",
        "compliant": "compliant",
        "partial": "partial",
        "partially": "partial",
        "gap": "gap",
        "na": "na",
        "planned": "planned",
    }
    return mapping.get(raw, "planned")


def _normalize_gap_status(value: Any) -> str:
    raw = str(value or "none").strip().lower()
    if raw in VALID_GAP_STATUS:
        return raw
    if "vendor" in raw or "complete" in raw:
        return "vendor_to_complete"
    return "none"


def _dedupe_matrix_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        key = re.sub(
            r"\s+",
            " ",
            str(row.get("requirement_text") or row.get("requirement") or "").strip().lower(),
        )
        ref = str(row.get("requirement_ref") or "")
        dedupe_key = ref or key
        if not dedupe_key or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        out.append(row)
    return out


def postprocess_proposal(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize proposal JSON from the LLM."""
    if not isinstance(data, dict):
        return {}

    matrix = data.get("compliance_matrix")
    if isinstance(matrix, list):
        cleaned: list[dict[str, Any]] = []
        for i, row in enumerate(matrix):
            if not isinstance(row, dict):
                continue
            ref = str(row.get("requirement_ref") or "").strip()
            if not ref:
                ref = f"REQ-{i + 1:02d}"
            response = str(
                row.get("vendor_response") or row.get("response") or ""
            ).strip()
            status = _normalize_compliance(
                row.get("compliance_status") or row.get("compliance")
            )
            evidence = row.get("evidence") if isinstance(row.get("evidence"), list) else []
            gap_status = _normalize_gap_status(row.get("gap_status"))

            if status == "compliant" and not evidence:
                status = "gap"
                gap_status = "vendor_to_complete"
                if VENDOR_PLACEHOLDER not in response:
                    response = f"{response} {VENDOR_PLACEHOLDER}".strip()

            cleaned.append(
                {
                    "requirement_ref": ref,
                    "category": str(row.get("category") or "TECHNICAL"),
                    "requirement_text": str(
                        row.get("requirement_text") or row.get("requirement") or ""
                    ).strip(),
                    "vendor_response": response,
                    "methodology": str(row.get("methodology") or "").strip(),
                    "evidence": evidence,
                    "compliance_status": status,
                    "gap_status": gap_status,
                    "confidence_score": float(row.get("confidence_score") or 0.0),
                    "sources": row.get("sources")
                    if isinstance(row.get("sources"), list)
                    else [],
                }
            )
        data["compliance_matrix"] = _dedupe_matrix_rows(cleaned)

    gaps = data.get("gaps_and_placeholders")
    if isinstance(gaps, list):
        cleaned_gaps: list[dict[str, Any]] = []
        for gap in gaps:
            if not isinstance(gap, dict):
                continue
            cleaned_gaps.append(
                {
                    "field": str(gap.get("field") or "").strip(),
                    "reason": str(gap.get("reason") or "not_in_profile").strip(),
                    "action": str(
                        gap.get("action") or "Vendor to provide evidence"
                    ).strip(),
                }
            )
        data["gaps_and_placeholders"] = cleaned_gaps
    else:
        data["gaps_and_placeholders"] = []

    for key in (
        "technical_approach",
        "company_overview",
        "why_choose_us",
        "staffing_approach",
        "training_framework",
    ):
        if key not in data or not isinstance(data.get(key), dict):
            if key == "technical_approach":
                data[key] = {"sections": []}
            elif key == "why_choose_us":
                data[key] = {"differentiators": [], "confidence_score": 0.0}
            else:
                data[key] = {"text": "", "confidence_score": 0.0, "evidence": []}

    if not isinstance(data.get("operational_risks"), list):
        data["operational_risks"] = data.pop("risks_and_mitigations", []) or []

    if not isinstance(data.get("assumptions_and_exclusions"), dict):
        data["assumptions_and_exclusions"] = {"assumptions": [], "exclusions": []}

    meta = data.get("meta")
    if not isinstance(meta, dict):
        data["meta"] = {"volumes": ["technical"]}

    return data


def count_placeholders_in_text(data: dict[str, Any]) -> int:
    count = 0

    def _walk(value: Any) -> None:
        nonlocal count
        if isinstance(value, str):
            count += len(PLACEHOLDER_RE.findall(value))
        elif isinstance(value, dict):
            for v in value.values():
                _walk(v)
        elif isinstance(value, list):
            for item in value:
                _walk(item)

    _walk(data)
    return count
