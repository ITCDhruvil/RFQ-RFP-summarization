"""Assemble commercial proposal pipeline context."""

from __future__ import annotations

from typing import Any

from apps.intelligence.models import ExtractedInsight
from apps.intelligence.services.commercial_assumptions import generate_commercial_assumptions
from apps.intelligence.services.commercial_exclusions import generate_commercial_exclusions
from apps.intelligence.services.commercial_gap_detector import detect_commercial_gaps
from apps.intelligence.services.commercial_pricing_engine import (
    build_resource_lines,
    calculate_pricing,
)
from apps.intelligence.services.commercial_requirement_registry import (
    build_commercial_requirement_registry,
)
from apps.intelligence.services.commercial_schemas import (
    COMMERCIAL_PIPELINE_VERSION,
    DEFAULT_WORKBENCH,
    normalize_commercial_vendor_profile,
)
from apps.intelligence.services.commercial_section_planner import plan_commercial_sections
from apps.intelligence.services.commercial_validator import validate_commercial_workbench


def _lines_are_populated(lines: list) -> bool:
    for row in lines:
        if not isinstance(row, dict):
            continue
        if int(row.get("quantity") or 0) > 0:
            return True
    return False


def _to_editable_lines(lines: list) -> list[dict]:
    editable: list[dict] = []
    for row in lines:
        if not isinstance(row, dict):
            continue
        editable.append(
            {
                "role_key": row.get("role_key"),
                "role_label": row.get("role_label"),
                "line_type": row.get("line_type") or "personnel",
                "billing_basis": row.get("billing_basis") or "monthly",
                "quantity": row.get("quantity"),
                "unit_cost_monthly": row.get("unit_cost_monthly"),
                "margin_percent": row.get("margin_percent"),
                "gst_percent": row.get("gst_percent"),
            }
        )
    return editable


def build_commercial_workbench(
    insights: list[ExtractedInsight],
    vendor_profile: dict[str, Any],
    existing_workbench: dict[str, Any] | None = None,
) -> dict[str, Any]:
    profile = normalize_commercial_vendor_profile(vendor_profile)
    workbench = dict(DEFAULT_WORKBENCH)
    if existing_workbench:
        workbench.update(existing_workbench)

    requirements = build_commercial_requirement_registry(insights)
    workbench["requirements"] = requirements

    answers = workbench.get("questionnaire_answers") or {}
    gap_report = detect_commercial_gaps(requirements, profile, answers)
    workbench["gap_report"] = gap_report

    if not workbench.get("terms"):
        workbench["terms"] = {}
    workbench["terms"].setdefault(
        "currency", requirements.get("currency") or profile.get("currency")
    )
    workbench["terms"].setdefault("payment_terms_days", profile.get("payment_terms_days"))
    workbench["terms"].setdefault("price_validity_days", profile.get("price_validity_days"))

    stored = workbench.get("pricing", {}).get("resource_lines") or []
    built = build_resource_lines(requirements, profile, answers)
    if _lines_are_populated(stored):
        lines = _to_editable_lines(stored)
    else:
        lines = built or _to_editable_lines(stored)
    pricing = calculate_pricing(lines)
    workbench["pricing"] = pricing

    if not workbench.get("assumptions"):
        workbench["assumptions"] = generate_commercial_assumptions(
            requirements, profile, answers
        )
    if not workbench.get("exclusions"):
        workbench["exclusions"] = generate_commercial_exclusions(
            requirements, profile, answers
        )

    workbench["section_plan"] = plan_commercial_sections(
        requirements, pricing.get("summary") or {}
    )
    workbench["validation_report"] = validate_commercial_workbench(
        workbench, profile, strict=False
    )
    workbench["pipeline_version"] = COMMERCIAL_PIPELINE_VERSION
    return workbench


def refresh_pricing_in_workbench(workbench: dict[str, Any]) -> dict[str, Any]:
    lines = workbench.get("pricing", {}).get("resource_lines") or []
    if lines and isinstance(lines[0], dict) and "monthly_cost" in lines[0]:
        editable = []
        for row in lines:
            editable.append(
                {
                    "role_key": row.get("role_key"),
                    "role_label": row.get("role_label"),
                    "quantity": row.get("quantity"),
                    "unit_cost_monthly": row.get("unit_cost_monthly"),
                    "margin_percent": row.get("margin_percent"),
                    "gst_percent": row.get("gst_percent"),
                }
            )
        lines = editable
    workbench["pricing"] = calculate_pricing(lines)
    return workbench
