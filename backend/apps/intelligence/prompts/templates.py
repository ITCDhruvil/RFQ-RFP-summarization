EXTRACTION_SYSTEM_PROMPT = """You are an enterprise procurement intelligence analyst extracting structured facts from RFQ/RFP/tender documents.

Rules:
- Extract ONLY information explicitly stated or clearly implied in the provided text (e.g. rejection rights, mandatory compliance, liability transfer).
- Do NOT invent calendar dates, amounts, or percentages not in the text.
- Every item MUST include section and a verbatim source_text snippet from the input.
- For "page": use the PDF page where source_text appears if stated in the text (e.g. "--- Page 21 ---"); otherwise omit page — do NOT infer page from clause numbers like 5.4.4 or 4.16.1.
- For "section": use the document section heading (e.g. 4.4 Commercial Terms), NOT internal paragraph sub-numbering alone (e.g. do not cite only "5.4.4" when the clause sits under section 4.4).
- Prefer complete, procurement-actionable statements (obligations, thresholds, weightings, guarantees, deliverables).
- Extract operational/support/governance obligations with the same priority as development scope.
- Include strategic-risk clauses: tender cancellation without cause, subcontractor liability on main contractor, lowest-bidder commercial formula pressure, MEM/owner discretion.
- If the section has no relevant content, return {"items": []}.
- Respond with valid JSON only."""

EXTRACTION_TYPE_INSTRUCTIONS = {
    "eligibility_criteria": (
        "Extract ALL bidder eligibility and qualification requirements: experience years, "
        "certifications, turnover, JV conditions, local content, mandatory registrations, "
        "technical disqualification thresholds (e.g. minimum marks), and compliance prerequisites."
    ),
    "submission_deadlines": (
        "Extract ALL schedule milestones from Timeline tables and narrative: "
        "Advertised/Issue Date, Proposer's Conference (treat as pre-bid / pre-proposal "
        "conference even if not labeled 'pre-bid'), Technical Questions Due, Proposal Due Date, "
        "pre-registration deadlines, protest deadlines, contract term dates. "
        "US public-sector RFPs often say 'Proposer's Conference' or 'Pre-Proposal Conference' "
        "instead of 'pre-bid' — extract every one with full date AND time (e.g. "
        "'January 28, 2025 at 11:00 AM'). "
        "For each item set label (short name), date_time (full date+time from document, or null), "
        "and value (URL or detail when not a calendar date). "
        "requirement must be 'label: date_time or value' as one line. Never return only the "
        "label without the date/time/URL."
    ),
    "technical_requirements": (
        "Extract ALL technical and operational service obligations — IT systems AND physical/"
        "managed services. Include: software (portal, SSO, integrations, VAPT, hosting, SLA/uptime), "
        "AND security/manpower services (guarding, escort, patrol, access control, CCTV, transport "
        "security, deployment headcount, shift patterns, 24x7 coverage, standby/reserve manpower, "
        "training/certification, uniforms/equipment, emergency/incident response, audit support, "
        "women-employee safety protocols, statutory labor compliance, background checks, and "
        "location-specific operating rules."
    ),
    "scope_of_work": (
        "Extract the primary business objective of the tender and all operational deliverables: "
        "service lines (e.g. transport escort security, facility guarding), geographic locations/sites, "
        "deployment scale (headcount, vehicles, posts), shift/roster models, milestones, duration, "
        "vendor vs client responsibilities, subcontractor rules, standby manpower obligations, "
        "labor/statutory compliance duties, and post-award operating expectations."
    ),
    "payment_terms": (
        "Extract ALL commercial and pricing terms: fixed-price vs T&M, taxes/expenses inclusion, "
        "commercial proposal validity, payment milestones, invoicing rules (main contractor only), "
        "retention, currency, performance guarantee %, advance payment bond, bank guarantees, "
        "price adjustment rules for non-quoted items, commercial evaluation formula "
        "(e.g. Lowest Bidder Price / Bidder Price * 100), and evaluation weighting if stated."
    ),
    "penalties_and_risks": (
        "Extract procurement risks and consequences — NOT only words 'penalty' or 'liquidated damages'. "
        "Include: rejection/cancellation, BAFO/price rules, funding/payment limits, indemnities, "
        "liquidated damages, bonds/guarantees, liability, subcontractor risk, amendment rights, "
        "and lowest-bidder commercial pressure. "
        "For EACH item set severity: "
        "critical = direct financial loss or payment risk ($, %, damages, LDs, bonds, overpayment, "
        "appropriation/funding failure, BAFO must be lower price, termination with cost); "
        "medium = award/compliance/commercial exposure without stated dollar impact; "
        "low = process/discretion only (e.g. may withdraw RFP) with no financial consequence in text."
    ),
    "mandatory_documents": (
        "Extract ALL mandatory submission artifacts: appendices, annexures, compliance matrices, "
        "acknowledgement forms, bank/performance guarantees, non-conformity appendix, project "
        "references, technical vs commercial proposal split, CVs, SLA document, and required forms."
    ),
    "evaluation_criteria": (
        "Extract ALL information about how proposals will be evaluated and awarded. Include: "
        "explicit weightings (e.g. 70/30 technical/commercial), minimum pass marks, scoring rubrics, "
        "evaluation committee process, best-value or lowest-price-technically-acceptable (LPTA) basis, "
        "oral presentations or demonstrations required, ranked/rated factors, pass/fail thresholds, "
        "and any language describing how the County/agency will select a winner. "
        "If no numeric scores exist, extract the qualitative selection language (e.g. 'County reserves "
        "the right to select the proposal most advantageous to the County'). "
        "Never return empty — every RFP has some form of award/selection language."
    ),
}


def extraction_user_prompt(extraction_type: str, chunk_text: str, section_title: str) -> str:
    instruction = EXTRACTION_TYPE_INSTRUCTIONS.get(
        extraction_type, "Extract all procurement-critical information in this category."
    )
    return f"""Extraction focus: {extraction_type.replace('_', ' ').title()}
Task: {instruction}

Document section context (use for section field): {section_title}

Document text:
---
{chunk_text}
---

Return JSON:
{{
  "items": [
    {{
      "requirement": "clear procurement-ready statement (for deadlines: 'Label: date, time, or URL')",
      "severity": "critical | medium | low (required for penalties_and_risks only, else omit)",
      "label": "short deadline name (optional)",
      "date_time": "full date and time from document, or null",
      "value": "URL or non-date detail (e.g. portal link), or null",
      "page": integer or null,
      "section": "document section heading or clause ref under that heading",
      "source_text": "verbatim excerpt from document text above",
      "confidence": 0.0 to 1.0
    }}
  ]
}}"""


SUMMARY_SYSTEM_PROMPT = """You are a senior procurement intelligence analyst producing a bid/no-bid briefing for enterprise RFQ/RFP tenders.

This is NOT a shallow document summary. Prioritize signals that affect bid decision, cost, risk, and compliance.

Priority order when synthesizing:
1. Primary procurement objective and operational/service scope (what is being bought, where, at what scale — headcount, sites, service lines, 24x7/shift model) when present in scope_of_work or technical_requirements extractions
2. Mandatory requirements and disqualification thresholds
3. Evaluation weighting and commercial model (fixed price, guarantees, bonds, lowest-bidder formula)
4. Contractual liabilities, rejection rights, cancellation rights, and performance accountability
5. SLA, multi-year 24x7 support, operational burden, and implementation obligations
6. Submission/compliance artifacts

Executive summary structure (when operational extractions exist):
- Sentence 1–2: primary service objective, locations, scale (e.g. personnel count), and core operational duties
- Remaining sentences: evaluation/commercial model, key compliance/submission points, and top risks
- NEVER claim technical requirements or scope of work are "absent", "missing", or "not detailed" when scope_of_work or technical_requirements extractions contain any items
- Do not let generic legal/boilerplate clauses dominate the executive summary when specific operational extractions exist

Priority scoring (procurement_critical_signals):
- HIGH: disqualification thresholds, 70/30 or similar weighting, fixed-price/rejection rules, guarantees/bonds, tender cancellation, subcontractor liability, dominant technical scoring criteria, multi-year 24x7/SLA operational burden, VAPT, lowest-bidder commercial formula
- MEDIUM: supporting detail that does not alone change bid economics

Rules:
- Use ONLY the structured extractions provided. Do not invent facts.
- For every entry in "sources", copy page, section, and source_text CHARACTER-FOR-CHARACTER from a single extraction item. source_text must be a verbatim excerpt from the extraction JSON — never paraphrase, summarize, or rewrite. Paraphrased citations are discarded by the system.
- Narrative fields (text, signal, insight, item) may be written in clear prose; only source_text must stay verbatim.
- NEVER write bare "not found" if extractions contain partial, procedural, or indirect information — explain what IS and IS NOT in the document.
- Executive summary must be 5–8 sentences. Lead with operational/service scope when scope_of_work or technical_requirements extractions have items; then cover evaluation, commercial model, compliance, and top risks.
- Be specific (percentages, weightings, durations) when extractions include them.
- Deduplicate aggressively: each distinct obligation should appear ONCE in the most appropriate section; cross-reference instead of repeating verbatim across procurement_critical_signals, key_requirements, technical_scope, risks, and checklist.
- Add procurement_strategy_insights: 3–6 interpretive insights (bid strategy, scoring optimization, delivery/operational burden, commercial pressure) grounded in extractions — clearly labeled as inference from stated facts.
- Respond with valid JSON only."""

SUMMARY_OUTPUT_SCHEMA = """
{
  "executive_summary": {"text": "string (5-8 sentences, procurement intelligence tone)", "sources": [{"page": int, "section": "string", "source_text": "verbatim excerpt copied from an extraction item"}]},
  "procurement_critical_signals": [{"signal": "string", "priority": "high|medium", "sources": [...]}],
  "procurement_strategy_insights": [{"insight": "string", "implication": "string (bid/delivery/commercial consequence)", "sources": [...]}],
  "key_requirements": [{"text": "string", "sources": [...]}],
  "important_deadlines": [{"text": "short label only", "date": "full date AND time from document (e.g. February 21, 2025 by 3:30 PM) or URL/rule text — never date without time if time appears in source", "sources": [...]}],
  "technical_scope": {"text": "string (comprehensive deliverables list)", "sources": [...]},
  "commercial_terms": {"text": "string", "sources": [...]},
  "risks_and_concerns": [{"text": "string", "severity": "critical|medium|low", "sources": [...]}],
  "submission_checklist": [{"item": "string (specific document/form name)", "category": "core_proposals|commercial_pricing|forms_compliance|guarantees_bonds|team_references|other", "sources": [...]}]
}"""


def build_operational_scope_guidance(extractions: dict) -> str:
    """Inject deterministic summary hints from extraction counts (reduces false 'no scope' summaries)."""
    sow = ((extractions.get("scope_of_work") or {}).get("items") or [])
    tech = ((extractions.get("technical_requirements") or {}).get("items") or [])
    op_items = sow + tech
    if not op_items:
        return (
            "\nOperational scope note: scope_of_work and technical_requirements extractions are "
            "empty. Do not invent operational detail; summarize only what other extraction types contain.\n"
        )

    samples: list[str] = []
    for item in op_items[:12]:
        req = str(item.get("requirement") or "").strip()
        if req:
            samples.append(req[:280])

    bullet_block = "\n".join(f"- {s}" for s in samples) if samples else "- (see extraction items)"
    return (
        f"\nCRITICAL — Operational scope present ({len(sow)} scope_of_work + "
        f"{len(tech)} technical_requirements items). Executive summary MUST open with the "
        "primary service objective, deployment scale, locations, and core operational duties. "
        "Do NOT write that technical requirements or scope of work are absent or undocumented.\n"
        f"Operational facts from extractions (themes to reflect; cite sources in output):\n"
        f"{bullet_block}\n"
    )


def summary_user_prompt(extractions_json: str, document_name: str) -> str:
    import json

    try:
        extractions = json.loads(extractions_json)
    except json.JSONDecodeError:
        extractions = {}
    scope_guidance = build_operational_scope_guidance(extractions)

    return f"""Document: {document_name}

Structured extractions (ground truth — do not add facts beyond these):
{extractions_json}
{scope_guidance}
Produce a procurement intelligence briefing as JSON:
{SUMMARY_OUTPUT_SCHEMA}

Section guidance:
- procurement_critical_signals: 8–12 unique high-signal bullets (evaluation weights, guarantees, SLA/24x7 term, VAPT, fixed price, rejection rights, cancellation, subcontractor liability, lowest-bidder formula, compliance matrices). No duplicates elsewhere.
- procurement_strategy_insights: Interpretive only — e.g. "Tender favors implementation completeness over innovation", "Commercial scoring pressures aggressive pricing", "50%+ technical weight on detailed solution/specifications", "Operational support maturity is a differentiator". Each must cite extractions.
- important_deadlines: One row per deadline from submission_deadlines extractions. text = short label; date = exact date+time or URL from source_text (copy from citation, including 'by 3:30 PM' / 'at 11:00 AM'). For portal-only items, put the URL in date. Do NOT put only the label in text with an empty date.
- risks_and_concerns: Top 6–10 risks from penalties_and_risks extractions; set severity (critical/medium/low) using same financial-impact rules; critical first in list order.
- commercial_terms: Include pricing model, validity, guarantees, bonds, invoicing, evaluation formula interpretation.
- technical_scope: Comprehensive operational deliverables from scope_of_work and technical_requirements (service lines, sites, headcount/deployment, shifts, training, equipment, SLA/24x7, IT deliverables if any). Do not describe scope as absent when extractions list deliverables.
- key_requirements: 4–8 mandatory bidder qualification and compliance requirements drawn primarily
  from eligibility_criteria and mandatory_documents extractions. Focus on things a bid manager
  must verify before submitting (e.g. registration, browser/portal requirements, signed letters,
  conference pre-registration). Do NOT duplicate items already in procurement_critical_signals.
- submission_checklist: A logical **document submission register** — one discrete deliverable per item (not long paragraphs). Use category:
  - core_proposals: Technical Proposal, Commercial Proposal (main volumes)
  - commercial_pricing: Commercial summary table, phase-wise cost breakup, pricing schedules
  - forms_compliance: Annexures, appendices, RFP Compliance Matrix, SLA document, mandatory forms
  - guarantees_bonds: Performance Guarantee, Advance Payment Bond, bank guarantees
  - team_references: CVs/resumes, project references with contacts, experience evidence
  Order items within each category from general → specific. 10–20 items when extractions support it.

Combine and deduplicate across sections. Empty sections only when zero supporting extraction items exist across ALL types."""
