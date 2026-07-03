"""Deterministic compliance matrix builder."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from apps.intelligence.services.proposal_methodology_templates import (
    assemble_methodology_response,
    get_methodology_framework,
)
from apps.intelligence.services.proposal_schemas import (
    ClassifiedRequirement,
    ComplianceStatus,
    GapStatus,
    RequirementCategory,
    RequirementMatchPlan,
    VENDOR_PLACEHOLDER,
)
from apps.intelligence.services.proposal_vendor_evidence import evidence_by_id

_CATEGORY_SECTION_MAP: dict[str, str] = {
    RequirementCategory.STAFFING.value: "staffing_approach",
    RequirementCategory.SECURITY.value: "service_delivery_model",
    RequirementCategory.OPERATIONAL.value: "sla_and_operations",
    RequirementCategory.TRAINING.value: "training_framework",
    RequirementCategory.TRANSITION.value: "transition_plan",
    RequirementCategory.REPORTING.value: "reporting_and_kpis",
    RequirementCategory.COMPLIANCE.value: "compliance_matrix",
    RequirementCategory.IMPLEMENTATION.value: "transition_plan",
    RequirementCategory.TECHNICAL.value: "technical_approach",
    RequirementCategory.COMMERCIAL.value: "commercial_note",
    RequirementCategory.LEGAL.value: "assumptions_exclusions",
}


def _evidence_objects(
    plan: RequirementMatchPlan,
    evidence_index: list,
) -> list[dict[str, Any]]:
    by_id = evidence_by_id(evidence_index)
    out: list[dict[str, Any]] = []
    for eid in plan.get("matched_evidence_ids") or []:
        ev = by_id.get(eid)
        if not ev:
            continue
        out.append(
            {
                "evidence_id": ev.get("evidence_id"),
                "source_type": ev.get("source_type"),
                "source_ref": ev.get("source_ref"),
                "excerpt": ev.get("excerpt"),
            }
        )
    return out


def _match_scores(plan: RequirementMatchPlan) -> list[float]:
    score_map = plan.get("evidence_match_scores") or {}
    return list(score_map.values())


def _calculate_compliance(
    plan: RequirementMatchPlan,
    evidence_objs: list[dict[str, Any]],
    match_scores: list[float],
) -> tuple[str, str]:
    if not evidence_objs:
        if plan.get("gap_detected"):
            return ComplianceStatus.GAP.value, GapStatus.VENDOR_TO_COMPLETE.value
        return ComplianceStatus.PLANNED.value, GapStatus.VENDOR_TO_COMPLETE.value

    avg = sum(match_scores) / len(match_scores) if match_scores else 0.0
    if avg >= 0.25:
        return ComplianceStatus.COMPLIANT.value, GapStatus.NONE.value
    if avg >= 0.12:
        return ComplianceStatus.PARTIAL.value, GapStatus.NONE.value
    return ComplianceStatus.PARTIAL.value, GapStatus.VENDOR_TO_COMPLETE.value


def _row_confidence(
    match_scores: list[float],
    evidence_objs: list[dict[str, Any]],
    compliance_status: str,
    gap_status: str,
) -> float:
    if not evidence_objs:
        evidence_quality = 0.0
        evidence_coverage = 0.0
    else:
        evidence_quality = (
            min(1.0, sum(match_scores) / len(match_scores) * 2.5) if match_scores else 0.2
        )
        evidence_coverage = min(1.0, len(evidence_objs) / 2.0)

    evidence_recency = 1.0
    gap_penalty = 0.4 if gap_status != GapStatus.NONE.value else 1.0
    compliance_penalty = {
        ComplianceStatus.COMPLIANT.value: 1.0,
        ComplianceStatus.PARTIAL.value: 0.75,
        ComplianceStatus.PLANNED.value: 0.5,
        ComplianceStatus.GAP.value: 0.35,
        ComplianceStatus.NA.value: 0.9,
    }.get(compliance_status, 0.5)

    score = (
        evidence_quality * evidence_coverage * evidence_recency * gap_penalty * compliance_penalty
    )
    return round(max(0.05, min(0.99, score)), 3)


def build_deterministic_compliance_matrix(
    requirements: list[ClassifiedRequirement],
    match_plans: list[RequirementMatchPlan],
    evidence_index: list,
) -> list[dict[str, Any]]:
    plan_by_id = {p.get("requirement_id"): p for p in match_plans}
    rows: list[dict[str, Any]] = []

    for req in requirements:
        req_id = req.get("requirement_id") or ""
        plan = plan_by_id.get(req_id) or RequirementMatchPlan()
        category = req.get("category") or RequirementCategory.TECHNICAL.value

        evidence_objs = _evidence_objects(plan, evidence_index)
        excerpts = [e.get("excerpt", "") for e in evidence_objs if e.get("excerpt")]
        match_scores = _match_scores(plan)

        compliance_status, gap_status = _calculate_compliance(
            plan, evidence_objs, match_scores
        )
        vendor_response, methodology = assemble_methodology_response(
            category, excerpts, requirement_text=req.get("requirement") or ""
        )

        if compliance_status == ComplianceStatus.GAP.value:
            if VENDOR_PLACEHOLDER not in vendor_response:
                vendor_response = f"{vendor_response} {VENDOR_PLACEHOLDER}"

        rows.append(
            {
                "requirement_ref": req_id,
                "category": category,
                "requirement_text": req.get("requirement") or "",
                "vendor_response": vendor_response,
                "methodology": methodology,
                "methodology_framework": list(get_methodology_framework(category).keys()),
                "evidence": evidence_objs,
                "compliance_status": compliance_status,
                "gap_status": gap_status,
                "confidence_score": _row_confidence(
                    match_scores, evidence_objs, compliance_status, gap_status
                ),
                "proposal_section": _CATEGORY_SECTION_MAP.get(
                    category, "technical_approach"
                ),
                "sources": [
                    {
                        "page": req.get("page"),
                        "section": req.get("section") or "",
                        "source_text": req.get("source_text") or "",
                    }
                ]
                if req.get("source_text")
                else [],
                "_deterministic": True,
            }
        )

    return rows


def merge_llm_matrix_responses(
    deterministic_rows: list[dict[str, Any]],
    llm_rows: list[dict[str, Any]],
    *,
    echo_threshold: float = 0.72,
) -> list[dict[str, Any]]:
    llm_by_ref = {
        str(r.get("requirement_ref")): r
        for r in llm_rows
        if isinstance(r, dict) and r.get("requirement_ref")
    }
    merged: list[dict[str, Any]] = []

    for pre in deterministic_rows:
        ref = str(pre.get("requirement_ref"))
        llm = llm_by_ref.get(ref, {})
        row = dict(pre)
        llm_response = str(llm.get("vendor_response") or "").strip()
        if llm_response:
            req_text = str(pre.get("requirement_text") or "")
            sim = SequenceMatcher(None, req_text.lower(), llm_response.lower()).ratio()
            if sim < echo_threshold and (VENDOR_PLACEHOLDER in llm_response or sim < 0.55):
                row["vendor_response"] = llm_response
                if llm.get("methodology"):
                    row["methodology"] = llm["methodology"]
        merged.append(row)

    return merged
