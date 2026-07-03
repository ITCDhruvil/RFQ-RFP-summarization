# Phase 2 — Document Parsing

## Goal

Convert uploaded RFQ/RFP PDF/DOCX files into **structured, page-level text** with sections and tables — ready for grounded summarization in Phase 3 (no OpenAI in this phase).

## Pipeline

```
queued
  → intake_processing → intake_completed
  → parsing_processing → parsing_completed
  → completed
```

Implemented in `processing.tasks.process_document_task` using existing `ProcessingJob` stage logs.

## Libraries

| Format | Primary | Fallback |
|--------|---------|----------|
| PDF | PyMuPDF (`fitz`) native text | pytesseract OCR per page when quality &lt; threshold |
| PDF tables | pdfplumber | — |
| DOCX | python-docx | — |

OCR runs **only** when native extraction quality is poor (short/garbled text).

## Models (`apps.parsing`)

- **ParsedDocument** — aggregate parse result, quality score, metadata (tables, page quality)
- **DocumentPage** — per-page text, method, OCR flag, quality
- **DocumentSection** — heuristic sections for summarization

Synced to **DocumentExtractedContent** (`raw_text`, `page_map`, `section_hierarchy`) for Phase 3.

## Section detection

Heuristics only (no ML):

- Numbered headings (`1.`, `2.1`, …)
- Known procurement titles (Eligibility Criteria, Scope of Work, …)
- Annexure / Appendix lines
- DOCX heading styles

## APIs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/documents/{id}/parsed/` | Parsed summary + previews |
| GET | `/api/v1/documents/{id}/parsed/status/` | Parsing + job status |
| GET | `/api/v1/documents/{id}/parsed/pages/` | All pages |
| GET | `/api/v1/documents/{id}/parsed/pages/{n}/` | Single page |
| GET | `/api/v1/documents/{id}/parsed/sections/` | Detected sections |

## Frontend

`/documents/[id]/parsed` — quality score, OCR count, section list, page-by-page viewer.

## Setup (OCR)

Install **Tesseract** on the host:

- Windows: [UB-Mannheim tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
- macOS: `brew install tesseract`
- Linux: `apt install tesseract-ocr`

Set `PARSING_OCR_ENABLED=False` in `.env` to disable OCR fallback.

## Install Python deps

```bash
pip install -r requirements.txt
python manage.py migrate
```
