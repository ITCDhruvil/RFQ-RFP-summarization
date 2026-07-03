"""Plan commercial proposal sections."""

from __future__ import annotations

from typing import Any


COMMERCIAL_SECTIONS = [
    {"key": "cover_letter", "title": "Commercial Cover Letter", "order": 1},
    {"key": "executive_summary", "title": "Commercial Executive Summary", "order": 2},
    {"key": "pricing_summary", "title": "Pricing Summary", "order": 3, "deterministic": True},
    {"key": "resource_pricing_table", "title": "Resource Pricing Table", "order": 4, "deterministic": True},
    {"key": "cost_breakdown", "title": "Cost Breakdown", "order": 5, "deterministic": True},
    {"key": "assumptions", "title": "Commercial Assumptions", "order": 6, "deterministic": True},
    {"key": "exclusions", "title": "Commercial Exclusions", "order": 7, "deterministic": True},
    {"key": "taxes_and_duties", "title": "Taxes & Duties", "order": 8},
    {"key": "payment_terms", "title": "Payment Terms", "order": 9},
    {"key": "price_validity", "title": "Price Validity", "order": 10},
    {"key": "commercial_terms", "title": "Commercial Terms & Conditions", "order": 11},
    {"key": "sign_off", "title": "Sign-Off", "order": 12},
]


def plan_commercial_sections(
    requirements: dict[str, Any],
    pricing_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    sections = [dict(s) for s in COMMERCIAL_SECTIONS]
    if requirements.get("taxes_mentioned"):
        for s in sections:
            if s["key"] == "taxes_and_duties":
                s["emphasis"] = "high"
    if pricing_summary.get("total_with_tax"):
        for s in sections:
            if s["key"] == "pricing_summary":
                s["emphasis"] = "high"
    return sections
