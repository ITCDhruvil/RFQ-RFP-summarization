# Getting Started — Running the App

Step-by-step guide to run the RFQ/RFP platform locally. You need **4 processes**: PostgreSQL, Redis, the Django backend, and the Next.js frontend (plus an optional Celery worker for async AI jobs).

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16+
- Redis 7+ (Windows: [Memurai](https://www.memurai.com/) or [Redis for Windows](https://github.com/microsoftarchive/redis/releases))
- (Optional) Tesseract OCR — scanned-PDF fallback, see [PARSING.md](PARSING.md)
- (Optional) OpenAI API key — Phase 3/4 AI features, see [INTELLIGENCE.md](INTELLIGENCE.md)

---

## 1. Database & Redis

Start PostgreSQL and Redis, then create the DB and user:

```sql
CREATE USER rfq_user WITH PASSWORD 'rfq_password';
CREATE DATABASE rfq_platform OWNER rfq_user;
```

---

## 2. Backend (terminal 1)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate          # Windows
# source .venv/bin/activate       # macOS/Linux

pip install -r requirements.txt
copy .env.example .env            # Windows  (cp on macOS/Linux)
# Edit .env: set OPENAI_API_KEY and confirm DATABASE_URL / Redis URLs

python manage.py migrate
python manage.py createsuperuser  # optional (admin access)
python manage.py runserver
```

- API → http://localhost:8000
- Admin → http://localhost:8000/admin/
- Health → http://localhost:8000/api/health/

> **`No module named 'whitenoise'`?** You're on system Python. Activate `.venv` or run `.\.venv\Scripts\python manage.py runserver`.

---

## 3. Celery worker (terminal 2) — optional

Needed only for async AI generation. Dev defaults (`INTELLIGENCE_SYNC_GENERATION=True`, `PROCESSING_SYNC=True`) run inline, so you can skip this for basic use.

```powershell
cd backend
.\.venv\Scripts\activate
celery -A config worker -l info -P solo   # -P solo required on Windows
```

---

## 4. Frontend (terminal 3)

```powershell
cd frontend
npm install
copy .env.example .env.local      # Windows  (cp on macOS/Linux)
npm run dev
```

- UI → http://localhost:3000

---

## Verify

1. Open http://localhost:3000
2. Upload a PDF/DOCX
3. Watch it move through `uploaded → parsing → completed`
4. Open the document → view parsed sections, generate summary/proposal, or chat

## After pulling changes

```powershell
cd backend && .\.venv\Scripts\activate && pip install -r requirements.txt && python manage.py migrate
cd frontend && npm install
```

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `No module named 'whitenoise'` | Activate `.venv` first |
| DB connection refused | PostgreSQL not running / wrong `DATABASE_URL` |
| Celery won't start on Windows | Add `-P solo` |
| AI jobs stuck | Start the Celery worker, or set `INTELLIGENCE_SYNC_GENERATION=True` |
| Password with `@ # %` in `DATABASE_URL` | URL-encode (`#` → `%23`) |
