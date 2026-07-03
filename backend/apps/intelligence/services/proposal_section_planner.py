"""Dynamic proposal section planner based on RFP content."""

from __future__ import annotations

from collections import Counter

from apps.intelligence.services.proposal_schemas import (
    ClassifiedRequirement,
    DetectedGap,
    SectionPlanItem,
)

_BASE_SECTIONS: list[SectionPlanItem] = [
    {
        "section_id": "cover_letter",
        "title": "Cover Letter",
        "purpose": "Formal submission letter referencing RFP and bidder",
        "required": True,
        "evidence_required": False,
        "min_confidence_target": 0.7,
    },
    {
        "section_id": "executive_summary",
        "title": "Executive Summary",
        "purpose": "Bidder value proposition — NOT an RFP recap",
        "required": True,
        "evidence_required": True,
        "min_confidence_target": 0.85,
    },
    {
        "section_id": "company_overview",
        "title": "Company Overview",
        "purpose": "Vendor credentials from profile evidence only",
        "required": True,
        "evidence_required": True,
        "min_confidence_target": 0.8,
    },
    {
        "section_id": "understanding_of_requirements",
        "title": "Understanding of Requirements",
        "purpose": "Demonstrate comprehension of client needs and scope",
        "required": True,
        "evidence_required": False,
        "min_confidence_target": 0.75,
    },
    {
        "section_id": "why_choose_us",
        "title": "Why Choose Us",
        "purpose": "Evidence-backed differentiators from vendor profile only",
        "required": True,
        "evidence_required": True,
        "min_confidence_target": 0.7,
    },
]

_CATEGORY_SECTIONS: dict[str, SectionPlanItem] = {
    "STAFFING": {
        "section_id": "staffing_approach",
        "title": "Staffing Approach",
        "purpose": "Workforce model, shift structure, backup pools, mobilization",
        "required": False,
        "evidence_required": True,
        "min_confidence_target": 0.75,
    },
    "SECURITY": {
        "section_id": "service_delivery_model",
        "title": "Service Delivery Model",
        "purpose": "Operational methodology for security service delivery",
        "required": False,
        "evidence_required": True,
        "min_confidence_target": 0.8,
    },
    "TRAINING": {
        "section_id": "training_framework",
        "title": "Training Framework",
        "purpose": "Training curriculum, frequency, competency verification",
        "required": False,
        "evidence_required": True,
        "min_confidence_target": 0.65,
    },
    "TRANSITION": {
        "section_id": "transition_plan",
        "title": "Transition Plan",
        "purpose": "Mobilization phases, governance, readiness criteria",
        "required": False,
        "evidence_required": True,
        "min_confidence_target": 0.7,
    },
    "REPORTING": {
        "section_id": "reporting_and_kpis",
        "title": "Reporting & KPIs",
        "purpose": "Reports, dashboards, accountability",
        "required": False,
        "evidence_required": False,
        "min_confidence_target": 0.6,
    },
    "OPERATIONAL": {
        "section_id": "sla_and_operations",
        "title": "SLA & Operations",
        "purpose": "How continuous coverage and SLAs are maintained",
        "required": False,
        "evidence_required": True,
        "min_confidence_target": 0.7,
    },
}


def build_section_plan(
    requirements: list[ClassifiedRequirement],
    gaps: list[DetectedGap],
) -> list[SectionPlanItem]:
    plan: list[SectionPlanItem] = list(_BASE_SECTIONS)
    seen_ids = {s["section_id"] for s in plan}

    counts = Counter(r.get("category") or "TECHNICAL" for r in requirements)
    for category, _count in counts.most_common():
        section = _CATEGORY_SECTIONS.get(category)
        if section and section["section_id"] not in seen_ids:
            plan.append({**section, "required": _count >= 2})
            seen_ids.add(section["section_id"])

    for extra in (
        {
            "section_id": "compliance_matrix",
            "title": "Compliance Matrix",
            "purpose": "Requirement-by-requirement response with evidence",
            "required": True,
            "evidence_required": True,
            "min_confidence_target": 0.9,
        },
        {
            "section_id": "risk_management",
            "title": "Risk Management",
            "purpose": "Operational risks with likelihood, impact, mitigation, owner",
            "required": True,
            "evidence_required": False,
            "min_confidence_target": 0.7,
        },
        {
            "section_id": "assumptions_exclusions",
            "title": "Assumptions & Exclusions",
            "purpose": "Explicit assumptions and exclusions",
            "required": True,
            "evidence_required": False,
            "min_confidence_target": 0.5,
        },
    ):
        if extra["section_id"] not in seen_ids:
            plan.append(extra)  # type: ignore[arg-type]
            seen_ids.add(extra["section_id"])

    if any(g.get("reason") == "pricing_required" for g in gaps):
        plan.append(
            {
                "section_id": "commercial_note",
                "title": "Commercial Volume Reference",
                "purpose": "Note that pricing is in separate commercial proposal",
                "required": True,
                "evidence_required": False,
                "min_confidence_target": 1.0,
            }
        )

    return plan
