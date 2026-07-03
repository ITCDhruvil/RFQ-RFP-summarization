"""Structured schemas for enterprise proposal generation pipeline."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, TypedDict


class RequirementCategory(StrEnum):
    TECHNICAL = "TECHNICAL"
    OPERATIONAL = "OPERATIONAL"
    STAFFING = "STAFFING"
    COMPLIANCE = "COMPLIANCE"
    COMMERCIAL = "COMMERCIAL"
    LEGAL = "LEGAL"
    SECURITY = "SECURITY"
    IMPLEMENTATION = "IMPLEMENTATION"
    REPORTING = "REPORTING"
    TRAINING = "TRAINING"
    TRANSITION = "TRANSITION"


class EvidenceSourceType(StrEnum):
    SOURCE_RFP = "SOURCE_RFP"
    SOURCE_VENDOR_PROFILE = "SOURCE_VENDOR_PROFILE"
    SOURCE_CASE_STUDY = "SOURCE_CASE_STUDY"
    SOURCE_CERTIFICATION = "SOURCE_CERTIFICATION"
    SOURCE_POLICY = "SOURCE_POLICY"
    SOURCE_KNOWLEDGE_BASE = "SOURCE_KNOWLEDGE_BASE"


class ComplianceStatus(StrEnum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    GAP = "gap"
    NA = "na"
    PLANNED = "planned"


class GapStatus(StrEnum):
    NONE = "none"
    VENDOR_TO_COMPLETE = "vendor_to_complete"
    RFP_ONLY = "rfp_only"


VENDOR_PLACEHOLDER = "[Vendor To Complete]"


class EvidenceRecord(TypedDict, total=False):
    evidence_id: str
    source_type: str
    source_ref: str
    excerpt: str
    field_path: str


class ClassifiedRequirement(TypedDict, total=False):
    requirement_id: str
    category: str
    requirement: str
    page: int
    section: str
    source_text: str
    extraction_type: str


class RequirementMatchPlan(TypedDict, total=False):
    requirement_id: str
    matched_evidence_ids: list[str]
    evidence_match_scores: dict[str, float]
    has_vendor_evidence: bool
    suggested_response_angle: str
    methodology_framework: list[str]
    gap_detected: bool
    gap_reason: str


class DetectedGap(TypedDict, total=False):
    field: str
    rfp_requirement: str
    reason: str
    action: str
    category: str


class SectionPlanItem(TypedDict, total=False):
    section_id: str
    title: str
    purpose: str
    required: bool
    evidence_required: bool
    min_confidence_target: float


class ValidationViolation(TypedDict, total=False):
    code: str
    message: str
    location: str
    severity: str


class PipelineContext(TypedDict, total=False):
    requirements: list[ClassifiedRequirement]
    evidence_index: list[EvidenceRecord]
    match_plans: list[RequirementMatchPlan]
    gaps: list[DetectedGap]
    section_plan: list[SectionPlanItem]
    evaluation_weights: dict
    pre_built_compliance_matrix: list[dict]
    traceability_matrix: list[dict]
    pipeline_version: str


# Keyword routing for deterministic requirement classification
_CATEGORY_KEYWORDS: dict[RequirementCategory, tuple[str, ...]] = {
    RequirementCategory.STAFFING: (
        "personnel",
        "headcount",
        "guards",
        "manpower",
        "staff",
        "workforce",
        "deployment",
        "fte",
        "shift",
    ),
    RequirementCategory.TRAINING: (
        "training",
        "induction",
        "certification program",
        "skill",
        "workshop",
    ),
    RequirementCategory.TRANSITION: (
        "mobilization",
        "transition",
        "go-live",
        "ramp-up",
        "onboarding",
    ),
    RequirementCategory.REPORTING: (
        "report",
        "dashboard",
        "kpi",
        "attendance",
        "incident log",
        "monthly",
    ),
    RequirementCategory.SECURITY: (
        "escort",
        "transport",
        "cctv",
        "access control",
        "patrol",
        "guarding",
        "surveillance",
    ),
    RequirementCategory.COMPLIANCE: (
        "compliance",
        "audit",
        "verify",
        "registration",
        "document",
        "certificate",
        "iso",
        "statutory",
    ),
    RequirementCategory.LEGAL: (
        "indemn",
        "liability",
        "contract",
        "terminate",
        "law",
        "legal",
        "hold harmless",
    ),
    RequirementCategory.COMMERCIAL: (
        "price",
        "cost",
        "payment",
        "invoice",
        "commercial",
        "pricing",
        "bid",
    ),
    RequirementCategory.IMPLEMENTATION: (
        "implement",
        "timeline",
        "milestone",
        "phase",
        "plan",
        "schedule",
    ),
    RequirementCategory.OPERATIONAL: (
        "sla",
        "24/7",
        "365",
        "operational",
        "service level",
        "response time",
        "escalation",
    ),
}


def classify_requirement_text(text: str, extraction_type: str = "") -> RequirementCategory:
    """Deterministic category assignment from requirement text."""
    lowered = text.lower()
    ext = extraction_type.lower()

    if ext in ("mandatory_documents", "eligibility_criteria"):
        return RequirementCategory.COMPLIANCE
    if ext == "payment_terms":
        return RequirementCategory.COMMERCIAL
    if ext == "penalties_and_risks":
        return RequirementCategory.LEGAL
    if ext == "submission_deadlines":
        return RequirementCategory.COMPLIANCE
    if ext == "evaluation_criteria":
        return RequirementCategory.TECHNICAL

    scores: dict[RequirementCategory, int] = {}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in lowered)
        if score:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)

    return RequirementCategory.TECHNICAL


def pipeline_context_to_json(ctx: PipelineContext) -> dict[str, Any]:
    return {
        "requirements": ctx.get("requirements") or [],
        "evidence_index": ctx.get("evidence_index") or [],
        "match_plans": ctx.get("match_plans") or [],
        "gaps": ctx.get("gaps") or [],
        "section_plan": ctx.get("section_plan") or [],
        "evaluation_weights": ctx.get("evaluation_weights") or {},
        "pre_built_compliance_matrix": ctx.get("pre_built_compliance_matrix") or [],
        "traceability_matrix": ctx.get("traceability_matrix") or [],
        "pipeline_version": ctx.get("pipeline_version") or "2.1.0",
    }


def pipeline_context_to_llm_json(
    ctx: PipelineContext,
    *,
    include_compliance_matrix: bool = True,
) -> dict[str, Any]:
    """Smaller payload for the synthesis LLM — omits traceability (stored server-side)."""
    payload = pipeline_context_to_json(ctx)
    payload.pop("traceability_matrix", None)
    if not include_compliance_matrix:
        payload.pop("pre_built_compliance_matrix", None)
    return payload


def build_briefing_context_for_proposal(summary_json: dict[str, Any]) -> dict[str, Any]:
    """Trim briefing to evaluation-relevant fields (avoids duplicating full extractions)."""
    if not isinstance(summary_json, dict):
        return {}
    signals = summary_json.get("procurement_critical_signals") or []
    if isinstance(signals, list) and len(signals) > 8:
        signals = signals[:8]
    checklist = summary_json.get("submission_checklist") or []
    if isinstance(checklist, list) and len(checklist) > 10:
        checklist = checklist[:10]
    return {
        "executive_summary": summary_json.get("executive_summary"),
        "evaluation_overview": summary_json.get("evaluation_overview"),
        "procurement_critical_signals": signals,
        "key_requirements": (summary_json.get("key_requirements") or [])[:12],
        "submission_checklist": checklist,
    }
