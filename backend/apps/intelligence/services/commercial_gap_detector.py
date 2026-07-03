"""Detect missing commercial inputs vs RFP requirements and vendor profile."""

from __future__ import annotations

import re
from typing import Any
from apps.intelligence.services.commercial_schemas import CommercialQuestion


_QUESTION_TEMPLATES: dict[str, dict[str, Any]] = {
    "security_guard_rate": {
        "label": "Monthly cost per Security Guard",
        "section": "Resource Rates",
        "input_type": "currency",
        "placeholder": "25000",
    },
    "supervisor_rate": {
        "label": "Monthly cost per Supervisor",
        "section": "Resource Rates",
        "input_type": "currency",
        "placeholder": "35000",
    },
    "desired_margin_percent": {
        "label": "Desired margin %",
        "section": "Margins",
        "input_type": "percent",
        "placeholder": "15",
    },
    "price_validity_days": {
        "label": "Price validity (days)",
        "section": "Commercial Terms",
        "input_type": "number",
        "placeholder": "90",
    },
    "payment_terms_days": {
        "label": "Payment terms (days)",
        "section": "Commercial Terms",
        "input_type": "number",
        "placeholder": "45",
    },
    "default_gst_percent": {
        "label": "GST / tax %",
        "section": "Taxes",
        "input_type": "percent",
        "placeholder": "18",
    },
    "currency": {
        "label": "Proposal currency",
        "section": "Pricing Model",
        "input_type": "select",
        "options": ["INR", "USD", "EUR", "GBP"],
    },
    "mobilization_fee": {
        "label": "Mobilization / setup fee (one-time)",
        "section": "Additional Commercial",
        "input_type": "currency",
        "placeholder": "500000",
    },
    "equipment_budget": {
        "label": "Equipment / capex budget (annual)",
        "section": "Additional Commercial",
        "input_type": "currency",
        "placeholder": "250000",
    },
    "contingency_percent": {
        "label": "Contingency %",
        "section": "Additional Commercial",
        "input_type": "percent",
        "placeholder": "5",
    },
}


def _has_rate(profile: dict, key: str, answers: dict) -> bool:
    if answers.get(key) not in (None, ""):
        return True
    for rate in profile.get("resource_rates") or []:
        if isinstance(rate, dict) and rate.get("role_key") == key and rate.get("unit_cost_monthly"):
            return True
    return False


def _has_value(profile: dict, profile_key: str, answer_key: str, answers: dict) -> bool:
    if answers.get(answer_key) not in (None, ""):
        return True
    val = profile.get(profile_key)
    return val not in (None, "", 0)


def detect_commercial_gaps(
    requirements: dict[str, Any],
    vendor_profile: dict[str, Any],
    questionnaire_answers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    answers = dict(questionnaire_answers or {})
    missing: list[str] = []
    questions: list[CommercialQuestion] = []

    def need(field_key: str, label: str, check: bool) -> None:
        if check:
            return
        missing.append(label)
        tpl = _QUESTION_TEMPLATES.get(field_key, {})
        questions.append(
            CommercialQuestion(
                field_key=field_key,
                label=tpl.get("label") or label,
                section=tpl.get("section") or "Commercial",
                required=True,
                input_type=tpl.get("input_type") or "text",
                placeholder=str(tpl.get("placeholder") or ""),
                options=tpl.get("options") or [],
            )
        )

    need(
        "currency",
        "Proposal currency",
        bool(requirements.get("currency") or vendor_profile.get("currency") or answers.get("currency")),
    )
    need(
        "default_gst_percent",
        "GST / tax %",
        _has_value(vendor_profile, "default_gst_percent", "default_gst_percent", answers),
    )
    need(
        "desired_margin_percent",
        "Desired margin %",
        _has_value(vendor_profile, "default_margin_percent", "desired_margin_percent", answers),
    )
    need(
        "payment_terms_days",
        "Payment terms",
        _has_value(vendor_profile, "payment_terms_days", "payment_terms_days", answers)
        or bool(requirements.get("payment_terms_snippet")),
    )
    need(
        "price_validity_days",
        "Price validity",
        _has_value(vendor_profile, "price_validity_days", "price_validity_days", answers),
    )

    if requirements.get("resource_count"):
        need(
            "security_guard_rate",
            "Security Guard monthly rate",
            _has_rate(vendor_profile, "security_guard", answers),
        )
        need(
            "supervisor_rate",
            "Supervisor monthly rate",
            _has_rate(vendor_profile, "supervisor", answers),
        )

    # De-duplicate questions by field_key
    seen: set[str] = set()
    unique_questions: list[CommercialQuestion] = []
    for q in questions:
        if q["field_key"] in seen:
            continue
        seen.add(q["field_key"])
        unique_questions.append(q)

    # Optional RFP-driven prompts (always visible for user to fill or skip)
    optional_keys: list[str] = []
    combined_text = " ".join(
        str(requirements.get(key) or "")
        for key in (
            "payment_terms_snippet",
            "billing_frequency",
            "contract_duration",
            "price_revision_clause",
            "guarantee_requirements",
        )
    ).lower()
    if re.search(r"mobiliz|setup\s+fee|transition\s+cost", combined_text):
        optional_keys.append("mobilization_fee")
    if re.search(r"equipment|capex|uniform|vehicle|asset", combined_text):
        optional_keys.append("equipment_budget")
    if re.search(r"contingenc|escalat|price\s+revision", combined_text):
        optional_keys.append("contingency_percent")

    for field_key in optional_keys:
        if field_key in seen:
            continue
        tpl = _QUESTION_TEMPLATES.get(field_key, {})
        unique_questions.append(
            CommercialQuestion(
                field_key=field_key,
                label=str(tpl.get("label") or field_key),
                section=str(tpl.get("section") or "Additional Commercial"),
                required=False,
                input_type=str(tpl.get("input_type") or "text"),
                placeholder=str(tpl.get("placeholder") or ""),
                options=tpl.get("options") or [],
            )
        )
        seen.add(field_key)

    return {
        "missing_commercial_inputs": missing,
        "questions": unique_questions,
        "ready_for_pricing": len(missing) == 0,
    }
