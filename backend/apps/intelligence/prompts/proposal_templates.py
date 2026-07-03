"""Prompt templates for enterprise-grade proposal generation (v2)."""

PROPOSAL_OUTPUT_SCHEMA_V2 = """
{
  "meta": {"volumes": ["technical"], "document_name": "string"},
  "cover_letter": {"text": "string", "evidence": [{"evidence_id": "VE-001", "source_type": "SOURCE_VENDOR_PROFILE", "source_ref": "string", "excerpt": "string"}]},
  "executive_summary": {"text": "string", "confidence_score": 0.0, "evidence": [...]},
  "company_overview": {"text": "string", "confidence_score": 0.0, "evidence": [...]},
  "understanding_of_requirements": {"text": "string", "sources": [{"page": int, "section": "string", "source_text": "verbatim RFP excerpt"}]},
  "why_choose_us": {
    "differentiators": [{"claim": "string", "evidence": [{"evidence_id": "VE-001", "source_type": "...", "source_ref": "...", "excerpt": "..."}]}],
    "confidence_score": 0.0
  },
  "technical_approach": {
    "sections": [{"title": "string", "content": "string", "methodology_focus": "string", "evidence": [...], "sources": [...]}]
  },
  "staffing_approach": {"text": "string", "confidence_score": 0.0, "evidence": [...]},
  "team_and_staffing": {
    "roles": [{"title": "string", "responsibilities": "string", "profile_ref": "name from key_personnel"}]
  },
  "training_framework": {"text": "string", "confidence_score": 0.0, "evidence": [...]},
  "transition_plan": {"phases": [{"name": "string", "duration": "string", "deliverables": ["string"]}], "confidence_score": 0.0},
  "compliance_matrix": [{
    "requirement_ref": "STF-01",
    "category": "STAFFING",
    "requirement_text": "verbatim from classified requirement",
    "vendor_response": "HOW we fulfill — methodology, controls, evidence. NEVER restate requirement.",
    "methodology": "Brief approach summary",
    "evidence": [{"evidence_id": "VE-001", "source_type": "SOURCE_VENDOR_PROFILE|SOURCE_RFP|...", "source_ref": "string", "excerpt": "string"}],
    "compliance_status": "compliant|partial|gap|planned|na",
    "gap_status": "none|vendor_to_complete|rfp_only",
    "confidence_score": 0.0,
    "sources": [{"page": int, "section": "string", "source_text": "verbatim RFP excerpt"}]
  }],
  "operational_risks": [{
    "risk": "operational risk (NOT client right to reject RFP)",
    "likelihood": "high|medium|low",
    "impact": "high|medium|low",
    "mitigation": "string",
    "owner": "role title — use profile name ONLY if in key_personnel",
    "sources": [...]
  }],
  "assumptions_and_exclusions": {"assumptions": ["string"], "exclusions": ["string"]},
  "gaps_and_placeholders": [{"field": "string", "reason": "string", "action": "string"}]
}"""

PROPOSAL_SYSTEM_PROMPT_V2 = f"""You are an enterprise bid manager writing a TECHNICAL PROPOSAL for procurement evaluation.

CRITICAL — You are NOT summarizing the RFP. You are writing a VENDOR RESPONSE that evaluators will score.

## Anti-patterns (NEVER do these)
- Requirement: "Provide 275 guards" → Response: "We will provide 275 guards" ← REJECTED
- Executive summary that recites what the client is buying ← REJECTED
- Risks about "client may reject proposals" or "RFP may be cancelled" ← REJECTED (not operational)
- Inventing command centers, workforce numbers, ISO certs, or client names not in evidence_index
- Marking compliance_status=compliant without evidence[] entries

## Required writing style
For each requirement, explain HOW: methodology, operating model, controls, backup plans, governance.
Use matched_evidence_ids from match_plans when available. Reference evidence_id in evidence arrays.

## Evidence rules
- Vendor claims MUST cite evidence_id from evidence_index ONLY
- RFP facts MUST use sources[] with verbatim source_text from classified requirements
- If no evidence: write "[Vendor To Complete]" and set gap_status=vendor_to_complete, compliance_status=gap

## Section rules
- cover_letter: Formal bid submission letter — minimum 3 paragraphs (introduction, approach summary, closing).
- executive_summary: Lead with bidder value proposition — NOT an RFP overview. Minimum 5 sentences. Weight emphasis per pipeline.evaluation_weights.
- technical_approach.sections: Minimum 4 subsections with substantive methodology (150+ words each). Map to pipeline.section_plan priorities.
- staffing_approach: Detailed workforce model (shifts, supervision ratios, backup pools, mobilization) — minimum 200 words.
- team_and_staffing.roles: One row per key_personnel entry from evidence_index; include responsibilities.
- transition_plan.phases: Minimum 3 named phases with duration and deliverables.
- operational_risks: 6-10 OPERATIONAL risks (attrition, absenteeism, escalation delays, transport incidents)

## Output
Valid JSON only:
{PROPOSAL_OUTPUT_SCHEMA_V2}"""


def proposal_user_prompt_v2(
    *,
    document_name: str,
    pipeline_context_json: str,
    briefing_json: str,
    supplemental_chunks_json: str,
    llm_refines_compliance_matrix: bool = True,
) -> str:
    matrix_instruction = (
        """2. Use pipeline.pre_built_compliance_matrix — copy all rows; refine vendor_response only if you add methodology detail without echoing requirement text"""
        if llm_refines_compliance_matrix
        else """2. Return "compliance_matrix": [] — compliance rows are assembled server-side from pipeline.pre_built_compliance_matrix; do NOT generate matrix rows"""
    )
    return f"""Document (RFP): {document_name}

## PRE-COMPUTED PIPELINE CONTEXT (authoritative — follow exactly)
{pipeline_context_json}

## Briefing (for evaluation weighting and client context only — do NOT copy into executive summary)
{briefing_json}

## Supplemental RFP chunks
{supplemental_chunks_json}

Generate the full technical proposal JSON.

MANDATORY:
1. Weight section depth by pipeline.evaluation_weights.weights
{matrix_instruction}
3. Use methodology_framework slots from match_plans when writing staffing/security sections
4. Link evidence via evidence_id from pipeline.evidence_index
5. Include pipeline.gaps in gaps_and_placeholders
6. Follow pipeline.section_plan emphasis/priority
7. Set confidence_score on sections using evidence coverage honesty"""


# Legacy v1 exports kept for reference
PROPOSAL_OUTPUT_SCHEMA = PROPOSAL_OUTPUT_SCHEMA_V2
PROPOSAL_SYSTEM_PROMPT = PROPOSAL_SYSTEM_PROMPT_V2


def proposal_user_prompt(
    *,
    document_name: str,
    extractions_json: str,
    briefing_json: str,
    supplemental_chunks_json: str,
    bidder_profile_json: str,
) -> str:
    """Legacy signature — redirects to v2 when pipeline context is embedded in extractions_json."""
    import json

    try:
        pipeline = json.loads(extractions_json)
        if "requirements" in pipeline and "evidence_index" in pipeline:
            return proposal_user_prompt_v2(
                document_name=document_name,
                pipeline_context_json=extractions_json,
                briefing_json=briefing_json,
                supplemental_chunks_json=supplemental_chunks_json,
            )
    except json.JSONDecodeError:
        pass

    return f"""Document (RFP): {document_name}
Structured extractions: {extractions_json}
Briefing: {briefing_json}
Supplemental chunks: {supplemental_chunks_json}
Bidder profile: {bidder_profile_json}
Produce technical proposal JSON."""
