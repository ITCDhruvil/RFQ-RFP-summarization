"""Parse evaluation criteria weights to drive proposal emphasis."""

from __future__ import annotations

import re
from typing import Any

from apps.intelligence.models import ExtractedInsight
from apps.intelligence.services.proposal_schemas import RequirementCategory

_WEIGHT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "technical": ("technical", "solution", "specification", "approach", "methodology"),
    "staffing": ("staffing", "manpower", "personnel", "guards", "workforce", "deployment"),
    "compliance": ("compliance", "mandatory", "document", "eligibility", "registration"),
    "experience": ("experience", "reference", "past performance", "track record", "portfolio"),
    "commercial": ("commercial", "price", "pricing", "cost", "financial"),
    "operational": ("operational", "sla", "service level", "24/7", "delivery"),
    "training": ("training", "competency", "certification program"),
    "transition": ("transition", "mobilization", "implementation"),
}

_CATEGORY_TO_WEIGHT_KEY: dict[str, str] = {
    RequirementCategory.STAFFING.value: "staffing",
    RequirementCategory.SECURITY.value: "operational",
    RequirementCategory.OPERATIONAL.value: "operational",
    RequirementCategory.TECHNICAL.value: "technical",
    RequirementCategory.COMPLIANCE.value: "compliance",
    RequirementCategory.TRAINING.value: "training",
    RequirementCategory.TRANSITION.value: "transition",
    RequirementCategory.IMPLEMENTATION.value: "transition",
    RequirementCategory.COMMERCIAL.value: "commercial",
}

_DEFAULT_WEIGHTS: dict[str, float] = {
    "technical": 0.25,
    "staffing": 0.20,
    "compliance": 0.15,
    "experience": 0.15,
    "commercial": 0.15,
    "operational": 0.10,
}

_SECTION_WEIGHT_MAP: dict[str, str] = {
    "executive_summary": "technical",
    "company_overview": "experience",
    "why_choose_us": "experience",
    "staffing_approach": "staffing",
    "service_delivery_model": "operational",
    "training_framework": "training",
    "transition_plan": "transition",
    "sla_and_operations": "operational",
    "compliance_matrix": "compliance",
    "technical_approach": "technical",
}


def parse_evaluation_weights(insights: list[ExtractedInsight]) -> dict[str, Any]:
    raw_weights: dict[str, float] = {}
    criteria_items: list[str] = []

    for insight in insights:
        if insight.extraction_type != "evaluation_criteria":
            continue
        for item in (insight.payload or {}).get("items") or []:
            text = str(item.get("requirement") or item.get("source_text") or "")
            if not text:
                continue
            criteria_items.append(text)
            lowered = text.lower()
            m = re.search(r"(\d{1,3})\s*%", text)
            if not m:
                continue
            pct = int(m.group(1))
            if not (0 < pct <= 100):
                continue
            weight = pct / 100.0
            for key, keywords in _WEIGHT_KEYWORDS.items():
                if any(kw in lowered for kw in keywords):
                    raw_weights[key] = max(raw_weights.get(key, 0), weight)

    if raw_weights:
        total = sum(raw_weights.values())
        normalized = (
            {k: round(v / total, 3) for k, v in raw_weights.items()}
            if total > 0
            else dict(_DEFAULT_WEIGHTS)
        )
        source = "extracted"
    else:
        normalized = dict(_DEFAULT_WEIGHTS)
        source = "default"

    return {
        "weights": normalized,
        "source": source,
        "criteria_items": criteria_items[:20],
    }


def section_emphasis_score(section_id: str, eval_weights: dict[str, float]) -> float:
    key = _SECTION_WEIGHT_MAP.get(section_id, "technical")
    return eval_weights.get(key, 0.1)


def category_emphasis(category: str, eval_weights: dict[str, float]) -> float:
    key = _CATEGORY_TO_WEIGHT_KEY.get(category, "technical")
    return eval_weights.get(key, 0.1)
