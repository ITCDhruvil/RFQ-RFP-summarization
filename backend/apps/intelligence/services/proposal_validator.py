"""Post-generation validation — hallucination and quality gates (v2.1)."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from django.conf import settings

from apps.intelligence.services.proposal_schemas import (
    VENDOR_PLACEHOLDER,
    ValidationViolation,
)

_ECHO_THRESHOLD = 0.72
_BLOCKING_CODES = frozenset(
    {
        "requirement_echo",
        "unjustified_compliance",
        "unverified_certification",
        "matrix_coverage_low",
    }
)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _extract_profile_cert_keywords(profile: dict) -> set[str]:
    keys: set[str] = set()
    for cert in profile.get("certifications") or []:
        for token in re.findall(r"[a-z0-9]+", str(cert).lower()):
            if len(token) >= 3:
                keys.add(token)
    assets = profile.get("knowledge_assets") or {}
    if isinstance(assets, dict):
        for cert in assets.get("certifications") or []:
            for token in re.findall(r"[a-z0-9]+", str(cert).lower()):
                if len(token) >= 3:
                    keys.add(token)
    return keys


def _walk_strings(obj: Any, path: str = "") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(obj, str):
        out.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            child_path = f"{path}.{k}" if path else k
            if isinstance(v, str):
                out.append((child_path, v))
            else:
                out.extend(_walk_strings(v, child_path))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            out.extend(_walk_strings(item, f"{path}[{i}]"))
    return out


def validate_proposal(
    data: dict[str, Any],
    profile: dict,
    *,
    requirement_count: int = 0,
    strict: bool | None = None,
) -> tuple[list[ValidationViolation], dict[str, Any]]:
    if strict is None:
        strict = getattr(settings, "PROPOSAL_STRICT_VALIDATION", True)

    violations: list[ValidationViolation] = []
    allowed_cert_tokens = _extract_profile_cert_keywords(profile)
    matrix = data.get("compliance_matrix") or []
    echo_count = 0
    unjustified_compliant = 0

    for i, row in enumerate(matrix):
        if not isinstance(row, dict):
            continue
        req_text = str(row.get("requirement_text") or "")
        response = str(row.get("vendor_response") or row.get("response") or "")
        loc = f"compliance_matrix[{i}]"

        sim = _similarity(req_text, response)
        if sim >= _ECHO_THRESHOLD and VENDOR_PLACEHOLDER not in response:
            echo_count += 1
            violations.append(
                ValidationViolation(
                    code="requirement_echo",
                    message=(
                        f"Response mirrors requirement (similarity {sim:.0%}). "
                        "Must explain HOW, not restate WHAT."
                    ),
                    location=loc,
                    severity="error",
                )
            )

        status = str(
            row.get("compliance_status") or row.get("compliance") or ""
        ).lower()
        evidence = row.get("evidence") or []

        if status in ("compliant", "fully") and not evidence:
            if VENDOR_PLACEHOLDER not in response:
                unjustified_compliant += 1
                violations.append(
                    ValidationViolation(
                        code="unjustified_compliance",
                        message="Marked compliant without evidence references",
                        location=loc,
                        severity="error",
                    )
                )

    for path, text in _walk_strings(data):
        if any(skip in path for skip in ("_pipeline", "_meta", "traceability")):
            continue
        iso_match = re.search(r"iso\s*\d+", text, re.I)
        if iso_match:
            cert_tokens = set(re.findall(r"[a-z0-9]+", iso_match.group().lower()))
            if not (cert_tokens & allowed_cert_tokens):
                violations.append(
                    ValidationViolation(
                        code="unverified_certification",
                        message=f"Unsupported certification claim '{iso_match.group()}'",
                        location=path,
                        severity="error" if strict else "warning",
                    )
                )

    matrix_coverage = len(matrix) / max(requirement_count, 1)
    if requirement_count > 0 and matrix_coverage < 0.85:
        violations.append(
            ValidationViolation(
                code="matrix_coverage_low",
                message=(
                    f"Matrix covers {matrix_coverage:.0%} of {requirement_count} "
                    "requirements (minimum 85%)"
                ),
                location="compliance_matrix",
                severity="error" if strict else "warning",
            )
        )

    error_count = sum(1 for v in violations if v.get("severity") == "error")
    warning_count = sum(1 for v in violations if v.get("severity") == "warning")
    blocking = [
        v
        for v in violations
        if v.get("code") in _BLOCKING_CODES and v.get("severity") == "error"
    ]

    return violations, {
        "passed": error_count == 0,
        "strict_mode": strict,
        "blocked": strict and bool(blocking),
        "error_count": error_count,
        "warning_count": warning_count,
        "echo_response_count": echo_count,
        "unjustified_compliant_count": unjustified_compliant,
        "matrix_row_count": len(matrix),
        "requirement_count": requirement_count,
        "matrix_coverage_ratio": round(matrix_coverage, 3),
        "violations": violations,
        "blocking_reason": blocking[0].get("message") if blocking else None,
    }


def compute_section_confidence(
    data: dict[str, Any],
    pipeline_ctx: dict[str, Any],
    validation_report: dict[str, Any] | None = None,
) -> dict[str, float]:
    pre_matrix = pipeline_ctx.get("pre_built_compliance_matrix") or []
    gap_count = len(pipeline_ctx.get("gaps") or [])

    validation_penalty = 1.0
    if validation_report:
        if validation_report.get("error_count", 0) > 0:
            validation_penalty = 0.5
        elif validation_report.get("warning_count", 0) > 0:
            validation_penalty = 0.75
    gap_penalty = max(0.4, 1.0 - gap_count * 0.05)

    def _rows_for(section_id: str) -> list[dict]:
        return [r for r in pre_matrix if r.get("proposal_section") == section_id]

    def _score(section_id: str, has_text: bool) -> float:
        rows = _rows_for(section_id)
        if not rows and not has_text:
            return 0.15
        row_scores = [float(r.get("confidence_score") or 0.2) for r in rows]
        eq = sum(row_scores) / len(row_scores) if row_scores else 0.2
        ec = min(1.0, len(rows) / max(len(pre_matrix), 1) * 3)
        raw = eq * ec * 1.0 * gap_penalty * validation_penalty
        return round(max(0.05, min(0.99, raw)), 3)

    return {
        "executive_summary": _score(
            "executive_summary",
            bool((data.get("executive_summary") or {}).get("text")),
        ),
        "staffing_approach": _score(
            "staffing_approach",
            bool((data.get("staffing_approach") or {}).get("text")),
        ),
        "compliance_matrix": _score("compliance_matrix", bool(pre_matrix)),
        "training_framework": _score(
            "training_framework",
            bool((data.get("training_framework") or {}).get("text")),
        ),
        "risk_management": _score("risk_management", bool(data.get("operational_risks"))),
    }
