"""LLM prompts for commercial proposal narrative sections only."""

from __future__ import annotations

import json

COMMERCIAL_SYSTEM_PROMPT = """You are an enterprise bid writer producing the NARRATIVE sections of a commercial proposal.

CRITICAL RULES:
1. NEVER invent, calculate, or modify pricing numbers. All figures are provided in pricing_engine_output.
2. Reference pricing ONLY by quoting the exact numbers from pricing_engine_output.
3. Do not add roles, quantities, or rates not present in pricing_engine_output.
4. Write professional enterprise bid language — each section minimum 2 paragraphs unless noted.
5. cover_letter and executive_summary must be submission-ready (formal tone, specific to the RFP).
6. Return valid JSON matching the output schema exactly.
7. Assumptions and exclusions provided are authoritative — do not contradict them.
"""

COMMERCIAL_OUTPUT_SCHEMA = {
    "cover_letter": {"body": "string"},
    "executive_summary": {"body": "string"},
    "taxes_and_duties": {"body": "string"},
    "payment_terms": {"body": "string"},
    "price_validity": {"body": "string"},
    "commercial_terms": {"body": "string"},
    "sign_off": {"authorized_signatory": "string", "designation": "string", "body": "string"},
    "meta": {
        "document_name": "string",
        "volumes": ["commercial"],
        "currency": "string",
    },
}


def commercial_user_prompt(
    *,
    document_name: str,
    requirements_json: str,
    vendor_profile_json: str,
    pricing_engine_json: str,
    assumptions_json: str,
    exclusions_json: str,
    terms_json: str,
    section_plan_json: str,
) -> str:
    return f"""Document: {document_name}

## RFP commercial requirements (extracted)
{requirements_json}

## Vendor commercial profile
{vendor_profile_json}

## PRICING ENGINE OUTPUT (AUTHORITATIVE — use these numbers verbatim)
{pricing_engine_json}

## Commercial assumptions (authoritative)
{assumptions_json}

## Commercial exclusions (authoritative)
{exclusions_json}

## Commercial terms
{terms_json}

## Section plan
{section_plan_json}

Write narrative sections only. Pricing tables, resource pricing, cost breakdown, assumptions list, and exclusions list are injected separately from the pricing engine.

Output schema:
{json.dumps(COMMERCIAL_OUTPUT_SCHEMA, indent=2)}
"""
