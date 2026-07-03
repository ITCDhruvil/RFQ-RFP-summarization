"""Match classified requirements to vendor evidence."""

from __future__ import annotations

from apps.intelligence.services.proposal_methodology_templates import (
    get_methodology_framework,
)
from apps.intelligence.services.proposal_schemas import (
    ClassifiedRequirement,
    EvidenceRecord,
    RequirementCategory,
    RequirementMatchPlan,
)
from apps.intelligence.services.proposal_vendor_evidence import tokenize

_CATEGORY_EVIDENCE_BOOST: dict[str, tuple[str, ...]] = {
    RequirementCategory.STAFFING.value: (
        "capabilities",
        "additional_notes",
        "reference_projects",
    ),
    RequirementCategory.SECURITY.value: ("capabilities", "reference_projects"),
    RequirementCategory.TRAINING.value: ("capabilities", "certifications"),
    RequirementCategory.COMPLIANCE.value: ("certifications", "capabilities"),
    RequirementCategory.TRANSITION.value: (
        "reference_projects",
        "additional_notes",
        "capabilities",
    ),
    RequirementCategory.IMPLEMENTATION.value: ("reference_projects", "capabilities"),
}


def _score_match(req_tokens: set[str], evidence: EvidenceRecord) -> float:
    ev_tokens = tokenize(evidence.get("excerpt") or "")
    if not req_tokens or not ev_tokens:
        return 0.0
    overlap = len(req_tokens & ev_tokens)
    if overlap == 0:
        return 0.0
    return overlap / max(len(req_tokens), 1)


def build_match_plans(
    requirements: list[ClassifiedRequirement],
    evidence_index: list[EvidenceRecord],
) -> list[RequirementMatchPlan]:
    plans: list[RequirementMatchPlan] = []

    for req in requirements:
        req_text = req.get("requirement") or ""
        req_tokens = tokenize(req_text)
        category = req.get("category") or RequirementCategory.TECHNICAL.value
        boost_paths = _CATEGORY_EVIDENCE_BOOST.get(category, ("capabilities",))

        scored: list[tuple[float, str]] = []
        for ev in evidence_index:
            score = _score_match(req_tokens, ev)
            field_path = ev.get("field_path") or ""
            if any(bp in field_path for bp in boost_paths):
                score *= 1.3
            if score > 0.05:
                scored.append((score, ev["evidence_id"]))

        scored.sort(key=lambda x: -x[0])
        matched_ids = [eid for _, eid in scored[:3]]
        score_map = {eid: round(score, 4) for score, eid in scored[:3]}
        has_evidence = bool(matched_ids)
        framework = get_methodology_framework(category)

        angle = _response_angle(category, has_evidence)
        gap = not has_evidence and category in (
            RequirementCategory.COMPLIANCE.value,
            RequirementCategory.STAFFING.value,
        )

        plans.append(
            RequirementMatchPlan(
                requirement_id=req.get("requirement_id") or "",
                matched_evidence_ids=matched_ids,
                evidence_match_scores=score_map,
                has_vendor_evidence=has_evidence,
                suggested_response_angle=angle,
                methodology_framework=list(framework.keys()),
                gap_detected=gap,
                gap_reason=(
                    "No vendor evidence matched this requirement" if gap else ""
                ),
            )
        )

    return plans


def _response_angle(category: str, has_evidence: bool) -> str:
    angles = {
        RequirementCategory.STAFFING.value: (
            "Describe staffing model, shift structure, backup pools, and mobilization "
            "approach — cite workforce evidence if available"
        ),
        RequirementCategory.SECURITY.value: (
            "Explain operational controls, supervision, protocols, and escalation — "
            "not merely that security will be provided"
        ),
        RequirementCategory.TRAINING.value: (
            "Outline training curriculum, frequency, trainers, and competency verification"
        ),
        RequirementCategory.TRANSITION.value: (
            "Detail mobilization phases, governance, and readiness criteria"
        ),
        RequirementCategory.REPORTING.value: (
            "Specify reports, KPIs, frequency, and accountability owners"
        ),
        RequirementCategory.OPERATIONAL.value: (
            "Explain HOW 24/7 or SLA coverage is maintained — shifts, backups, monitoring"
        ),
        RequirementCategory.COMPLIANCE.value: (
            "Reference specific certifications/documents from vendor evidence or mark gap"
        ),
        RequirementCategory.IMPLEMENTATION.value: (
            "Provide phased plan with milestones, dependencies, and deliverables"
        ),
    }
    base = angles.get(
        category,
        "Explain methodology and approach — do NOT restate the requirement verbatim",
    )
    if not has_evidence:
        return f"{base}. Use [Vendor To Complete] for unverified claims."
    return base
