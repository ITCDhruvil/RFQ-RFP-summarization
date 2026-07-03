# Phase 3 — Procurement Intelligence & Grounded Summaries

## Goal

Transform parsed RFQ/RFP documents into **structured, source-grounded** procurement briefings using OpenAI — not a conversational chatbot.

## Flow

```
Parsed sections (Phase 2)
  → Section-aware semantic chunks
  → Focused extraction passes (9 procurement categories)
  → Structured JSON per category
  → Final grounded summary (7 briefing sections)
```

## Pipeline stages (on generate)

`chunking_processing` → `chunking_completed` → `extraction_processing` → `extraction_completed` → `summary_processing` → `completed`

Triggered via API (not on every upload) to control cost.

## Models (`apps.intelligence`)

| Model | Purpose |
|-------|---------|
| `DocumentChunk` | Section-aware text segments with page range |
| `ExtractedInsight` | Per-type JSON extractions with confidence |
| `GeneratedSummary` | Final briefing JSON + version/regenerate |

## Extraction types (focused prompts)

- Eligibility criteria
- Submission deadlines
- Technical requirements
- Scope of work
- Payment terms
- Penalties and risks
- Mandatory documents
- Evaluation criteria

Executive overview is produced in the **final summary** pass from extractions.

## Grounding & quality

- Each item requires `page`, `section`, `source_text`
- Validation: snippet overlap with chunk text; confidence penalty if weak
- Deduplication across chunks
- Missing extraction type detection in `_meta`
- `SourceReference` rows created per extraction item

### Prompt v4.1+ (procurement intelligence)

- Broader extraction instructions (commercial, indirect risks, SLA/support, evaluation weighting)
- Wider chunk coverage for commercial/risk/evaluation types (stratified sampling)
- Summary includes `procurement_critical_signals` and nuanced deadline/risk synthesis
- Regenerate summary after upgrading to refresh existing documents

### Prompt v4.4.1 (operational extraction pinning)

- Scope/technical chunk selection always includes sections with manpower, escort, guarding, or headcount text
- If those extraction passes return zero items, an automatic single-chunk retry runs on operational sections only

### Prompt v4.4.0 (operational scope fidelity)

- Security/manpower/transport-service RFPs: expanded extraction keywords and instructions
- `scope_of_work` uses broad document coverage (same as technical requirements)
- Executive summary must lead with operational objective, scale, and locations when scope extractions exist
- Summary pass injects deterministic operational-scope guidance from extraction counts
- Reduced generic legal-keyword routing for `penalties_and_risks` (fewer false positives)

## APIs

| Method | Path |
|--------|------|
| POST | `/api/v1/documents/{id}/summary/generate/` |
| POST | `/api/v1/documents/{id}/summary/regenerate/` |
| GET | `/api/v1/documents/{id}/summary/` |
| GET | `/api/v1/documents/{id}/summary/status/` |
| GET | `/api/v1/documents/{id}/insights/` |

## Configuration

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.1
INTELLIGENCE_MAX_CHUNK_CHARS=6000
```

## Frontend

`/documents/{id}/summary` — generate/regenerate, progress polling, expandable briefing, insights with citations.

**PDF export:** `GET /api/v1/documents/{id}/summary/download/?variant=full|executive` — structured report (full briefing or executive edition). Buttons on the briefing page header when a summary is completed.

## Explicitly excluded

- Chat / agents / LangChain / vector DB / RAG retrieval
