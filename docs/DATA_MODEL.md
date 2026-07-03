# Data Model — Versioning, Content, Pipeline, Traceability

This document defines the **production foundations** added to address versioning, raw text storage, granular pipelines, structured errors, and source traceability.

## 1. Tender versioning (Issue 1)

Procurement documents are never isolated uploads. They belong to a **Tender** lineage:

```
Tender (RFP-2026-0142)
 ├── Version 1          [original]
 ├── Version 2          [revision]     → supersedes Version 1
 ├── Corrigendum A      [corrigendum]
 └── Clarification 3    [clarification]
```

### Models

| Model | Purpose |
|-------|---------|
| `Tender` | Business package: `reference_code`, `title`, `organization`, `status` |
| `DocumentVersion` | Links `Tender` ↔ `Document`; `version_type`, `version_label`, `version_sequence`, `supersedes`, `is_current` |

### Rules

- Each upload creates a `Document` + `DocumentVersion` under a tender.
- `is_current=True` marks the active version for retrieval/summarization (previous currents are cleared on new upload).
- `supersedes_version_id` optional on upload to record explicit lineage.
- API: `POST /api/v1/documents/upload/` accepts `tender_reference`, `tender_id`, `version_type`, `version_label`, `supersedes_version_id`.
- API: `GET /api/v1/tenders/`, `GET /api/v1/tenders/{id}/` for lineage inspection.

Without this structure, corrigendums cause **stale summaries**, **inconsistent retrieval**, and **impossible comparisons**.

---

## 2. Raw text storage (Issue 2)

**Do not jump straight to chunks.** Phase 2 must persist intermediate representations on `DocumentExtractedContent`:

| Field | Phase 2 usage |
|-------|----------------|
| `raw_text` | Full extracted text (OCR or native parse) |
| `page_map` | `[{page, start_offset, end_offset, ...}]` |
| `layout_structure` | Blocks, tables, headers |
| `section_hierarchy` | Nested section tree |
| `content_ready` | `True` after OCR/sectioning |

Phase 1 creates an **empty scaffold** at upload/intake so schema and APIs are stable before OCR ships.

---

## 3. Granular pipeline stages (Issue 3)

`PipelineStage` replaces coarse-only statuses:

```
uploaded → queued
→ intake_processing → intake_completed        [Phase 1]
→ ocr_processing → ocr_completed              [Phase 2]
→ sectioning_processing → sectioning_completed
→ chunking_processing → chunking_completed
→ embedding_processing → embedding_completed
→ extraction_processing → extraction_completed
→ summary_processing
→ completed | failed
```

### Supporting structures

- `ProcessingJob.current_stage` — active stage
- `ProcessingJob.completed_stages` — JSON list for **partial recovery**
- `ProcessingStageLog` — per-stage `started` / `completed` / `failed` audit rows

Retries can resume from the last incomplete stage instead of restarting the entire pipeline.

---

## 4. Structured error taxonomy (Issue 4)

Failures are stored on `ProcessingJob.last_error`:

```json
{
  "error_type": "INTAKE_FAILURE",
  "stage": "intake_processing",
  "recoverable": true,
  "retry_count": 2,
  "message": "Stored file missing",
  "details": {
    "exception_class": "FileNotFoundError"
  }
}
```

`ProcessingErrorType` enum: `STORAGE_FAILURE`, `VALIDATION_FAILURE`, `INTAKE_FAILURE`, `OCR_FAILURE`, `SECTIONING_FAILURE`, `CHUNKING_FAILURE`, `EMBEDDING_FAILURE`, `EXTRACTION_FAILURE`, `SUMMARY_FAILURE`, `TIMEOUT_FAILURE`, `UNKNOWN_FAILURE`.

Plain `error_message` / `error_code` remain for admin filters; **canonical source is `last_error`**.

---

## 5. Source traceability (Issue 5)

`SourceReference` model — populated in Phase 2+ when extractions/summaries are generated:

```json
{
  "source_document": "RFP-2026-0142 / Version 2",
  "page": 14,
  "section": "Eligibility Criteria",
  "section_path": "Volume I > Eligibility Criteria",
  "chunk_id": "chk_abc123",
  "confidence": 0.91,
  "char_offset_start": 12040,
  "char_offset_end": 12890
}
```

`DocumentDetail` API returns `source_trace_schema` as the **required citation shape** for downstream features.

For procurement/legal use cases, every summary and extraction MUST cite `SourceReference` rows — not free-text guesses.

---

## Phase roadmap alignment

| Phase | Activates |
|-------|-----------|
| 1 | Tender versioning, content scaffold, intake stages, structured errors, trace schema |
| 2 | OCR → populate `DocumentExtractedContent`, `SourceReference` on extraction |
| 3 | Chunking/embedding with `chunk_id` linkage |
| 4 | Summary/RAG with mandatory citations |
