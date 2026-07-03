"""Build classified requirement registry from extraction insights."""

from __future__ import annotations

import re
from typing import Any

from apps.intelligence.models import ExtractedInsight
from apps.intelligence.services.proposal_schemas import (
    ClassifiedRequirement,
    RequirementCategory,
    classify_requirement_text,
)

_REQUIREMENT_EXTRACTION_TYPES = (
    "technical_requirements",
    "scope_of_work",
    "mandatory_documents",
    "eligibility_criteria",
    "evaluation_criteria",
    "payment_terms",
    "penalties_and_risks",
)


def _item_text(item: dict[str, Any]) -> str:
    return str(item.get("requirement") or item.get("text") or "").strip()


def build_requirement_registry(
    insights: list[ExtractedInsight],
) -> list[ClassifiedRequirement]:
    """Extract and classify all proposal-relevant requirements."""
    registry: list[ClassifiedRequirement] = []
    seen: set[str] = set()
    counter = 0

    for insight in insights:
        if insight.extraction_type not in _REQUIREMENT_EXTRACTION_TYPES:
            continue
        items = (insight.payload or {}).get("items") or []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = _item_text(item)
            if not text or len(text) < 8:
                continue
            key = re.sub(r"\s+", " ", text.lower())[:200]
            if key in seen:
                continue
            seen.add(key)
            counter += 1
            category = classify_requirement_text(text, insight.extraction_type)
            prefix = _category_prefix(category)
            registry.append(
                ClassifiedRequirement(
                    requirement_id=f"{prefix}-{counter:02d}",
                    category=category.value,
                    requirement=text,
                    page=int(item.get("page") or 0),
                    section=str(item.get("section") or ""),
                    source_text=str(item.get("source_text") or text)[:500],
                    extraction_type=insight.extraction_type,
                )
            )

    return registry


def _category_prefix(category: RequirementCategory) -> str:
    return {
        RequirementCategory.STAFFING: "STF",
        RequirementCategory.SECURITY: "SEC",
        RequirementCategory.TRAINING: "TRN",
        RequirementCategory.TRANSITION: "TRN",
        RequirementCategory.REPORTING: "RPT",
        RequirementCategory.COMPLIANCE: "CMP",
        RequirementCategory.LEGAL: "LEG",
        RequirementCategory.COMMERCIAL: "COM",
        RequirementCategory.IMPLEMENTATION: "IMP",
        RequirementCategory.OPERATIONAL: "OPS",
        RequirementCategory.TECHNICAL: "TEC",
    }.get(category, "REQ")
