"""Requirement traceability audit trail."""

from __future__ import annotations

from typing import Any


def build_traceability_matrix(
    compliance_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    trace: list[dict[str, Any]] = []
    for row in compliance_rows:
        if not isinstance(row, dict):
            continue
        evidence_ids = [
            e.get("evidence_id")
            for e in (row.get("evidence") or [])
            if isinstance(e, dict) and e.get("evidence_id")
        ]
        trace.append(
            {
                "requirement_id": row.get("requirement_ref"),
                "category": row.get("category"),
                "evidence_ids": evidence_ids,
                "proposal_section": row.get("proposal_section"),
                "compliance_status": row.get("compliance_status"),
                "gap_status": row.get("gap_status"),
                "confidence_score": row.get("confidence_score"),
            }
        )
    return trace
