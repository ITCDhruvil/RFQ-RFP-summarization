import re
from typing import Any

from apps.intelligence.choices import ExtractionType
from apps.intelligence.services.citation_service import canonicalize_extraction_item


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def validate_and_score_items(
    items: list[dict[str, Any]],
    *,
    chunk_text: str,
    section_title: str,
    page_start: int,
    page_end: int,
    total_pages: int,
    page_texts: list[tuple[int, str]] | None = None,
) -> list[dict[str, Any]]:
    """Grounding validation with canonical page/section resolution."""
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    pages = page_texts or []

    for raw in items:
        if not isinstance(raw, dict):
            continue

        requirement = str(raw.get("requirement") or "").strip()
        if not requirement:
            continue

        dedupe_key = _normalize(requirement)[:200]
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        item = canonicalize_extraction_item(
            raw,
            chunk_text=chunk_text,
            section_title=section_title,
            page_start=page_start,
            page_end=page_end,
            total_pages=total_pages,
            page_texts=pages,
        )
        if item.get("requirement"):
            validated.append(item)

    return validated


def aggregate_confidence(items: list[dict[str, Any]]) -> float:
    if not items:
        return 0.0
    return round(sum(i["confidence"] for i in items) / len(items), 4)


def detect_missing_extractions(present_types: set[str]) -> list[str]:
    from apps.intelligence.choices import FOCUSED_EXTRACTION_TYPES

    missing = []
    for ext_type in FOCUSED_EXTRACTION_TYPES:
        if ext_type not in present_types:
            missing.append(ext_type)
    return missing


def merge_insight_items(all_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate across chunks for same extraction type."""
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for item in all_items:
        key = _normalize(item.get("requirement", ""))[:200]
        if not key or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged
