# Phase 4 — Document-Scoped RAG Chat

## Goal

Let users **ask questions about a single uploaded document** and receive answers grounded in retrieved text, with page/section citations. Not tender-wide search, not a generic chatbot.

## Why Chroma (not FAISS)

| | **Chroma** | **FAISS** |
|---|------------|-----------|
| Persistence | Built-in on disk (`CHROMA_PERSIST_DIR`) | Manual save/load per index |
| Document filter | `where={"document_id": "..."}` | Custom ID maps + post-filter |
| Ops for POC | Embedded, no extra server | Great for batch/offline search |

For **one collection + per-document isolation**, Chroma fits this platform better. FAISS is preferable at very large scale with custom sharding.

## Flow

```
DocumentChunk (Phase 3)
  → OpenAI embeddings (text-embedding-3-small)
  → Chroma upsert (metadata: document_id, chunk_id, pages, section)
User question
  → embed query
  → Chroma top-K (filtered by document_id)
  → GPT-4o JSON answer + citations
  → SourceReference (kind=citation) + chat message stored
```

Indexing runs automatically during **Generate summary** (`embedding_processing` stage). Older documents: open chat UI and click **Index document for chat**, or `POST /api/v1/documents/{id}/chat/index/`.

## APIs

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/documents/{id}/chat/index/` | Index status |
| POST | `/api/v1/documents/{id}/chat/index/` | Build/refresh Chroma index |
| GET | `/api/v1/documents/{id}/chat/sessions/` | List sessions |
| POST | `/api/v1/documents/{id}/chat/sessions/` | Create session |
| GET | `/api/v1/documents/{id}/chat/sessions/{session_id}/` | Session + messages |
| POST | `/api/v1/documents/{id}/chat/sessions/{session_id}/messages/` | Send message (`{"message": "..."}`) |

## Prerequisites

- Document **parsed** and **chunked** (run Phase 3 generate summary once).
- `OPENAI_API_KEY` set for embeddings + chat.
- `chromadb` installed (`pip install -r requirements.txt`).

## Configuration

```env
CHROMA_PERSIST_DIR=./chroma_data
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
CHAT_RETRIEVAL_TOP_K=8
CHAT_MAX_HISTORY_TURNS=6
CHAT_MIN_RETRIEVAL_SCORE=0.25
```

## Frontend

`/documents/{id}/chat` — conversation UI with citations under each assistant reply.

## Grounding (prompt v4.1+)

When the answer is not supported by retrieved document excerpts, the assistant reply is exactly:

**Not found in this document.**

No speculation, no generic legal filler, and no long “could not find” explanations. Partial multi-part answers cite supported facts and use the same phrase for unsupported parts.

## Celery on Windows

Run worker with solo pool: `celery -A config worker -l info -P solo`
