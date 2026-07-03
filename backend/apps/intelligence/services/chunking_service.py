import logging
import re

from django.conf import settings
from django.db import transaction

from apps.documents.models import Document
from apps.intelligence.models import DocumentChunk
from apps.intelligence.services.citation_service import extract_section_prefix
from apps.parsing.choices import ParsingStatus
from apps.parsing.models import DocumentSection, ParsedDocument

logger = logging.getLogger(__name__)

# Section keywords → extraction relevance (for metadata)
SECTION_TAGS = {
    "eligibility": ["eligibility", "qualification", "bidder", "pre-qualif"],
    "deadline": ["deadline", "submission", "closing", "due date", "validity", "etender"],
    "technical": [
        "technical", "specification", "sla", "architecture", "integration",
        "security", "guard", "escort", "manpower", "deployment", "training",
    ],
    "scope": [
        "scope", "work", "deliverable", "statement of work", "implementation",
        "security service", "transport", "guarding", "personnel", "operational",
    ],
    "payment": ["payment", "commercial", "price", "invoice", "guarantee", "bond"],
    "risk": ["penalty", "liquidated", "termination", "liability", "reject", "compliance"],
    "documents": ["annexure", "appendix", "form", "mandatory", "compliance matrix"],
    "evaluation": ["evaluation", "weightage", "scoring", "criteria", "marks"],
    "support": ["support", "maintenance", "warranty", "training", "handover"],
    "general": ["general", "condition", "instruction", "provision", "governing"],
}


def _split_paragraphs(text: str, max_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return [text] if text.strip() else []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) + 2 > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_len = len(para)
        else:
            current.append(para)
            current_len += len(para) + 2

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def _table_context_for_pages(parsed: ParsedDocument, page_start: int, page_end: int) -> str:
    tables = parsed.parsing_metadata.get("tables", [])
    lines: list[str] = []
    for table in tables:
        page = table.get("page", 0)
        if page_start <= page <= page_end:
            headers = table.get("headers", [])
            rows = table.get("rows", [])[:15]
            lines.append(f"[Table on page {page}]")
            if headers:
                lines.append(" | ".join(headers))
            for row in rows:
                lines.append(" | ".join(row))
    return "\n".join(lines)


def _infer_tags(title: str) -> list[str]:
    lower = title.lower()
    tags = []
    for tag, keywords in SECTION_TAGS.items():
        if any(k in lower for k in keywords):
            tags.append(tag)
    return tags


class ChunkingService:
    @staticmethod
    @transaction.atomic
    def build_chunks(document: Document) -> list[DocumentChunk]:
        parsed = ParsedDocument.objects.get(
            document=document,
            parsing_status=ParsingStatus.COMPLETED,
        )
        sections = list(
            DocumentSection.objects.filter(parsed_document=parsed).order_by("section_order")
        )

        DocumentChunk.objects.filter(document=document).delete()

        max_chars = settings.INTELLIGENCE_MAX_CHUNK_CHARS
        chunk_order = 0
        created: list[DocumentChunk] = []

        for section in sections:
            base_text = section.content.strip()
            if not base_text:
                continue

            table_ctx = _table_context_for_pages(
                parsed, section.page_start, section.page_end
            )
            if table_ctx:
                base_text = f"{base_text}\n\n--- Tables ---\n{table_ctx}"

            parts = _split_paragraphs(base_text, max_chars)
            if not parts:
                parts = [base_text]

            for part_index, part_text in enumerate(parts):
                chunk_order += 1
                chunk = DocumentChunk.objects.create(
                    document=document,
                    parsed_document=parsed,
                    section_title=section.title,
                    page_start=section.page_start,
                    page_end=section.page_end,
                    chunk_order=chunk_order,
                    chunk_text=part_text,
                    char_count=len(part_text),
                    metadata={
                        "section_order": section.section_order,
                        "part_index": part_index,
                        "tags": _infer_tags(section.title),
                        "section_prefix": extract_section_prefix(section.title),
                    },
                )
                created.append(chunk)

        if not created and parsed.structured_text:
            chunk_order += 1
            chunk = DocumentChunk.objects.create(
                document=document,
                parsed_document=parsed,
                section_title="Full Document",
                page_start=1,
                page_end=parsed.total_pages or 1,
                chunk_order=chunk_order,
                chunk_text=parsed.structured_text[: max_chars * 3],
                char_count=len(parsed.structured_text),
                metadata={"fallback": True},
            )
            created.append(chunk)

        logger.info(
            "chunks_created document_id=%s count=%s",
            document.id,
            len(created),
        )
        return created
