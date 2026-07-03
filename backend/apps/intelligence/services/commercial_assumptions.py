"""Generate commercial assumptions from profile, RFP, and questionnaire."""

from __future__ import annotations

from typing import Any


_BASE_ASSUMPTIONS = [
    "Client will provide workspace and basic utilities at each site.",
    "Prices assume baseline staffing levels stated in the pricing schedule.",
    "Additional staffing or surge requirements will be billed separately.",
    "Client will provide timely access for site surveys and mobilization.",
]

_RFP_DERIVED = [
    ("taxes_mentioned", "Pricing includes applicable taxes as stated in the RFP."),
    ("performance_guarantee_required", "Performance guarantee will be furnished per RFP requirements."),
    ("price_revision_allowed", "Price revision clauses will apply only as permitted in the RFP."),
    ("billing_frequency", "Invoicing frequency aligns with RFP billing requirements: {billing_frequency}."),
]


def generate_commercial_assumptions(
    requirements: dict[str, Any],
    vendor_profile: dict[str, Any],
    questionnaire_answers: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    assumptions: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(text: str, source: str = "system") -> None:
        key = text.lower().strip()
        if not key or key in seen:
            return
        seen.add(key)
        assumptions.append({"text": text, "source": source, "editable": "true"})

    for text in _BASE_ASSUMPTIONS:
        add(text, "template")
    for text in vendor_profile.get("commercial_assumptions") or []:
        add(str(text), "vendor_profile")
    for key, template in _RFP_DERIVED:
        if requirements.get(key):
            val = requirements.get("billing_frequency") if key == "billing_frequency" else ""
            add(template.format(billing_frequency=val or "as specified"), "rfp")

    if requirements.get("contract_duration"):
        add(
            f"Contract pricing is based on a duration of {requirements['contract_duration']}.",
            "rfp",
        )

    answers = questionnaire_answers or {}
    if answers.get("commercial_assumptions_note"):
        add(str(answers["commercial_assumptions_note"]), "questionnaire")

    return assumptions
