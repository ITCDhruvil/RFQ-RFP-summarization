# RFQ/RFP Document Intelligence Platform

Production POC for RFQ/RFP document upload, parsing, and (future) grounded summarization.

| Phase | Scope |
|-------|--------|
| **1** | Upload, Celery pipeline, tender versioning, stage tracking |
| **2** | PDF/DOCX parsing, sections, tables, page-level text, inspection UI |
| **3** | OpenAI grounded extraction + procurement summary |
| **4** | Document-scoped RAG chat (Chroma + citations) |

Phase 3 uses **OpenAI** for focused extraction and summaries. Phase 4 adds **Chroma** vector search and a **per-document chat** UI (see [docs/CHAT.md](docs/CHAT.md)).

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Django 5, DRF, PostgreSQL, Celery, Redis |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind, Axios, React Query |

## Repository structure

```
RAQ-Document-summarizer/
├── backend/                 # Django API + Celery workers
├── frontend/                # Next.js UI
├── docs/
│   ├── API_CONTRACTS.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── PARSING.md
│   ├── INTELLIGENCE.md
│   └── CHAT.md
└── README.md
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+ (local install or managed instance)
- Redis 7+ (local install or managed instance)
- **Tesseract OCR** (optional, for scanned PDF fallback) — see [docs/PARSING.md](docs/PARSING.md)
- **OpenAI API key** (Phase 3) — see [docs/INTELLIGENCE.md](docs/INTELLIGENCE.md)

## Quick start

### 1. PostgreSQL and Redis

Install and start PostgreSQL and Redis on your machine, then create the database and user:

```sql
CREATE USER rfq_user WITH PASSWORD 'rfq_password';
CREATE DATABASE rfq_platform OWNER rfq_user;
```

Ensure `DATABASE_URL` and Redis URLs in `backend/.env` match your local setup (defaults assume `localhost:5432` and `localhost:6379`).

**Windows:** Install [PostgreSQL](https://www.postgresql.org/download/windows/) and [Redis](https://github.com/microsoftarchive/redis/releases) (or Memurai), or use cloud-hosted instances and point `.env` at those URLs.

**macOS:** `brew install postgresql@16 redis` then `brew services start postgresql@16` and `brew services start redis`.

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows — activate the venv before every backend command (required)
.\.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux

python manage.py migrate
python manage.py createsuperuser   # optional, for admin
python manage.py runserver
# Or without activating: .\.venv\Scripts\python manage.py runserver 127.0.0.1:8002
```

**If you see `No module named 'whitenoise'`:** you are using system Python, not `.venv`. Activate the venv above or run commands with `.\.venv\Scripts\python`.

In a **second terminal** (same venv):

```bash
cd backend
.\.venv\Scripts\activate
celery -A config worker -l info
```

API: http://localhost:8000  
Admin: http://localhost:8000/admin/  
Health: http://localhost:8000/api/health/

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env.local   # Windows
# cp .env.example .env.local   # macOS/Linux
npm run dev
```

UI: http://localhost:3000

## Environment variables

### Backend (`backend/.env`)

See `backend/.env.example` for all keys. Minimum:

```env
SECRET_KEY=your-dev-secret-key
DEBUG=True
DATABASE_URL=postgres://rfq_user:rfq_password@localhost:5432/rfq_platform
# If the DB password contains @, #, or %, URL-encode them (e.g. # → %23).
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CORS_ALLOWED_ORIGINS=http://localhost:3000
MEDIA_ROOT=./media
```

### Frontend (`frontend/.env.local`)

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_API_HEALTH_URL=http://localhost:8000/api/health/
```

## API endpoints (Phase 1)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health/` | Health check |
| POST | `/api/v1/documents/upload/` | Upload PDF/DOCX |
| GET | `/api/v1/documents/` | List documents |
| GET | `/api/v1/documents/{id}/` | Document details |
| GET | `/api/v1/documents/{id}/status/` | Processing status (polling) |
| GET | `/api/v1/processing/jobs/{id}/` | Job details |
| GET | `/api/v1/documents/{id}/parsed/` | Parsed document summary |
| GET | `/api/v1/documents/{id}/parsed/status/` | Parsing status |
| GET | `/api/v1/documents/{id}/parsed/pages/` | Page-level text |
| GET | `/api/v1/documents/{id}/parsed/sections/` | Detected sections |
| POST | `/api/v1/documents/{id}/summary/generate/` | Start AI summary (async) |
| GET | `/api/v1/documents/{id}/summary/` | Grounded briefing JSON |
| GET | `/api/v1/documents/{id}/insights/` | Extracted procurement facts |
| POST | `/api/v1/documents/{id}/proposal/generate/` | Start AI proposal draft (async) |
| GET | `/api/v1/documents/{id}/proposal/` | Technical proposal JSON |
| GET | `/api/v1/documents/{id}/proposal/status/` | Proposal generation status |
| GET | `/api/v1/documents/{id}/proposal/download/` | Proposal PDF export |

Full contracts: [docs/API_CONTRACTS.md](docs/API_CONTRACTS.md) · [docs/INTELLIGENCE.md](docs/INTELLIGENCE.md) · [docs/PROPOSAL.md](docs/PROPOSAL.md)

## Processing statuses

**Upload pipeline:** `uploaded` → `queued` → `intake_*` → `parsing_*` → `completed`

**AI summary (on demand):** `chunking_*` → `extraction_*` → `summary_processing` → `completed`

Docs: [docs/PARSING.md](docs/PARSING.md) · [docs/INTELLIGENCE.md](docs/INTELLIGENCE.md) · [docs/DATA_MODEL.md](docs/DATA_MODEL.md)

**UI:** `/documents/{id}/parsed` · `/documents/{id}/summary` · `/documents/{id}/proposal`

After pulling changes:

```bash
pip install -r requirements.txt
python manage.py migrate
```

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for system design, layering, and extension points.

## Production notes

- Set `DJANGO_SETTINGS_MODULE=config.settings.production`
- Use strong `SECRET_KEY`, disable `DEBUG`, configure `ALLOWED_HOSTS`
- Run via Gunicorn + reverse proxy; serve media from object storage in later phases
- Scale Celery workers horizontally; Redis and PostgreSQL managed services recommended

## Phase 2+ (not implemented)

- AI summarization and structured extraction
- Embeddings and vector search
- OCR pipelines
- LangChain / agent workflows
- Human review and audit export
