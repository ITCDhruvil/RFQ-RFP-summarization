# API Contracts — Phase 1

Base URL: `http://localhost:8000`

All JSON responses use `Content-Type: application/json`. Errors return:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Human-readable message"
  }
}
```

---

## Health

### `GET /api/health/`

**Response 200** (healthy) / **503** (degraded)

```json
{
  "status": "healthy",
  "service": "rfq-document-platform",
  "version": "1.0.0-phase1",
  "checks": {
    "database": { "status": "ok" },
    "redis": { "status": "ok" },
    "media_storage": { "status": "ok" }
  }
}
```

---

## Documents

### `POST /api/v1/documents/upload/`

**Content-Type:** `multipart/form-data`

| Field | Type   | Required | Description        |
|-------|--------|----------|--------------------|
| file  | binary | yes      | PDF or DOCX file   |

**Response 201**

```json
{
  "id": "uuid",
  "original_filename": "rfq-sample.pdf",
  "mime_type": "application/pdf",
  "size_bytes": 1048576,
  "status": "queued",
  "job_id": "uuid",
  "created_at": "2026-05-22T12:00:00Z"
}
```

**Error codes:** `missing_file`, `invalid_file_type`, `file_too_large`, `invalid_mime_type`, `mime_extension_mismatch`, `storage_error`

Throttle: `30/hour` per client IP (upload scope).

---

### `GET /api/v1/documents/`

Paginated list (page size 20).

**Response 200**

```json
{
  "count": 1,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "original_filename": "rfq-sample.pdf",
      "mime_type": "application/pdf",
      "size_bytes": 1048576,
      "status": "completed",
      "created_at": "2026-05-22T12:00:00Z",
      "updated_at": "2026-05-22T12:00:05Z"
    }
  ]
}
```

---

### `GET /api/v1/documents/{document_id}/`

**Response 200**

```json
{
  "id": "uuid",
  "original_filename": "rfq-sample.pdf",
  "stored_filename": "abc123....pdf",
  "mime_type": "application/pdf",
  "size_bytes": 1048576,
  "status": "completed",
  "metadata": {
    "extension": ".pdf",
    "upload_source": "api",
    "processing": {
      "pipeline_version": "1.0.0",
      "stages_completed": ["intake_validation"],
      "storage_verified": true,
      "ready_for_extraction": true
    }
  },
  "checksum_sha256": "hex",
  "created_at": "2026-05-22T12:00:00Z",
  "updated_at": "2026-05-22T12:00:05Z",
  "latest_job": { }
}
```

---

### `GET /api/v1/documents/{document_id}/status/`

Lightweight status endpoint for polling.

**Response 200**

```json
{
  "document_id": "uuid",
  "status": "processing",
  "latest_job": {
    "id": "uuid",
    "status": "processing",
    "pipeline_stage": "intake_validation",
    "retry_count": 0,
    "error_code": "",
    "error_message": "",
    "celery_task_id": "celery-uuid",
    "started_at": "2026-05-22T12:00:01Z",
    "completed_at": null,
    "created_at": "2026-05-22T12:00:00Z",
    "updated_at": "2026-05-22T12:00:01Z"
  }
}
```

---

## Processing

### `GET /api/v1/processing/jobs/{job_id}/`

**Response 200**

```json
{
  "id": "uuid",
  "document_id": "uuid",
  "document_status": "completed",
  "status": "completed",
  "current_stage": "completed",
  "pipeline_stage": "completed",
  "completed_stages": ["intake_completed"],
  "retry_count": 0,
  "max_retries": 3,
  "error_code": "",
  "error_message": "",
  "last_error": {},
  "celery_task_id": "celery-uuid",
  "started_at": "2026-05-22T12:00:01Z",
  "completed_at": "2026-05-22T12:00:05Z",
  "created_at": "2026-05-22T12:00:00Z",
  "updated_at": "2026-05-22T12:00:05Z"
}
```

---

## Tender versioning

### `GET /api/v1/tenders/` · `GET /api/v1/tenders/{tender_id}/`

See [DATA_MODEL.md](DATA_MODEL.md). Upload accepts `tender_reference`, `version_type`, `version_label`, `supersedes_version_id`.

## Processing status lifecycle

```
uploaded → queued → intake_processing → intake_completed
       → parsing_processing → parsing_completed → completed
                              ↘ failed (structured last_error on job)
```

Phase 3 (on demand): `chunking_*` → `extraction_*` → `summary_processing` → `completed`.

---

## Parsing (Phase 2)

### `GET /api/v1/documents/{document_id}/parsed/status/`

```json
{
  "document_id": "uuid",
  "document_status": "parsing_completed",
  "parsing_status": "completed",
  "parsing_quality_score": 0.91,
  "total_pages": 42,
  "ocr_pages": 2,
  "latest_job": { }
}
```

### `GET /api/v1/documents/{document_id}/parsed/`

```json
{
  "id": "uuid",
  "document_id": "uuid",
  "parsing_status": "completed",
  "total_pages": 42,
  "parsing_quality_score": 0.91,
  "ocr_pages": 2,
  "tables_count": 3,
  "parsing_metadata": {
    "page_quality": [
      { "page": 1, "quality_score": 0.93, "extraction_method": "native_pdf", "ocr_used": false }
    ],
    "tables": [{ "page": 5, "headers": [], "rows": [] }]
  },
  "raw_text_preview": "...",
  "structured_text_preview": "## Introduction\n\n..."
}
```

### `GET /api/v1/documents/{document_id}/parsed/pages/`

Array of pages with `page_number`, `extracted_text`, `extraction_method`, `ocr_used`, `quality_score`.

### `GET /api/v1/documents/{document_id}/parsed/pages/{page_number}/`

Single page object.

### `GET /api/v1/documents/{document_id}/parsed/sections/`

Array of `{ title, content, page_start, page_end, section_order }`.

See [PARSING.md](PARSING.md).

---

## Intelligence / Summary (Phase 3)

### `POST /api/v1/documents/{document_id}/summary/generate/`

Starts async Celery task. Returns **202**.

```json
{
  "message": "Summary generation started.",
  "document_id": "uuid",
  "celery_task_id": "celery-uuid",
  "regenerate": false
}
```

### `POST /api/v1/documents/{document_id}/summary/regenerate/`

Increments version, replaces current summary. Returns **202**.

### `GET /api/v1/documents/{document_id}/summary/status/`

```json
{
  "document_id": "uuid",
  "document_status": "extraction_processing",
  "summary_status": "processing",
  "summary_id": "uuid",
  "version": 1,
  "progress_stage": "extraction_processing",
  "total_tokens": null
}
```

### `GET /api/v1/documents/{document_id}/summary/download/`

Returns a structured **PDF** of the current completed briefing.

| Query | Values | Description |
|-------|--------|-------------|
| `variant` | `full` (default), `executive` | Full report with all sections, or executive summary + critical signals only |

Response: `application/pdf` with `Content-Disposition: attachment`.

Requires `summary_status=completed`.

### `GET /api/v1/documents/{document_id}/summary/`

```json
{
  "id": "uuid",
  "status": "completed",
  "version": 1,
  "summary_json": {
    "executive_summary": { "text": "...", "sources": [{ "page": 12, "section": "...", "source_text": "..." }] },
    "key_requirements": [],
    "important_deadlines": [],
    "technical_scope": {},
    "commercial_terms": {},
    "risks_and_concerns": [],
    "submission_checklist": []
  },
  "total_tokens": 12400
}
```

### `GET /api/v1/documents/{document_id}/insights/`

```json
[
  {
    "extraction_type": "eligibility_criteria",
    "confidence_score": 0.82,
    "payload": {
      "items": [
        {
          "requirement": "Bidder must have 5 years experience",
          "page": 12,
          "section": "Eligibility Criteria",
          "source_text": "verbatim snippet",
          "confidence": 0.91
        }
      ]
    }
  }
]
```

See [INTELLIGENCE.md](INTELLIGENCE.md).

---

## Proposal generation

Requires `summary_status=completed`. See [PROPOSAL.md](PROPOSAL.md).

### `POST /api/v1/documents/{document_id}/proposal/generate/`

Starts async proposal generation. Returns **202** (or **200** if proposal already exists and `regenerate` is not set).

```json
{
  "bidder_profile": {
    "company_name": "Acme Security Ltd",
    "capabilities": ["24/7 guarding", "CCTV monitoring"],
    "certifications": ["ISO 9001"],
    "key_personnel": [],
    "reference_projects": [],
    "additional_notes": "15 years public sector experience"
  },
  "regenerate": false
}
```

Response:

```json
{
  "message": "Proposal generation started.",
  "document_id": "uuid",
  "proposal_id": "uuid",
  "celery_task_id": "celery-uuid",
  "regenerate": false,
  "sync": false
}
```

### `GET /api/v1/documents/{document_id}/proposal/status/`

```json
{
  "document_id": "uuid",
  "proposal_status": "processing",
  "proposal_id": "uuid",
  "version": 1,
  "total_tokens": null,
  "error_message": null,
  "summary_status": "completed"
}
```

### `GET /api/v1/documents/{document_id}/proposal/`

```json
{
  "id": "uuid",
  "status": "completed",
  "version": 1,
  "proposal_json": {
    "cover_letter": { "text": "...", "sources": [] },
    "executive_summary": { "text": "...", "sources": [] },
    "understanding_of_requirements": { "text": "...", "sources": [] },
    "technical_approach": { "sections": [{ "title": "...", "content": "...", "sources": [] }] },
    "compliance_matrix": [{ "requirement_ref": "TR-01", "requirement_text": "...", "response": "...", "compliance": "fully", "sources": [] }],
    "implementation_plan": { "phases": [{ "name": "Mobilization", "duration": "30 days", "deliverables": ["..."] }], "sources": [] },
    "team_and_staffing": { "roles": [{ "title": "Project Manager", "responsibilities": "...", "profile_ref": "[TO BE COMPLETED]" }] },
    "risks_and_mitigations": [{ "risk": "...", "mitigation": "...", "sources": [] }],
    "gaps_and_placeholders": [{ "field": "Commercial pricing", "reason": "pricing_required" }],
    "_meta": { "prompt_version": "1.0.0", "disclaimer": "AI-generated draft..." }
  },
  "bidder_profile_snapshot": {},
  "total_tokens": 8500
}
```

### `GET /api/v1/documents/{document_id}/proposal/download/`

Returns a structured **PDF** of the current completed proposal draft.

Response: `application/pdf` with `Content-Disposition: attachment`.

Requires `proposal_status=completed`.

Document detail includes `extracted_content`, `source_trace_schema`, `tender`, `version`.
