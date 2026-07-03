"""Retrieve grounded chunks for a document-scoped query."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from apps.chat.services.chroma_service import ChromaVectorStore
from apps.intelligence.models import DocumentChunk
from apps.intelligence.services.openai_service import OpenAIService


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    page_start: int
    page_end: int
    section_title: str
    score: float
    chunk_order: int


# Extra embedding queries for procurement wording mismatches (e.g. "pre-bid" vs conference).
_QUERY_EXPANSIONS: dict[str, list[str]] = {
    "pre-bid": [
        "proposer conference pre-proposal conference timeline schedule",
        "issue date advertisement schedule conference due date time",
    ],
    "prebid": [
        "proposer conference pre-proposal conference timeline schedule",
        "issue date advertisement schedule conference due date time",
    ],
    "pre bid": [
        "proposer conference pre-proposal conference timeline schedule",
        "issue date advertisement schedule conference due date time",
    ],
}


_TIMELINE_QUERY_MARKERS = (
    "pre-bid",
    "prebid",
    "pre bid",
    "deadline",
    "due date",
    "conference",
    "timeline",
    "submission date",
)


class RetrievalService:
    @staticmethod
    def _timeline_keyword_chunks(document_id: str, query: str) -> list[RetrievedChunk]:
        """Pull cover-page schedule chunks when vector search misses the timeline table."""
        lowered = query.lower()
        if not any(marker in lowered for marker in _TIMELINE_QUERY_MARKERS):
            return []

        supplemental: list[RetrievedChunk] = []
        for chunk in DocumentChunk.objects.filter(document_id=document_id).order_by(
            "chunk_order"
        ):
            text = chunk.chunk_text
            lower_text = text.lower()
            is_cover_timeline = chunk.page_start == 1 and (
                "issue date" in lower_text or "proposer" in lower_text
            )
            if not is_cover_timeline:
                continue
            supplemental.append(
                RetrievedChunk(
                    chunk_id=str(chunk.id),
                    text=text,
                    page_start=int(chunk.page_start),
                    page_end=int(chunk.page_end),
                    section_title=str(chunk.section_title or ""),
                    score=0.5,
                    chunk_order=int(chunk.chunk_order),
                )
            )
            break
        return supplemental

    @staticmethod
    def _expanded_queries(query: str) -> list[str]:
        q = query.strip()
        if not q:
            return []
        lowered = q.lower()
        extra: list[str] = []
        for key, phrases in _QUERY_EXPANSIONS.items():
            if key in lowered:
                extra.extend(phrases)
                break
        return [q, *extra]

    @staticmethod
    def _parse_hits(
        raw: dict,
        *,
        min_score: float,
    ) -> list[RetrievedChunk]:
        ids = (raw.get("ids") or [[]])[0]
        documents = (raw.get("documents") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        results: list[RetrievedChunk] = []
        for i, chunk_id in enumerate(ids):
            meta = metadatas[i] if i < len(metadatas) else {}
            distance = distances[i] if i < len(distances) else 1.0
            score = max(0.0, 1.0 - float(distance))
            if score < min_score:
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=documents[i] if i < len(documents) else "",
                    page_start=int(meta.get("page_start", 1)),
                    page_end=int(meta.get("page_end", 1)),
                    section_title=str(meta.get("section_title", "")),
                    score=round(score, 4),
                    chunk_order=int(meta.get("chunk_order", 0)),
                )
            )
        return results

    @staticmethod
    def retrieve(document_id: str, query: str) -> list[RetrievedChunk]:
        openai = OpenAIService()
        queries = RetrievalService._expanded_queries(query)
        query_embeddings, _ = openai.embed_texts(queries)
        if not query_embeddings:
            return []

        doc_id = str(document_id)
        top_k = settings.CHAT_RETRIEVAL_TOP_K
        min_score = settings.CHAT_MIN_RETRIEVAL_SCORE
        by_id: dict[str, RetrievedChunk] = {}

        for embedding in query_embeddings:
            raw = ChromaVectorStore.query(
                document_id=doc_id,
                query_embedding=embedding,
                top_k=top_k,
            )
            for chunk in RetrievalService._parse_hits(raw, min_score=min_score):
                prev = by_id.get(chunk.chunk_id)
                if prev is None or chunk.score > prev.score:
                    by_id[chunk.chunk_id] = chunk

        for chunk in RetrievalService._timeline_keyword_chunks(doc_id, query):
            prev = by_id.get(chunk.chunk_id)
            if prev is None or chunk.score >= prev.score:
                by_id[chunk.chunk_id] = chunk

        merged = sorted(by_id.values(), key=lambda c: (-c.score, c.chunk_order))
        if merged:
            return merged[:top_k]

        # Chroma returned hits but all were below threshold — keep best matches rather
        # than sending an empty context to the LLM.
        for embedding in query_embeddings:
            raw = ChromaVectorStore.query(
                document_id=doc_id,
                query_embedding=embedding,
                top_k=top_k,
            )
            for chunk in RetrievalService._parse_hits(raw, min_score=0.0):
                prev = by_id.get(chunk.chunk_id)
                if prev is None or chunk.score > prev.score:
                    by_id[chunk.chunk_id] = chunk

        for chunk in RetrievalService._timeline_keyword_chunks(doc_id, query):
            prev = by_id.get(chunk.chunk_id)
            if prev is None or chunk.score >= prev.score:
                by_id[chunk.chunk_id] = chunk

        fallback = sorted(by_id.values(), key=lambda c: (-c.score, c.chunk_order))
        return fallback[: max(1, min(3, top_k))]

    @staticmethod
    def retrieve_batch(
        document_id: str,
        queries: list[str],
        *,
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Embed all queries in one API call, merge hits, return top chunks by score."""
        cleaned = [q.strip() for q in queries if q and q.strip()]
        if not cleaned:
            return []

        openai = OpenAIService()
        expanded: list[str] = []
        for query in cleaned:
            expanded.extend(RetrievalService._expanded_queries(query))
        if not expanded:
            return []

        query_embeddings, _ = openai.embed_texts(expanded)
        if not query_embeddings:
            return []

        doc_id = str(document_id)
        limit = top_k if top_k is not None else settings.CHAT_RETRIEVAL_TOP_K
        min_score = settings.CHAT_MIN_RETRIEVAL_SCORE
        by_id: dict[str, RetrievedChunk] = {}

        for embedding in query_embeddings:
            raw = ChromaVectorStore.query(
                document_id=doc_id,
                query_embedding=embedding,
                top_k=limit,
            )
            for chunk in RetrievalService._parse_hits(raw, min_score=min_score):
                prev = by_id.get(chunk.chunk_id)
                if prev is None or chunk.score > prev.score:
                    by_id[chunk.chunk_id] = chunk

        for query in cleaned:
            for chunk in RetrievalService._timeline_keyword_chunks(doc_id, query):
                prev = by_id.get(chunk.chunk_id)
                if prev is None or chunk.score >= prev.score:
                    by_id[chunk.chunk_id] = chunk

        merged = sorted(by_id.values(), key=lambda c: (-c.score, c.chunk_order))
        if merged:
            return merged[:limit]

        for embedding in query_embeddings:
            raw = ChromaVectorStore.query(
                document_id=doc_id,
                query_embedding=embedding,
                top_k=limit,
            )
            for chunk in RetrievalService._parse_hits(raw, min_score=0.0):
                prev = by_id.get(chunk.chunk_id)
                if prev is None or chunk.score > prev.score:
                    by_id[chunk.chunk_id] = chunk

        for query in cleaned:
            for chunk in RetrievalService._timeline_keyword_chunks(doc_id, query):
                prev = by_id.get(chunk.chunk_id)
                if prev is None or chunk.score >= prev.score:
                    by_id[chunk.chunk_id] = chunk

        fallback = sorted(by_id.values(), key=lambda c: (-c.score, c.chunk_order))
        return fallback[: max(1, min(3, limit))]
