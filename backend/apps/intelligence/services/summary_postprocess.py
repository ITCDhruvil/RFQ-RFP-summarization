"""
Post-process LLM summary JSON: deduplication, priority tuning, citation alignment.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from apps.intelligence.services.citation_service import (
    build_extraction_citation_lookup,
    canonicalize_summary_sources,
    enforce_verbatim_summary_sources,
)

SIMILARITY_THRESHOLD = 0.72

CHECKLIST_CATEGORY_ORDER = [
    "core_proposals",
    "commercial_pricing",
    "forms_compliance",
    "guarantees_bonds",
    "team_references",
    "other",
]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _item_text(item: dict[str, Any]) -> str:
    base = str(
        item.get("signal")
        or item.get("text")
        or item.get("item")
        or item.get("insight")
        or ""
    ).strip()
    implication = str(item.get("implication") or "").strip()
    if implication:
        return f"{base} {implication}".strip()
    return base


def _is_duplicate(text: str, seen: list[str]) -> bool:
    norm = _normalize_text(text)
    if not norm:
        return True
    for prior in seen:
        if _similarity(norm, prior) >= SIMILARITY_THRESHOLD:
            return True
        # Substring overlap for long requirements
        if len(norm) > 40 and len(prior) > 40 and (norm in prior or prior in norm):
            return True
    return False


def _dedupe_list(items: list[dict], seen: list[str]) -> list[dict]:
    kept: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        text = _item_text(item)
        if _is_duplicate(text, seen):
            continue
        seen.append(_normalize_text(text))
        kept.append(item)
    return kept


def _infer_checklist_category(text: str) -> str:
    lower = text.lower()
    rules: list[tuple[str, list[str]]] = [
        (
            "guarantees_bonds",
            [
                "performance guarantee",
                "advance payment bond",
                "bank guarantee",
                " bond",
            ],
        ),
        (
            "team_references",
            [
                "cv",
                "resume",
                "reference",
                "implementation experience",
                "contact details",
                "technical team",
            ],
        ),
        (
            "forms_compliance",
            [
                "appendix",
                "annexure",
                "compliance matrix",
                "sla agreement",
                "fill all",
                "mandatory document",
                "general requirements",
            ],
        ),
        (
            "commercial_pricing",
            [
                "cost breakup",
                "breakup",
                "break-up",
                "summary table",
                "commercial proposal",
                "phase wise",
                "phase-wise",
            ],
        ),
        ("core_proposals", ["technical proposal"]),
    ]
    for category, keywords in rules:
        if any(kw in lower for kw in keywords):
            return category
    return "other"


def organize_submission_checklist(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assign category and sort into logical document-list order."""
    organized: list[dict[str, Any]] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        label = str(item.get("item") or item.get("text") or "").strip()
        if not label:
            continue
        item["item"] = label
        if not item.get("category"):
            item["category"] = _infer_checklist_category(label)
        organized.append(item)

    def sort_key(entry: dict[str, Any]) -> tuple[int, str]:
        cat = str(entry.get("category") or "other")
        try:
            idx = CHECKLIST_CATEGORY_ORDER.index(cat)
        except ValueError:
            idx = len(CHECKLIST_CATEGORY_ORDER)
        return (idx, _normalize_text(str(entry.get("item", ""))))

    return sorted(organized, key=sort_key)


def adjust_signal_priorities(signals: list[dict]) -> None:
    """Operational/commercial burden signals should not be under-prioritized."""
    high_patterns = [
        r"24\s*x\s*7",
        r"24x7",
        r"performance guarantee",
        r"advance payment bond",
        r"fixed[- ]price",
        r"lowest bidder",
        r"cancel",
        r"subcontractor",
        r"reject",
        r"70\s*/\s*30",
        r"60\s*/\s*100",
    ]
    for signal in signals:
        text = _item_text(signal).lower()
        if any(re.search(pat, text) for pat in high_patterns):
            if (signal.get("priority") or "").lower() != "high":
                signal["priority"] = "high"


def _enrich_deadline_item(item: dict[str, Any]) -> dict[str, Any]:
    """Fill date field from source_text so UI shows date+time, not label only."""
    label = str(item.get("text") or item.get("item") or "").strip()
    date = str(item.get("date") or "").strip()
    sources = item.get("sources") or []
    source_text = ""
    if sources and isinstance(sources[0], dict):
        source_text = str(sources[0].get("source_text") or "").strip()

    if source_text and label:
        pattern = re.compile(
            rf"^{re.escape(label)}\s*[:–\-]\s*(.+)$",
            re.IGNORECASE,
        )
        match = pattern.match(source_text)
        if match:
            item["date"] = match.group(1).strip()
        elif not date and len(source_text) > len(label):
            item["date"] = source_text
    elif source_text and not date:
        item["date"] = source_text
        if not label:
            item["text"] = "Deadline"

    return item


def _apply_risk_severity(item: dict[str, Any]) -> dict[str, Any]:
    from apps.intelligence.services.risk_severity import (
        classify_penalty_severity,
        normalize_severity,
    )

    text = _item_text(item)
    llm = normalize_severity(item.get("severity")) if item.get("severity") else None
    rules = classify_penalty_severity(text)
    order = {"low": 0, "medium": 1, "critical": 2}
    final = llm or rules
    if order.get(rules, 1) > order.get(final, 1):
        final = rules
    item["severity"] = final
    return item


def _enrich_risks_and_concerns(items: list) -> list[dict[str, Any]]:
    enriched = [_apply_risk_severity(i) for i in items if isinstance(i, dict)]
    order = {"critical": 0, "medium": 1, "low": 2}
    enriched.sort(
        key=lambda x: order.get(str(x.get("severity", "medium")).lower(), 1)
    )
    return enriched


def _enrich_important_deadlines(items: list) -> list[dict[str, Any]]:
    return [
        _enrich_deadline_item(i)
        for i in items
        if isinstance(i, dict)
    ]


def _load_page_texts(document) -> list[tuple[int, str]]:
    try:
        parsed = document.parsed_document
    except Exception:
        return []
    return list(
        parsed.pages.order_by("page_number").values_list("page_number", "extracted_text")
    )


def reapply_summary_citations(
    data: dict[str, Any],
    insights: list,
    document,
) -> dict[str, Any]:
    """Re-run citation grounding on stored summary JSON (no LLM call)."""
    page_texts = _load_page_texts(document)
    lookup = build_extraction_citation_lookup(insights, page_texts)
    canonicalize_summary_sources(data, lookup)
    enforce_verbatim_summary_sources(
        data,
        page_texts=page_texts,
        insights=insights,
        lookup=lookup,
    )
    return data


def postprocess_summary(
    data: dict[str, Any],
    insights: list,
    document=None,
) -> dict[str, Any]:
    if document is not None:
        reapply_summary_citations(data, insights, document)
    else:
        lookup = build_extraction_citation_lookup(insights)
        canonicalize_summary_sources(data, lookup)

    deadlines = data.get("important_deadlines")
    if isinstance(deadlines, list):
        data["important_deadlines"] = _enrich_important_deadlines(deadlines)

    risks = data.get("risks_and_concerns")
    if isinstance(risks, list):
        data["risks_and_concerns"] = _enrich_risks_and_concerns(risks)

    seen: list[str] = []

    signals = data.get("procurement_critical_signals") or []
    if isinstance(signals, list):
        adjust_signal_priorities(signals)
        for s in signals:
            if isinstance(s, dict):
                t = _item_text(s)
                if t:
                    seen.append(_normalize_text(t))

    for key in (
        "key_requirements",
        "important_deadlines",
        "risks_and_concerns",
        "procurement_strategy_insights",
    ):
        items = data.get(key)
        if isinstance(items, list):
            data[key] = _dedupe_list(items, seen)

    checklist = data.get("submission_checklist")
    if isinstance(checklist, list):
        checklist = _dedupe_list(checklist, seen)
        data["submission_checklist"] = organize_submission_checklist(checklist)

    return data
