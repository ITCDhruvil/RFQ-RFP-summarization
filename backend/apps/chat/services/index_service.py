"""Embed document chunks and persist in Chroma."""

from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone

from apps.chat.models import DocumentVectorIndex
from apps.chat.services.chroma_service import ChromaVectorStore
from apps.documents.models import Document
from apps.intelligence.models import DocumentChunk
from apps.intelligence.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class VectorIndexService:
    @staticmethod
    def is_indexed(document_id) -> bool:
        record = DocumentVectorIndex.objects.filter(document_id=document_id).first()
        if not record:
            return False
        return VectorIndexService.chroma_has_vectors(str(document_id))

    @staticmethod
    def chroma_has_vectors(document_id: str) -> bool:
        """True when Chroma still holds at least one vector for this document."""
        from apps.chat.services.chroma_service import get_collection

        try:
            result = get_collection().get(
                where={"document_id": str(document_id)},
                limit=1,
                include=[],
            )
        except Exception as exc:
            logger.warning(
                "chroma_has_vectors_check_failed document_id=%s error=%s",
                document_id,
                exc,
            )
            return False
        return bool(result.get("ids"))

    @staticmethod
    def index_document(document: Document, *, force: bool = False) -> DocumentVectorIndex:
        chunks = list(
            DocumentChunk.objects.filter(document=document).order_by("chunk_order")
        )
        if not chunks:
            from apps.core.exceptions import ValidationServiceError

            raise ValidationServiceError(
                "No chunks found. Generate summary first to create chunks.",
                code="chunks_required",
            )

        existing = DocumentVectorIndex.objects.filter(document=document).first()

        if (
            not force
            and existing
            and existing.chunk_count == len(chunks)
            and VectorIndexService.chroma_has_vectors(str(document.id))
        ):
            return existing

        if existing and not VectorIndexService.chroma_has_vectors(str(document.id)):
            logger.warning(
                "stale_vector_index_reindex document_id=%s db_chunks=%s",
                document.id,
                len(chunks),
            )

        # Retrieve previously indexed chunk IDs so we can do a targeted delete
        # instead of a slow full-collection metadata scan.
        old_chunk_ids: list[str] | None = (
            existing.indexed_chunk_ids if existing else None
        )

        openai = OpenAIService()
        texts = [c.chunk_text for c in chunks]
        new_chunk_ids = [str(c.id) for c in chunks]
        embeddings, _usage = openai.embed_texts(texts)

        doc_id = str(document.id)
        metadatas = [
            {
                "document_id": doc_id,
                "chunk_id": str(c.id),
                "page_start": int(c.page_start),
                "page_end": int(c.page_end),
                "section_title": (c.section_title or "")[:512],
                "chunk_order": int(c.chunk_order),
            }
            for c in chunks
        ]

        ChromaVectorStore.upsert_chunks(
            document_id=doc_id,
            chunk_ids=new_chunk_ids,
            old_chunk_ids=old_chunk_ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        record, _ = DocumentVectorIndex.objects.update_or_create(
            document=document,
            defaults={
                "chunk_count": len(chunks),
                "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
                "collection_name": settings.CHROMA_COLLECTION_NAME,
                "indexed_at": timezone.now(),
                "indexed_chunk_ids": new_chunk_ids,
            },
        )
        return record

    @staticmethod
    def ensure_indexed(document: Document) -> DocumentVectorIndex:
        return VectorIndexService.index_document(document, force=False)
