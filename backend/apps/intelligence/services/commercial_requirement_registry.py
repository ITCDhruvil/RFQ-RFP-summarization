"""Extract structured commercial requirements from RFP intelligence."""

from __future__ import annotations

import re
from typing import Any

from apps.intelligence.models import ExtractedInsight

_COMMERCIAL_EXTRACTION_TYPES = (
    "payment_terms",
    "penalties_and_risks",
    "scope_of_work",
    "mandatory_documents",
    "evaluation_criteria",
    "eligibility_criteria",
)

_CURRENCY_PATTERNS = (
    (re.compile(r"\bINR\b|₹|rupees?\b", re.I), "INR"),
    (re.compile(r"\bUSD\b|\$|dollars?\b", re.I), "USD"),
    (re.compile(r"\bEUR\b|€|euros?\b", re.I), "EUR"),
    (re.compile(r"\bGBP\b|£|pounds?\b", re.I), "GBP"),
)

_DURATION_RE = re.compile(
    r"(\d+)\s*(months?|years?|yrs?)\b",
    re.I,
)
_BILLING_RE = re.compile(
    r"\b(monthly|quarterly|annual|yearly|weekly|bi-?weekly)\b",
    re.I,
)
_RESOURCE_COUNT_RE = re.compile(
    r"(\d{1,5})\s*(?:security\s+guards?|guards?|personnel|staff|resources?|headcount|FTEs?)\b",
    re.I,
)
_PRICE_REVISION_RE = re.compile(
    r"(price\s+revision|escalation|indexation|annual\s+increase)",
    re.I,
)
_GUARANTEE_RE = re.compile(
    r"(performance\s+guarantee|bank\s+guarantee|security\s+deposit|earnest\s+money)",
    re.I,
)
_TAX_RE = re.compile(r"\b(GST|VAT|tax|dut(?:y|ies))\b", re.I)
_INVOICE_RE = re.compile(r"\b(invoice|invoicing|billing)\b", re.I)
_PENALTY_RE = re.compile(r"\b(penalt(?:y|ies)|liquidated\s+damages|LD)\b", re.I)


def _collect_texts(insights: list[ExtractedInsight]) -> list[str]:
    texts: list[str] = []
    for insight in insights:
        if insight.extraction_type not in _COMMERCIAL_EXTRACTION_TYPES:
            continue
        for item in (insight.payload or {}).get("items") or []:
            if not isinstance(item, dict):
                continue
            text = str(item.get("requirement") or item.get("text") or "").strip()
            if text:
                texts.append(text)
    return texts


def _detect_currency(text: str) -> str | None:
    for pattern, code in _CURRENCY_PATTERNS:
        if pattern.search(text):
            return code
    return None


def _detect_duration(text: str) -> str | None:
    match = _DURATION_RE.search(text)
    if not match:
        return None
    return f"{match.group(1)} {match.group(2).lower()}"


def _detect_billing(text: str) -> str | None:
    match = _BILLING_RE.search(text)
    return match.group(1).title() if match else None


def _detect_resource_count(texts: list[str]) -> int | None:
    counts: list[int] = []
    for text in texts:
        for match in _RESOURCE_COUNT_RE.finditer(text):
            try:
                counts.append(int(match.group(1)))
            except ValueError:
                continue
    return max(counts) if counts else None


def _first_match_snippet(texts: list[str], pattern: re.Pattern[str]) -> str | None:
    for text in texts:
        if pattern.search(text):
            return text[:300]
    return None


def build_commercial_requirement_registry(
    insights: list[ExtractedInsight],
) -> dict[str, Any]:
    """Build structured commercial requirements from extractions."""
    texts = _collect_texts(insights)
    combined = "\n".join(texts)

    currency = None
    for text in texts:
        currency = _detect_currency(text)
        if currency:
            break

    duration = None
    billing = None
    for text in texts:
        duration = duration or _detect_duration(text)
        billing = billing or _detect_billing(text)

    resource_count = _detect_resource_count(texts)

    commercial_forms = [
        t[:200]
        for t in texts
        if re.search(r"\b(form|schedule|annex|appendix|boq|bill of quantities|pricing)\b", t, re.I)
    ][:8]

    return {
        "contract_duration": duration,
        "currency": currency,
        "billing_frequency": billing,
        "resource_count": resource_count,
        "price_revision_allowed": bool(_PRICE_REVISION_RE.search(combined)),
        "performance_guarantee_required": bool(_GUARANTEE_RE.search(combined)),
        "taxes_mentioned": bool(_TAX_RE.search(combined)),
        "invoicing_terms_snippet": _first_match_snippet(texts, _INVOICE_RE),
        "payment_terms_snippet": _first_match_snippet(
            texts, re.compile(r"\b(payment|milestone|net\s+\d+)\b", re.I)
        ),
        "penalties_snippet": _first_match_snippet(texts, _PENALTY_RE),
        "commercial_forms": commercial_forms,
        "raw_clauses": texts[:25],
        "pricing_model_requirements": [
            t[:200]
            for t in texts
            if re.search(r"\b(price|pricing|rate|cost|commercial)\b", t, re.I)
        ][:12],
    }
