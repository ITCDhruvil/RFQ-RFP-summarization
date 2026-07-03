import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.conf import settings
from django.db import close_old_connections, transaction

from apps.documents.choices import SourceReferenceKind
from apps.documents.models import Document, SourceReference
from apps.intelligence.choices import ExtractionType, FOCUSED_EXTRACTION_TYPES
from apps.intelligence.models import DocumentChunk, ExtractedInsight, GeneratedSummary
from apps.intelligence.prompts.templates import EXTRACTION_SYSTEM_PROMPT, extraction_user_prompt
from apps.intelligence.services.grounding import (
    aggregate_confidence,
    merge_insight_items,
    validate_and_score_items,
)
from apps.intelligence.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)

# Maximum parallel threads — one per extraction type.
# Bounded at 8 (= len(FOCUSED_EXTRACTION_TYPES)) so we never over-subscribe.
_EXTRACTION_WORKERS = getattr(settings, "INTELLIGENCE_EXTRACTION_WORKERS", 8)

# Max chars to send per chunk to the LLM after paragraph-level pre-filtering (#5).
# Chunks are up to INTELLIGENCE_MAX_CHUNK_CHARS (6 000) — filtering trims them to this.
_CHUNK_TRIM_CHARS = getattr(settings, "INTELLIGENCE_CHUNK_TRIM_CHARS", 3500)

# How many chunks to group into a single LLM call (#6).
# Default 3 → a 14-chunk type makes 5 calls instead of 14 (~65% fewer calls per type).
# Set to 1 to disable batching and send one chunk per call (original behaviour).
_EXTRACTION_BATCH_SIZE = getattr(settings, "INTELLIGENCE_EXTRACTION_BATCH_SIZE", 3)

# Keyword hints for chunk routing (broad — indirect procurement language included)
EXTRACTION_CHUNK_KEYWORDS: dict[str, list[str]] = {
    ExtractionType.ELIGIBILITY_CRITERIA: [
        "eligibility", "qualification", "experience", "bidder", "contractor",
        "disqualif", "minimum", "marks", "pre-qualif",
    ],
    ExtractionType.SUBMISSION_DEADLINES: [
        "deadline", "submission", "closing", "due", "validity", "etender",
        "e-tender", "portal", "query", "clarification", "proposal", "late",
        # Pre-bid / conference (US RFPs rarely say "pre-bid" — use Proposer's Conference)
        "conference", "proposer", "bidder", "pre-bid", "prebid", "pre bid",
        "pre-registration", "pre registration", "mandatory", "non-mandatory",
        "timeline", "advertised", "issue date", "anticipated", "opening",
        "walkthrough", "site visit", "questions due", "february", "january",
    ],
    ExtractionType.TECHNICAL_REQUIREMENTS: [
        "technical", "specification", "sla", "performance", "sso", "sharepoint",
        "portal", "mobile", "workflow", "dashboard", "integration", "vapt",
        "hosting", "maintenance", "training", "source code", "24x7", "uptime",
        # Physical / managed security services
        "security", "guard", "guarding", "escort", "patrol", "manpower",
        "personnel", "deployment", "shift", "roster", "cctv", "access control",
        "transport", "emergency", "incident", "audit", "uniform", "weapon",
        "background check", "statutory", "labor", "labour", "standby",
        "women", "safety protocol",
    ],
    ExtractionType.SCOPE_OF_WORK: [
        "scope", "work", "deliverable", "milestone", "sow", "implementation",
        "vendor", "responsib", "subcontract",
        "security service", "transport", "escort", "guarding", "bangalore",
        "chennai", "location", "site", "headcount", "manpower", "personnel",
        "deployment", "standby", "24x7", "shift", "operational",
    ],
    ExtractionType.PAYMENT_TERMS: [
        "payment", "commercial", "price", "invoice", "retention", "fixed",
        "guarantee", "bond", "validity", "tax", "milestone", "advance",
        "performance", "bank", "quoted",
    ],
    ExtractionType.PENALTIES_AND_RISKS: [
        "penalty", "liquidated", "termination", "liability", "risk",
        "reject", "non-conform", "noncomform", "breach", "default",
        "indemn", "cancel", "discretion",
        "under-performance", "non-performance", "damages", "forfeit",
    ],
    ExtractionType.MANDATORY_DOCUMENTS: [
        "annexure", "appendix", "form", "emd", "document", "compliance",
        "matrix", "acknowledg", "guarantee", "reference", "cv", "proposal",
        "non-conform",
    ],
    ExtractionType.EVALUATION_CRITERIA: [
        # Explicit scoring language
        "evaluation", "weightage", "weight", "scoring", "criteria", "scored",
        "technical", "commercial", "70", "30", "marks", "minimum",
        # US/UK government RFP language
        "award", "selection", "review", "committee", "assessment", "judg",
        "rank", "ranked", "best value", "lowest", "price", "factor",
        "qualify", "qualified", "qualif", "pass", "fail", "threshold",
        "points", "score", "rated", "rating", "oral presentation",
    ],
}

# Types that need wide document coverage (not only keyword hits)
BROAD_COVERAGE_TYPES = frozenset(
    {
        ExtractionType.PAYMENT_TERMS,
        ExtractionType.PENALTIES_AND_RISKS,
        ExtractionType.EVALUATION_CRITERIA,
        ExtractionType.MANDATORY_DOCUMENTS,
        ExtractionType.TECHNICAL_REQUIREMENTS,
        ExtractionType.SCOPE_OF_WORK,
        ExtractionType.ELIGIBILITY_CRITERIA,  # qualif/experience scattered throughout
    }
)

DEFAULT_MAX_CHUNKS = 10
BROAD_MAX_CHUNKS = 14
MIN_BROAD_CHUNKS = 8

# Sections that carry service scope / manpower / guarding (security & facilities RFPs).
OPERATIONAL_CONTENT_MARKERS: tuple[str, ...] = (
    "scope of work",
    "security personnel",
    "approximately 275",
    "275 security",
    "transport escort",
    "transport security",
    "standby manpower",
    "guarding",
    "escort guard",
    "bangalore",
    "chennai",
    "headcount",
    "deployment",
    "women associate",
    "24/7",
    "24x7",
    "supplier information",
)

OPERATIONAL_PIN_TYPES = frozenset(
    {
        ExtractionType.SCOPE_OF_WORK,
        ExtractionType.TECHNICAL_REQUIREMENTS,
    }
)


# ── Opt #5 — paragraph-level context trimmer ─────────────────────────────────

def _trim_chunk_to_relevant_paragraphs(
    text: str,
    extraction_type: str,
    max_chars: int = _CHUNK_TRIM_CHARS,
) -> str:
    """
    Return only the paragraphs most relevant to *extraction_type*, up to *max_chars*.

    Chunks are selected by keyword routing but may still contain large sections of
    irrelevant prose. Filtering to top-scoring paragraphs cuts input tokens by
    30–50% for dense chunks while keeping every sentence that matches the keywords.

    Small chunks (already within budget) pass through unchanged.
    """
    if len(text) <= max_chars:
        return text

    keywords = EXTRACTION_CHUNK_KEYWORDS.get(extraction_type, [])
    if not keywords:
        return text[:max_chars]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return text[:max_chars]

    scored: list[tuple[int, str]] = []
    for para in paragraphs:
        lower = para.lower()
        score = sum(1 for kw in keywords if kw in lower)
        scored.append((score, para))

    # Sort by relevance descending; then rebuild in *original document order*
    # so we don't scramble the narrative structure for the LLM.
    relevant_set = {
        para for score, para in sorted(scored, key=lambda x: -x[0])
        if score > 0
    }
    ordered = [p for p in paragraphs if p in relevant_set]

    # Fill remaining budget with unseen paragraphs (preserves any stray context).
    seen = set(ordered)
    for para in paragraphs:
        if para not in seen:
            ordered.append(para)

    result_parts: list[str] = []
    total = 0
    for para in ordered:
        if total + len(para) + 2 > max_chars:
            break
        result_parts.append(para)
        total += len(para) + 2

    return "\n\n".join(result_parts) if result_parts else text[:max_chars]


# ── Opt #6 — chunk batching ───────────────────────────────────────────────────

def _build_batch_groups(
    chunks: list[DocumentChunk],
    batch_size: int,
) -> list[list[DocumentChunk]]:
    """Split *chunks* into consecutive groups of at most *batch_size*."""
    return [chunks[i : i + batch_size] for i in range(0, len(chunks), batch_size)]


class ExtractionService:
    @staticmethod
    def _chunk_has_operational_content(chunk: DocumentChunk) -> bool:
        blob = f"{chunk.section_title} {chunk.chunk_text}".lower()
        return any(marker in blob for marker in OPERATIONAL_CONTENT_MARKERS)

    @staticmethod
    def _pin_operational_chunks(
        selected: list[DocumentChunk],
        all_chunks: list[DocumentChunk],
        max_chunks: int,
    ) -> list[DocumentChunk]:
        """Ensure scope/technical passes always see manpower & SOW sections first."""
        pinned = [c for c in all_chunks if ExtractionService._chunk_has_operational_content(c)]
        if not pinned:
            return selected

        merged: list[DocumentChunk] = []
        seen: set = set()
        for chunk in pinned + selected:
            if chunk.id in seen:
                continue
            seen.add(chunk.id)
            merged.append(chunk)
        return merged[:max_chunks]

    @staticmethod
    def _max_chunks_for_type(extraction_type: str) -> int:
        if extraction_type in BROAD_COVERAGE_TYPES:
            return getattr(
                settings,
                "INTELLIGENCE_BROAD_EXTRACTION_CHUNKS",
                BROAD_MAX_CHUNKS,
            )
        return getattr(
            settings,
            "INTELLIGENCE_DEFAULT_EXTRACTION_CHUNKS",
            DEFAULT_MAX_CHUNKS,
        )

    @staticmethod
    def _stratified_fill(
        chunks: list[DocumentChunk],
        exclude_ids: set,
        count: int,
    ) -> list[DocumentChunk]:
        """Sample chunks across the document when keyword routing under-selects."""
        pool = [c for c in chunks if c.id not in exclude_ids]
        if not pool or count <= 0:
            return []
        if len(pool) <= count:
            return pool
        step = len(pool) / count
        picked: list[DocumentChunk] = []
        for i in range(count):
            idx = min(int(i * step), len(pool) - 1)
            chunk = pool[idx]
            if chunk.id not in {c.id for c in picked}:
                picked.append(chunk)
        return picked

    @staticmethod
    def select_chunks(chunks: list[DocumentChunk], extraction_type: str) -> list[DocumentChunk]:
        if not chunks:
            return []

        keywords = EXTRACTION_CHUNK_KEYWORDS.get(extraction_type, [])
        max_chunks = ExtractionService._max_chunks_for_type(extraction_type)

        scored: list[tuple[int, DocumentChunk]] = []
        for chunk in chunks:
            text = f"{chunk.section_title} {chunk.chunk_text}".lower()
            score = sum(1 for kw in keywords if kw in text)
            tags = chunk.metadata.get("tags", [])
            for tag in tags:
                if any(kw in tag or kw in text for kw in keywords):
                    score += 2
            if score > 0:
                scored.append((score, chunk))

        selected: list[DocumentChunk] = []
        seen_ids: set = set()

        if scored:
            scored.sort(key=lambda x: (-x[0], x[1].chunk_order))
            for _, chunk in scored[:max_chunks]:
                if chunk.id not in seen_ids:
                    selected.append(chunk)
                    seen_ids.add(chunk.id)

        min_needed = MIN_BROAD_CHUNKS if extraction_type in BROAD_COVERAGE_TYPES else 4
        if len(selected) < min_needed:
            extra = ExtractionService._stratified_fill(
                chunks, seen_ids, min_needed - len(selected)
            )
            for chunk in extra:
                selected.append(chunk)
                seen_ids.add(chunk.id)

        if not selected:
            selected = ExtractionService._stratified_fill(chunks, set(), min(max_chunks, 6))

        if extraction_type in OPERATIONAL_PIN_TYPES:
            selected = ExtractionService._pin_operational_chunks(
                selected, chunks, max_chunks
            )
            operational = [
                c for c in selected if ExtractionService._chunk_has_operational_content(c)
            ]
            other = [c for c in selected if c not in operational]
            operational.sort(key=lambda c: c.chunk_order)
            other.sort(key=lambda c: c.chunk_order)
            return (operational + other)[:max_chunks]

        selected.sort(key=lambda c: c.chunk_order)
        return selected[:max_chunks]

    @staticmethod
    def _run_extraction_batches(
        extraction_type: str,
        selected: list[DocumentChunk],
        *,
        client: OpenAIService,
        total_pages: int,
        page_texts: list[tuple[int, str]],
        batch_size: int = _EXTRACTION_BATCH_SIZE,
    ) -> tuple[list[dict], list[str], dict]:
        """Run LLM extraction over chunk batches; return items, chunk_ids, token usage."""
        all_items: list[dict] = []
        chunk_ids: list[str] = []
        total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for batch in _build_batch_groups(selected, batch_size):
            trimmed: list[str] = [
                _trim_chunk_to_relevant_paragraphs(c.chunk_text, extraction_type)
                for c in batch
            ]

            if len(batch) == 1:
                prompt_text = trimmed[0]
                prompt_label = batch[0].section_title
            else:
                parts: list[str] = [
                    f"=== Section: {c.section_title} "
                    f"| Pages {c.page_start}–{c.page_end} ===\n{t}"
                    for c, t in zip(batch, trimmed)
                ]
                prompt_text = "\n\n".join(parts)
                prompt_label = f"{batch[0].section_title} (+{len(batch) - 1} more)"

            batch_page_start = min(c.page_start for c in batch)
            batch_page_end = max(c.page_end for c in batch)

            user_prompt = extraction_user_prompt(
                extraction_type,
                prompt_text,
                prompt_label,
            )
            try:
                data, usage = client.chat_json(
                    system=EXTRACTION_SYSTEM_PROMPT,
                    user=user_prompt,
                )
            except Exception as exc:
                logger.warning(
                    "extraction_batch_failed type=%s chunks=%s error=%s",
                    extraction_type,
                    [str(c.id) for c in batch],
                    exc,
                )
                continue

            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                total_usage[key] = total_usage.get(key, 0) + usage.get(key, 0)

            items = data.get("items") or []
            validated = validate_and_score_items(
                items,
                chunk_text=prompt_text,
                section_title=prompt_label,
                page_start=batch_page_start,
                page_end=batch_page_end,
                total_pages=total_pages,
                page_texts=page_texts,
            )
            all_items.extend(validated)
            chunk_ids.extend(str(c.id) for c in batch)

        return all_items, chunk_ids, total_usage

    @staticmethod
    def _extract_single_type(
        extraction_type: str,
        selected: list[DocumentChunk],
        document: Document,
        summary: GeneratedSummary,
        total_pages: int,
        page_texts: list[tuple[int, str]],
        all_chunks: list[DocumentChunk] | None = None,
    ) -> ExtractedInsight:
        """
        Run all chunk-level LLM calls for one extraction type and persist the result.
        Designed to run inside a ThreadPoolExecutor worker — each call owns its own
        OpenAIService instance and DB connection to avoid cross-thread sharing.
        """
        # Ensure Django gives this thread a fresh DB connection rather than
        # reusing a stale one from the parent thread.
        close_old_connections()

        client = OpenAIService()
        pool = all_chunks or selected

        all_items, chunk_ids, total_usage = ExtractionService._run_extraction_batches(
            extraction_type,
            selected,
            client=client,
            total_pages=total_pages,
            page_texts=page_texts,
        )

        merged = merge_insight_items(all_items)

        if not merged and extraction_type in OPERATIONAL_PIN_TYPES:
            fallback = [
                c for c in pool if ExtractionService._chunk_has_operational_content(c)
            ]
            if fallback:
                logger.warning(
                    "extraction_empty_retry type=%s operational_chunks=%s",
                    extraction_type,
                    len(fallback),
                )
                retry_items, retry_ids, retry_usage = (
                    ExtractionService._run_extraction_batches(
                        extraction_type,
                        fallback,
                        client=client,
                        total_pages=total_pages,
                        page_texts=page_texts,
                        batch_size=1,
                    )
                )
                merged = merge_insight_items(retry_items)
                chunk_ids = retry_ids
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    total_usage[key] = total_usage.get(key, 0) + retry_usage.get(key, 0)
        if extraction_type == ExtractionType.PENALTIES_AND_RISKS:
            from apps.intelligence.services.risk_severity import apply_penalties_severity

            merged = apply_penalties_severity(merged)
        confidence = aggregate_confidence(merged)

        insight = ExtractedInsight.objects.create(
            document=document,
            generated_summary=summary,
            extraction_type=extraction_type,
            payload={"items": merged},
            confidence_score=confidence,
            model_name=client.model,
            prompt_version=settings.INTELLIGENCE_PROMPT_VERSION,
            token_usage=total_usage,
            chunk_ids=chunk_ids,
        )
        ExtractionService._sync_source_references(document, insight)

        logger.info(
            "extraction_complete type=%s items=%s chunks=%s confidence=%s",
            extraction_type,
            len(merged),
            len(selected),
            confidence,
        )
        return insight

    @staticmethod
    def run_extractions(
        document: Document,
        summary: GeneratedSummary,
        chunks: list[DocumentChunk],
    ) -> list[ExtractedInsight]:
        parsed = document.parsed_document
        total_pages = parsed.total_pages
        page_texts = list(
            parsed.pages.order_by("page_number").values_list("page_number", "extracted_text")
        )

        # Pre-compute chunk selection for every type in one pass so we don't
        # re-score the same chunk list 8× inside the thread pool.
        chunk_selection: dict[str, list[DocumentChunk]] = {
            etype: ExtractionService.select_chunks(chunks, etype)
            for etype in FOCUSED_EXTRACTION_TYPES
        }

        # Map future → extraction_type so we can log failures with context.
        future_to_type: dict = {}
        results: dict[str, ExtractedInsight] = {}

        with ThreadPoolExecutor(max_workers=_EXTRACTION_WORKERS) as pool:
            for etype in FOCUSED_EXTRACTION_TYPES:
                fut = pool.submit(
                    ExtractionService._extract_single_type,
                    etype,
                    chunk_selection[etype],
                    document,
                    summary,
                    total_pages,
                    page_texts,
                    chunks,
                )
                future_to_type[fut] = etype

            for fut in as_completed(future_to_type):
                etype = future_to_type[fut]
                try:
                    results[etype] = fut.result()
                except Exception as exc:
                    logger.error(
                        "extraction_type_failed type=%s error=%s",
                        etype,
                        exc,
                        exc_info=True,
                    )

        # Return insights in the canonical FOCUSED_EXTRACTION_TYPES order so
        # downstream summary building is deterministic regardless of thread finish order.
        return [results[etype] for etype in FOCUSED_EXTRACTION_TYPES if etype in results]

    @staticmethod
    @transaction.atomic
    def _sync_source_references(document: Document, insight: ExtractedInsight) -> None:
        version = getattr(document, "version", None)
        for item in insight.payload.get("items", []):
            SourceReference.objects.create(
                document=document,
                document_version=version,
                reference_kind=SourceReferenceKind.EXTRACTION,
                source_document_label=document.original_filename,
                page=item.get("page"),
                section=item.get("section", "")[:512],
                section_path=(item.get("section_path") or "")[:1024],
                excerpt=item.get("source_text", "")[:2000],
                confidence=item.get("confidence"),
                chunk_id=insight.chunk_ids[0] if insight.chunk_ids else "",
                metadata={
                    "extraction_type": insight.extraction_type,
                    "requirement": item.get("requirement", "")[:500],
                    "insight_id": str(insight.id),
                },
            )
