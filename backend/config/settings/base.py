"""
Base settings for RFQ/RFP Document Intelligence Platform.
"""
import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:3000"]),
    MAX_UPLOAD_SIZE_MB=(int, 50),
    CELERY_TASK_MAX_RETRIES=(int, 3),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="change-me-in-production-use-strong-key")
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.core",
    "apps.authentication",
    "apps.documents",
    "apps.processing",
    "apps.parsing",
    "apps.intelligence",
    "apps.chat",
    "apps.health",
]

# OpenAI (Phase 3)
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="gpt-4o")
OPENAI_TIMEOUT_SECONDS = env.int("OPENAI_TIMEOUT_SECONDS", default=120)
OPENAI_MAX_RETRIES = env.int("OPENAI_MAX_RETRIES", default=3)
OPENAI_TEMPERATURE = env.float("OPENAI_TEMPERATURE", default=0.1)
INTELLIGENCE_MAX_CHUNK_CHARS = env.int("INTELLIGENCE_MAX_CHUNK_CHARS", default=6000)
# text-embedding-3-* allows 8192 tokens (~32 000 chars). Cap at 1.5× the max chunk
# size — no need to send more; truncation just wastes the API call budget.
OPENAI_EMBEDDING_MAX_CHARS = env.int("OPENAI_EMBEDDING_MAX_CHARS", default=9000)
INTELLIGENCE_PROMPT_VERSION = env("INTELLIGENCE_PROMPT_VERSION", default="4.4.1")
PROPOSAL_PROMPT_VERSION = env("PROPOSAL_PROMPT_VERSION", default="2.1.0")
PROPOSAL_STRICT_VALIDATION = env.bool("PROPOSAL_STRICT_VALIDATION", default=True)
PROPOSAL_MATRIX_DETERMINISTIC = env.bool("PROPOSAL_MATRIX_DETERMINISTIC", default=True)
# False = skip LLM compliance-matrix output (deterministic matrix only) — much faster.
PROPOSAL_MATRIX_LLM_REFINE = env.bool("PROPOSAL_MATRIX_LLM_REFINE", default=False)
PROPOSAL_SUPPLEMENTAL_CHUNK_LIMIT = env.int("PROPOSAL_SUPPLEMENTAL_CHUNK_LIMIT", default=8)
PROPOSAL_SUPPLEMENTAL_CHUNK_CHARS = env.int("PROPOSAL_SUPPLEMENTAL_CHUNK_CHARS", default=3000)
PROPOSAL_RETRIEVAL_QUERY_COUNT = env.int("PROPOSAL_RETRIEVAL_QUERY_COUNT", default=4)
COMMERCIAL_PROPOSAL_PROMPT_VERSION = env("COMMERCIAL_PROPOSAL_PROMPT_VERSION", default="1.0.0")
COMMERCIAL_PROPOSAL_STRICT_VALIDATION = env.bool("COMMERCIAL_PROPOSAL_STRICT_VALIDATION", default=True)
INTELLIGENCE_DEFAULT_EXTRACTION_CHUNKS = env.int(
    "INTELLIGENCE_DEFAULT_EXTRACTION_CHUNKS", default=10
)
INTELLIGENCE_BROAD_EXTRACTION_CHUNKS = env.int(
    "INTELLIGENCE_BROAD_EXTRACTION_CHUNKS", default=14
)
# Number of parallel threads for extraction (one per type). Default = 8 = len(FOCUSED_EXTRACTION_TYPES).
# Lower this on resource-constrained machines or when hitting OpenAI rate limits.
INTELLIGENCE_EXTRACTION_WORKERS = env.int("INTELLIGENCE_EXTRACTION_WORKERS", default=8)
# Opt #5 — max chars per chunk after paragraph-level pre-filtering (3 500 ≈ 875 tokens).
INTELLIGENCE_CHUNK_TRIM_CHARS = env.int("INTELLIGENCE_CHUNK_TRIM_CHARS", default=3500)
# Opt #6 — chunks grouped into one LLM call. 3 → 14 chunks = 5 calls instead of 14.
# Set to 1 to send one chunk per call (original behaviour).
INTELLIGENCE_EXTRACTION_BATCH_SIZE = env.int("INTELLIGENCE_EXTRACTION_BATCH_SIZE", default=3)
# False = enqueue Celery; True = run pipeline in HTTP request (slow, dev-friendly)
INTELLIGENCE_SYNC_GENERATION = env.bool("INTELLIGENCE_SYNC_GENERATION", default=False)
# False = Celery worker parses uploads; True = parse in background thread (dev/Windows)
PROCESSING_SYNC = env.bool("PROCESSING_SYNC", default=False)

# Phase 4 — Document-scoped RAG chat (Chroma)
CHROMA_PERSIST_DIR = Path(
    env("CHROMA_PERSIST_DIR", default=str(BASE_DIR / "chroma_data"))
)
CHROMA_COLLECTION_NAME = env("CHROMA_COLLECTION_NAME", default="rfq_document_chunks")
OPENAI_EMBEDDING_MODEL = env("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")
CHAT_RETRIEVAL_TOP_K = env.int("CHAT_RETRIEVAL_TOP_K", default=8)
CHAT_MAX_HISTORY_TURNS = env.int("CHAT_MAX_HISTORY_TURNS", default=6)
CHAT_PROMPT_VERSION = env("CHAT_PROMPT_VERSION", default="4.1.0")
CHAT_MIN_RETRIEVAL_SCORE = env.float("CHAT_MIN_RETRIEVAL_SCORE", default=0.25)

# Document parsing (Phase 2)
PARSING_OCR_ENABLED = env.bool("PARSING_OCR_ENABLED", default=True)
PARSING_QUALITY_OCR_THRESHOLD = env.float("PARSING_QUALITY_OCR_THRESHOLD", default=0.35)
PARSING_MIN_PAGE_TEXT_LENGTH = env.int("PARSING_MIN_PAGE_TEXT_LENGTH", default=25)

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.request_logging.RequestLoggingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://rfq_user:rfq_password@localhost:5432/rfq_platform",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Media / uploads
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
DOCUMENT_UPLOAD_DIR = MEDIA_ROOT / "documents"

# DOCX → PDF preview (LibreOffice headless or docx2pdf on Windows + Word)
DOCX_PREVIEW_ENABLED = env.bool("DOCX_PREVIEW_ENABLED", default=True)
LIBREOFFICE_PATH = env("LIBREOFFICE_PATH", default="")
DOCX_PREVIEW_USE_WORD = env.bool(
    "DOCX_PREVIEW_USE_WORD", default=sys.platform == "win32"
)
DOCX_PREVIEW_TIMEOUT_SEC = env.int("DOCX_PREVIEW_TIMEOUT_SEC", default=120)

MAX_UPLOAD_SIZE_BYTES = env.int("MAX_UPLOAD_SIZE_MB", default=50) * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_UPLOAD_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "EXCEPTION_HANDLER": "apps.core.exceptions.custom_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("API_THROTTLE_RATE", default="100/hour"),
        "upload": env("UPLOAD_THROTTLE_RATE", default="30/hour"),
    },
}

# CORS
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/1")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

# ── P5: Worker hardening ──────────────────────────────────────────────────────
# Recycle each worker process after N tasks to prevent memory leaks.
CELERY_WORKER_MAX_TASKS_PER_CHILD = env.int("CELERY_WORKER_MAX_TASKS_PER_CHILD", default=50)
# Soft/hard memory limit per worker process (MB). Soft triggers a graceful restart;
# hard kills the process. Requires billiard ≥ 4.x or use --max-memory-per-child flag.
CELERY_WORKER_MAX_MEMORY_PER_CHILD = env.int(
    "CELERY_WORKER_MAX_MEMORY_PER_CHILD", default=512000  # 512 MB in KB
)
# Store results for 24 h then expire from Redis.
CELERY_RESULT_EXPIRES = env.int("CELERY_RESULT_EXPIRES", default=86400)
# Prefetch 1 task at a time — avoids one worker hoarding long-running doc jobs.
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# Reject tasks that have been waiting in queue longer than 1 hour (stale uploads).
CELERY_TASK_SOFT_TIME_LIMIT = env.int("CELERY_TASK_SOFT_TIME_LIMIT", default=600)   # 10 min
CELERY_TASK_TIME_LIMIT = env.int("CELERY_TASK_TIME_LIMIT", default=900)              # 15 min
# Send task-failure events so the Django app can poll/react.
CELERY_SEND_TASK_ERROR_EMAILS = False  # use structured logging instead
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_MAX_RETRIES = env.int("CELERY_TASK_MAX_RETRIES", default=3)
CELERY_TASK_DEFAULT_RETRY_DELAY = env.int("CELERY_TASK_RETRY_DELAY", default=60)

# Structured logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": (
                '{"timestamp":"%(asctime)s","level":"%(levelname)s",'
                '"logger":"%(name)s","message":"%(message)s"}'
            ),
            "datefmt": "%Y-%m-%dT%H:%M:%SZ",
        },
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "apps": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO"), "propagate": False},
        "celery": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = MAX_UPLOAD_SIZE_BYTES
