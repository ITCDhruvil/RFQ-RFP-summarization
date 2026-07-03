"""Schemas for enterprise commercial proposal generation."""

from __future__ import annotations

from typing import Any, TypedDict

COMMERCIAL_PIPELINE_VERSION = "1.0.0"

DEFAULT_COMMERCIAL_VENDOR_PROFILE: dict[str, Any] = {
    "currency": "INR",
    "default_gst_percent": 18.0,
    "default_margin_percent": 15.0,
    "payment_terms_days": 45,
    "price_validity_days": 90,
    "rate_cards": [],
    "resource_rates": [],
    "commercial_assumptions": [],
    "commercial_exclusions": [],
}

DEFAULT_WORKBENCH: dict[str, Any] = {
    "requirements": {},
    "questionnaire_answers": {},
    "pricing": {"resource_lines": [], "summary": {}},
    "assumptions": [],
    "exclusions": [],
    "terms": {
        "payment_terms_days": None,
        "price_validity_days": None,
        "currency": None,
        "tax_notes": "",
    },
    "gap_report": {"missing_commercial_inputs": [], "questions": []},
    "validation_report": {},
}


class CommercialQuestion(TypedDict, total=False):
    field_key: str
    label: str
    section: str
    required: bool
    input_type: str
    placeholder: str
    options: list[str]


class ResourcePricingLine(TypedDict, total=False):
    role_key: str
    role_label: str
    line_type: str
    billing_basis: str
    quantity: int
    unit_cost_monthly: float
    margin_percent: float
    gst_percent: float
    monthly_cost: float
    annual_cost: float
    total_with_margin: float


def normalize_commercial_vendor_profile(raw: dict | None) -> dict[str, Any]:
    base = dict(DEFAULT_COMMERCIAL_VENDOR_PROFILE)
    if not raw or not isinstance(raw, dict):
        return base
    base["currency"] = str(raw.get("currency") or base["currency"]).strip().upper()[:8]
    base["default_gst_percent"] = _float(raw.get("default_gst_percent"), base["default_gst_percent"])
    base["default_margin_percent"] = _float(
        raw.get("default_margin_percent"), base["default_margin_percent"]
    )
    base["payment_terms_days"] = _int(raw.get("payment_terms_days"), base["payment_terms_days"])
    base["price_validity_days"] = _int(raw.get("price_validity_days"), base["price_validity_days"])
    base["rate_cards"] = _list_of_dicts(raw.get("rate_cards"))
    base["resource_rates"] = _list_of_dicts(raw.get("resource_rates"))
    base["commercial_assumptions"] = _list_of_str(raw.get("commercial_assumptions"))
    base["commercial_exclusions"] = _list_of_str(raw.get("commercial_exclusions"))
    base["company_legal_name"] = str(raw.get("company_legal_name") or "").strip()
    base["authorized_signatory"] = str(raw.get("authorized_signatory") or "").strip()
    base["signatory_designation"] = str(raw.get("signatory_designation") or "").strip()
    return base


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _list_of_str(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _list_of_dicts(value: Any) -> list[dict]:
    if not isinstance(value, list):
        return []
    return [x for x in value if isinstance(x, dict)]
