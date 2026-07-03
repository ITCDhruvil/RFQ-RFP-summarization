"""Generate commercial exclusions from profile and RFP signals."""

from __future__ import annotations

from typing import Any


_BASE_EXCLUSIONS = [
    "Emergency or ad-hoc staffing surges are excluded unless separately agreed.",
    "Additional locations beyond those listed in the pricing schedule are excluded.",
    "Specialized equipment procurement is excluded unless explicitly priced.",
    "Changes in government levies or statutory rates after submission are excluded.",
    "Client-furnished consumables and uniforms are excluded unless stated otherwise.",
]


def generate_commercial_exclusions(
    requirements: dict[str, Any],
    vendor_profile: dict[str, Any],
    questionnaire_answers: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    exclusions: list[dict[str, str]] = []
    seen: set[str] = set()

    def add(text: str, source: str = "system") -> None:
        key = text.lower().strip()
        if not key or key in seen:
            return
        seen.add(key)
        exclusions.append({"text": text, "source": source, "editable": "true"})

    for text in _BASE_EXCLUSIONS:
        add(text, "template")
    for text in vendor_profile.get("commercial_exclusions") or []:
        add(str(text), "vendor_profile")

    if requirements.get("penalties_snippet"):
        add(
            "Liquidated damages or penalties apply only as per the RFP; no indirect losses are accepted.",
            "rfp",
        )

    answers = questionnaire_answers or {}
    if answers.get("commercial_exclusions_note"):
        add(str(answers["commercial_exclusions_note"]), "questionnaire")

    return exclusions
