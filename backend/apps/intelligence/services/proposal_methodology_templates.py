"""Deterministic methodology frameworks per requirement category."""

from __future__ import annotations

from typing import Any

from apps.intelligence.services.proposal_schemas import RequirementCategory, VENDOR_PLACEHOLDER

# Each slot maps to a narrative component the vendor must address.
METHODOLOGY_FRAMEWORKS: dict[str, dict[str, str]] = {
    RequirementCategory.STAFFING.value: {
        "deployment_model": "Shift/deployment model (e.g. three-shift rotation, site supervisors per zone)",
        "backup_pool_strategy": "Backup/float pool % and activation trigger for absences",
        "escalation_strategy": "Escalation path for unfilled shifts within SLA window",
        "recruitment_capacity": "Recruitment pipeline capacity and time-to-fill for surge demand",
        "onboarding_process": "Pre-deployment vetting, induction, and site readiness checklist",
    },
    RequirementCategory.SECURITY.value: {
        "operational_controls": "Patrol routes, access control points, incident logging",
        "supervision_model": "Site supervisor ratios and command/control touchpoints",
        "incident_response": "Detection → escalation → resolution workflow and timelines",
        "transport_protocols": "Escort procedures, roll-call, cab inspection checklist",
        "quality_assurance": "Audit frequency, non-conformance corrective actions",
    },
    RequirementCategory.OPERATIONAL.value: {
        "coverage_model": "How 24/7/365 continuity is maintained across shifts",
        "monitoring": "Attendance, GPS/check-call, or control-room monitoring",
        "sla_management": "SLA measurement, reporting, and breach remediation",
        "backup_activation": "Procedure when primary resource unavailable",
    },
    RequirementCategory.TRAINING.value: {
        "curriculum": "Initial and refresher training modules aligned to client SOPs",
        "delivery_model": "Classroom, on-site, e-learning mix and frequency",
        "competency_verification": "Assessment, certification, and re-training triggers",
        "trainer_qualifications": "Trainer credentials — profile evidence only",
    },
    RequirementCategory.TRANSITION.value: {
        "mobilization_phases": "Phased go-live with readiness gates",
        "governance": "Steering committee, weekly war-room, issue log",
        "knowledge_transfer": "Handover from incumbent or greenfield setup steps",
        "readiness_criteria": "Objective criteria before declaring operational",
    },
    RequirementCategory.REPORTING.value: {
        "report_types": "Attendance, incident, SLA, monthly governance reports",
        "frequency": "Daily/weekly/monthly cadence per report type",
        "accountability": "Named role responsible for each report",
        "escalation_on_breach": "What happens when KPI thresholds missed",
    },
    RequirementCategory.COMPLIANCE.value: {
        "regulatory_alignment": "Applicable licenses/registrations held",
        "document_submission": "Which compliance documents will be attached",
        "audit_readiness": "Internal audit cycle and evidence retention",
        "gap_remediation": "Plan if certification pending",
    },
    RequirementCategory.IMPLEMENTATION.value: {
        "phases": "Named phases with duration and entry/exit criteria",
        "dependencies": "Client inputs, site access, approvals required",
        "deliverables": "Tangible outputs per phase",
        "risk_mitigation": "Top implementation risks and mitigations",
    },
    RequirementCategory.TECHNICAL.value: {
        "approach": "Technical/service approach tailored to requirement",
        "tools_systems": "Systems, equipment, or platforms used — evidence only",
        "integration": "Integration with client processes or third parties",
        "quality_controls": "QA checkpoints and acceptance criteria",
    },
    RequirementCategory.COMMERCIAL.value: {
        "pricing_approach": "Reference commercial volume — no figures in technical draft",
        "assumptions": "Commercial assumptions requiring client confirmation",
    },
    RequirementCategory.LEGAL.value: {
        "contractual_alignment": "Acknowledgement of terms — legal review required",
        "indemnity_approach": "Risk transfer approach — legal review required",
    },
}


def get_methodology_framework(category: str) -> dict[str, str]:
    return METHODOLOGY_FRAMEWORKS.get(
        category, METHODOLOGY_FRAMEWORKS[RequirementCategory.TECHNICAL.value]
    )


def _slot_value_from_evidence(
    slot: str,
    evidence_excerpts: list[str],
    category: str,
) -> str:
    """Fill a methodology slot from evidence text when keywords align."""
    slot_keywords: dict[str, tuple[str, ...]] = {
        "deployment_model": ("shift", "deploy", "rotation", "24/7", "site"),
        "backup_pool_strategy": ("bench", "backup", "float", "pool", "surge"),
        "recruitment_capacity": ("recruit", "pipeline", "workforce", "personnel", "headcount"),
        "onboarding_process": ("train", "induction", "onboard", "vetting"),
        "operational_controls": ("patrol", "access", "cctv", "control"),
        "coverage_model": ("24/7", "365", "continuous", "coverage"),
        "curriculum": ("training", "curriculum", "module"),
        "regulatory_alignment": ("iso", "certif", "licens", "psara", "registered"),
    }
    keywords = slot_keywords.get(slot, ())
    for excerpt in evidence_excerpts:
        lower = excerpt.lower()
        if any(kw in lower for kw in keywords):
            return excerpt[:280]
    return VENDOR_PLACEHOLDER


def assemble_methodology_response(
    category: str,
    evidence_excerpts: list[str],
    *,
    requirement_text: str = "",
) -> tuple[str, str]:
    """
    Build deterministic vendor_response skeleton and methodology summary.
    Returns (vendor_response, methodology_summary).
    """
    framework = get_methodology_framework(category)
    paragraphs: list[str] = []
    filled_slots: list[str] = []

    for slot, hint in framework.items():
        value = _slot_value_from_evidence(slot, evidence_excerpts, category)
        label = hint.split("(")[0].strip()
        paragraphs.append(f"{label}: {value}")
        if VENDOR_PLACEHOLDER not in value:
            filled_slots.append(label)

    vendor_response = " ".join(paragraphs)
    if filled_slots:
        methodology = f"Approach covers: {', '.join(filled_slots[:4])}."
    else:
        methodology = (
            f"Methodology framework defined for {category}; "
            f"vendor evidence required to complete."
        )

    return vendor_response, methodology
