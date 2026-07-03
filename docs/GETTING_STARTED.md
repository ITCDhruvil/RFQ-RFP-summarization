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

### 1a. Start the services

- **Windows:** PostgreSQL runs as a service after install. Start Redis/Memurai (`memurai` service or `redis-server.exe`).
- **macOS:** `brew services start postgresql@16 && brew services start redis`
- **Linux:** `sudo systemctl start postgresql redis`

### 1b. Open a psql shell as the admin (`postgres`) user

```powershell
# Windows (default install path — adjust version number)
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres
# macOS / Linux
psql -U postgres
```

You'll be prompted for the `postgres` superuser password (the one you set during install). You should land at a prompt like:

```
postgres=#
```

### 1c. Create the user and database

Run these three commands inside the psql shell (each ends with `;`):

```sql
CREATE USER rfq_user WITH PASSWORD 'rfq_password';
CREATE DATABASE rfq_platform OWNER rfq_user;
GRANT ALL PRIVILEGES ON DATABASE rfq_platform TO rfq_user;
```

> ⚠️ Pick your **own** password — don't ship `rfq_password` to production. If your password contains `@`, `#`, or `%`, you must URL-encode it in `.env` (see 1e).

### 1d. Verify, then exit

```sql
\l          -- list databases; you should see rfq_platform owned by rfq_user
\du         -- list roles; you should see rfq_user
\q          -- quit psql
```

Quick connection test as the new user:

```powershell
psql -U rfq_user -d rfq_platform -h localhost   # enter rfq_password when prompted
```

### 1e. Point `.env` at your database

The backend reads a single `DATABASE_URL`. Format:

```
postgres://<user>:<password>@<host>:<port>/<db_name>
```

In `backend/.env` (created in step 2), set:

```env
DATABASE_URL=postgres://rfq_user:rfq_password@localhost:5432/rfq_platform
```

Mapping to what you just created:

| Part        | Value            | Where it came from            |
|-------------|------------------|-------------------------------|
| user        | `rfq_user`       | `CREATE USER` (1c)            |
| password    | `rfq_password`   | `CREATE USER ... PASSWORD`    |
| host        | `localhost`      | your local PostgreSQL         |
| port        | `5432`           | PostgreSQL default            |
| db_name     | `rfq_platform`   | `CREATE DATABASE` (1c)        |

**Example — custom password with special chars.** If you set the password to `P@ss#1`, URL-encode it (`@` → `%40`, `#` → `%23`):

```env
DATABASE_URL=postgres://rfq_user:P%40ss%231@localhost:5432/rfq_platform
```

**Example — cloud/managed PostgreSQL** (e.g. RDS, Neon, Supabase) on a non-default host/port:

```env
DATABASE_URL=postgres://rfq_user:secret@db.example.com:5433/rfq_platform
```

Django applies the schema in step 2 via `python manage.py migrate` — no manual table creation needed.

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
