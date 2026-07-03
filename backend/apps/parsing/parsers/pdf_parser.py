import logging
from pathlib import Path

import fitz
import pdfplumber
from django.conf import settings
from PIL import Image

from apps.parsing.choices import ExtractionMethod
from apps.parsing.parsers.base import DocumentParseResult, ParsedPageResult, ParsedTableResult
from apps.parsing.services.quality import aggregate_quality, is_poor_extraction, score_page_text
from apps.parsing.services.section_detection import (
    build_structured_text,
    detect_sections_from_pages,
)

logger = logging.getLogger(__name__)


def _ocr_page_image(pix: fitz.Pixmap) -> str:
    import pytesseract

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return pytesseract.image_to_string(img)


def _extract_page_native(page: fitz.Page) -> str:
    return page.get_text("text") or ""


def _extract_tables_pdfplumber(file_path: Path) -> list[ParsedTableResult]:
    tables: list[ParsedTableResult] = []
    try:
        with pdfplumber.open(str(file_path)) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                for table in page.extract_tables() or []:
                    if not table:
                        continue
                    headers = [str(c or "").strip() for c in table[0]]
                    rows = [
                        [str(c or "").strip() for c in row]
                        for row in table[1:]
                        if any(str(c or "").strip() for c in row)
                    ]
                    tables.append(
                        ParsedTableResult(
                            page_number=page_num,
                            headers=headers,
                            rows=rows,
                            raw=table,
                        )
                    )
    except Exception as exc:
        logger.warning("pdfplumber_tables_failed path=%s error=%s", file_path, exc)
    return tables


def parse_pdf(file_path: Path) -> DocumentParseResult:
    pages: list[ParsedPageResult] = []
    ocr_pages_count = 0
    empty_pages = 0

    doc = fitz.open(str(file_path))
    try:
        for index in range(len(doc)):
            page_number = index + 1
            page = doc.load_page(index)
            text = _extract_page_native(page)
            method = ExtractionMethod.NATIVE_PDF
            ocr_used = False
            quality = score_page_text(text)

            if settings.PARSING_OCR_ENABLED and is_poor_extraction(quality):
                try:
                    pix = page.get_pixmap(dpi=200)
                    ocr_text = _ocr_page_image(pix)
                    ocr_quality = score_page_text(ocr_text)
                    if ocr_quality > quality:
                        text = ocr_text
                        method = ExtractionMethod.OCR
                        ocr_used = True
                        quality = ocr_quality
                        ocr_pages_count += 1
                except Exception as exc:
                    logger.warning(
                        "ocr_fallback_failed page=%s error=%s", page_number, exc
                    )

            is_empty = not text.strip()
            if is_empty:
                empty_pages += 1

            pages.append(
                ParsedPageResult(
                    page_number=page_number,
                    extracted_text=text,
                    extraction_method=method,
                    ocr_used=ocr_used,
                    quality_score=quality,
                    is_empty=is_empty,
                )
            )
    finally:
        doc.close()

    tables = _extract_tables_pdfplumber(file_path)
    sections = detect_sections_from_pages(pages)
    raw_text = "\n\n".join(
        f"--- Page {p.page_number} ---\n{p.extracted_text}" for p in pages if p.extracted_text
    )
    structured_text = build_structured_text(sections)
    page_scores = [p.quality_score for p in pages if not p.is_empty] or [0.0]
    quality_score = aggregate_quality(page_scores)

    metadata = {
        "file_type": "pdf",
        "parser": "pymupdf",
        "table_parser": "pdfplumber",
        "total_pages": len(pages),
        "empty_pages": empty_pages,
        "ocr_pages": ocr_pages_count,
        "tables": [
            {
                "page": t.page_number,
                "headers": t.headers,
                "rows": t.rows,
            }
            for t in tables
        ],
        "page_quality": [
            {
                "page": p.page_number,
                "quality_score": p.quality_score,
                "extraction_method": p.extraction_method,
                "ocr_used": p.ocr_used,
            }
            for p in pages
        ],
    }

    return DocumentParseResult(
        pages=pages,
        sections=sections,
        tables=tables,
        raw_text=raw_text,
        structured_text=structured_text,
        parsing_metadata=metadata,
        parsing_quality_score=quality_score,
        file_type="pdf",
    )
