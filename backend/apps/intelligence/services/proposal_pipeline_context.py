"""Assemble pre-generation pipeline context (v2.1)."""

from __future__ import annotations

from apps.intelligence.models import ExtractedInsight
from apps.intelligence.services.proposal_capability_matcher import build_match_plans
from apps.intelligence.services.proposal_compliance_matrix_builder import (
    build_deterministic_compliance_matrix,
)
from apps.intelligence.services.proposal_evaluation_weights import (
    parse_evaluation_weights,
    section_emphasis_score,
)
from apps.intelligence.services.proposal_gap_detector import detect_gaps
from apps.intelligence.services.proposal_requirement_registry import (
    build_requirement_registry,
)
from apps.intelligence.services.proposal_schemas import (
    PipelineContext,
    pipeline_context_to_json,
)
from apps.intelligence.services.proposal_section_planner import build_section_plan
from apps.intelligence.services.proposal_traceability import build_traceability_matrix
from apps.intelligence.services.proposal_vendor_evidence import build_vendor_evidence_index


def build_pipeline_context(
    insights: list[ExtractedInsight],
    profile: dict,
) -> PipelineContext:
    requirements = build_requirement_registry(insights)
    evidence_index = build_vendor_evidence_index(profile)
    match_plans = build_match_plans(requirements, evidence_index)
    gaps = detect_gaps(requirements, evidence_index, insights, profile)

    eval_data = parse_evaluation_weights(insights)
    eval_weights = eval_data.get("weights") or {}

    section_plan = build_section_plan(requirements, gaps)
    for section in section_plan:
        sid = section.get("section_id") or ""
        emphasis = section_emphasis_score(sid, eval_weights)
        section["emphasis_weight"] = round(emphasis, 3)
        section["priority"] = (
            "high" if emphasis >= 0.25 else "medium" if emphasis >= 0.15 else "low"
        )

    pre_built_matrix = build_deterministic_compliance_matrix(
        requirements, match_plans, evidence_index
    )
    traceability = build_traceability_matrix(pre_built_matrix)

    return PipelineContext(
        requirements=requirements,
        evidence_index=evidence_index,
        match_plans=match_plans,
        gaps=gaps,
        section_plan=section_plan,
        evaluation_weights=eval_data,
        pre_built_compliance_matrix=pre_built_matrix,
        traceability_matrix=traceability,
        pipeline_version="2.1.0",
    )


def pipeline_context_json(insights: list[ExtractedInsight], profile: dict) -> dict:
    return pipeline_context_to_json(build_pipeline_context(insights, profile))
