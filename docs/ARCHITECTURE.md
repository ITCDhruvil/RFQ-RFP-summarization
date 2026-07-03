# Architecture — Phase 1

## Overview

Phase 1 delivers the **foundation and upload-processing architecture** for an enterprise RFQ/RFP document intelligence platform. No AI, embeddings, OCR, or vector stores are included.

```
┌─────────────┐     REST      ┌──────────────────────────────────────┐
│  Next.js    │ ────────────► │  Django + DRF                        │
│  Frontend   │               │  ┌──────────┐  ┌──────────────────┐  │
└─────────────┘               │  │ documents│  │ processing       │  │
                              │  │ app      │  │ app              │  │
                              │  └────┬─────┘  └────────┬─────────┘  │
                              │       │ service layer    │             │
                              │       └────────┬─────────┘             │
                              │                ▼                       │
                              │         PostgreSQL                     │
                              │                │                       │
                              │                ▼ enqueue               │
                              │         Celery worker                  │
                              │                │                       │
                              │         Redis (broker + results)       │
                              │                │                       │
                              │         Media storage (files)          │
                              └──────────────────────────────────────┘
```

## Backend layering

| Layer | Responsibility |
|-------|----------------|
| **Views (API)** | HTTP, serialization, throttling |
| **Services** | Business rules, transactions, orchestration |
| **Models** | Persistence, audit timestamps, status enums |
| **Tasks (Celery)** | Async execution, retries, logging |
| **Core** | Shared utilities, middleware, exceptions |

### Apps

- **`apps.core`** — `TimeStampedModel`, `UUIDPrimaryKeyModel`, file validation, request logging, exception handler
- **`apps.authentication`** — Scaffold for future SSO/API keys (Phase 1: Django default user, open API)
- **`apps.documents`** — `Document` model, upload/list/detail APIs
- **`apps.processing`** — `ProcessingJob` model, Celery pipeline, job/status APIs
- **`apps.health`** — Dependency checks (DB, Redis, media)

## Upload flow

1. Client `POST /api/v1/documents/upload/` with multipart file.
2. `DocumentService.upload()` validates extension, size, writes file to `MEDIA_ROOT/documents/`, computes SHA-256.
3. Creates `Document` (`uploaded` → `queued`) and `ProcessingJob` (`queued`).
4. Enqueues `processing.process_document` Celery task.
5. Worker runs intake validation, then `DocumentParsingService.run_parsing()` (Phase 2).
6. Persists `ParsedDocument`, pages, sections; syncs `DocumentExtractedContent`.
7. Updates job/document to `completed` or `failed` with retry semantics.

## Production foundations (Phase 1.1)

| Issue | Solution |
|-------|----------|
| Document versioning | `Tender` + `DocumentVersion` lineage, `is_current`, `supersedes` |
| Raw text storage | `DocumentExtractedContent` (raw_text, page_map, layout, sections) |
| Granular pipeline | `PipelineStage` enum + `ProcessingStageLog` + `completed_stages` |
| Structured errors | `ProcessingJob.last_error` + `ProcessingErrorType` |
| Source traceability | `SourceReference` model + `source_trace_schema` on document API |

Full schema: [DATA_MODEL.md](DATA_MODEL.md).

## Extensibility (future phases)

| Concern | Extension point |
|---------|-----------------|
| OCR | Activate `ocr_*` stages; populate `DocumentExtractedContent` |
| Chunking / embeddings | `chunking_*`, `embedding_*` stages; link `chunk_id` on `SourceReference` |
| RAG / summaries | `summary_*` stage; mandatory `SourceReference` rows per answer |
| Human review | Status transitions + review app |
| Audit logs | `ProcessingStageLog` + dedicated `audit` app |
| Auth | `apps.authentication` models + DRF permissions |

## Frontend architecture

- **App Router** pages: Dashboard, Upload, Document detail
- **`lib/api`** — Axios client and typed API functions
- **`lib/types`** — TypeScript contracts aligned with API
- **React Query** — Caching, polling for non-terminal statuses
- **Components** — Presentational UI (table, dropzone, status badge, shell)

## Security (Phase 1)

- Extension and MIME validation (content-based when `python-magic` available)
- Sanitized filenames; UUID-based storage names
- Upload size limits and rate throttling
- Structured logging with request IDs
- Production settings: HSTS, secure cookies, SSL redirect

## Configuration

Environment-driven via `django-environ` and `.env`:

- `DATABASE_URL`, `CELERY_BROKER_URL`, `MEDIA_ROOT`, `MAX_UPLOAD_SIZE_MB`, `CORS_ALLOWED_ORIGINS`

Separate `development` and `production` settings modules.
