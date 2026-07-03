# Enterprise Commercial Proposal Engine

## Design principle

Technical and commercial proposals are **independent deliverables** sharing only:

- Completed procurement briefing (`GeneratedSummary`)
- RFP extractions (`ExtractedInsight`)
- Document context

```
RFP → Technical Proposal   (GeneratedProposal)
RFP → Commercial Proposal  (GeneratedCommercialProposal)
```

Pricing is **never** computed by the LLM. The pricing engine is deterministic; the LLM writes narrative sections only.

---

## Architecture

```
RFP extractions
    ↓
commercial_requirement_registry.py   — structured commercial requirements
    ↓
CommercialVendorProfile (vendor_profile JSON)
    ↓
commercial_gap_detector.py           — missing inputs only
    ↓
Dynamic questionnaire (frontend)     — gap-driven questions
    ↓
commercial_pricing_engine.py         — deterministic totals
    ↓
commercial_assumptions.py / commercial_exclusions.py
    ↓
commercial_section_planner.py
    ↓
commercial_validator.py            — blocking validation
    ↓
commercial_proposal_service.py       — LLM narratives + merge deterministic sections
    ↓
commercial_proposal_pdf_service.py
```

Pipeline version: **1.0.0**

---

## Database model

`GeneratedCommercialProposal` (migration `0003_generated_commercial_proposal`):

| Field | Purpose |
|-------|---------|
| `commercial_json` | Final output (narrative + pricing tables + assumptions) |
| `vendor_profile` | `CommercialVendorProfile` snapshot |
| `workbench` | Editable draft: requirements, questionnaire, pricing, assumptions, exclusions, terms, validation |
| `status` | `pending` → `processing` → `completed` / `failed` |

Parallel to `GeneratedProposal`; no shared table.

---

## API (document-scoped)

Base: `/api/v1/documents/{document_id}/commercial-proposal/`

| Method | Path | Purpose |
|--------|------|---------|
| POST | `prepare/` | Initialize workbench + questionnaire |
| GET | `/` | Current commercial proposal |
| GET | `status/` | Poll generation status |
| GET | `questionnaire/` | Gap-driven questions |
| PUT | `pricing/` | Edit pricing lines → recalculate |
| PUT | `assumptions/` | Edit assumptions |
| PUT | `terms/` | Edit terms + questionnaire answers |
| POST | `validate/` | Run `commercial_validator` |
| POST | `generate/` | Start generation (async/sync) |
| POST | `cancel/` | Stop in-flight generation |
| GET | `download/` | PDF export |

User-requested global routes (`/commercial-proposals/{id}`) map to document-scoped resources via `commercial_proposal_id` in responses.

---

## Services

| Module | Role |
|--------|------|
| `commercial_schemas.py` | Types, defaults, profile normalization |
| `commercial_requirement_registry.py` | Extract duration, currency, billing, resource counts |
| `commercial_gap_detector.py` | Missing inputs + question schema |
| `commercial_pricing_engine.py` | **Deterministic** pricing |
| `commercial_assumptions.py` | Assumption list (editable) |
| `commercial_exclusions.py` | Exclusion list (editable) |
| `commercial_section_planner.py` | 12 commercial sections |
| `commercial_validator.py` | Blocking validation |
| `commercial_pipeline_context.py` | Workbench orchestration |
| `commercial_proposal_service.py` | Generation + LLM |
| `commercial_proposal_orchestrator.py` | Lifecycle |
| `commercial_proposal_dispatch.py` | Sync thread / Celery |
| `commercial_proposal_pdf_service.py` | ReportLab PDF |

---

## Settings

```env
COMMERCIAL_PROPOSAL_PROMPT_VERSION=1.0.0
COMMERCIAL_PROPOSAL_STRICT_VALIDATION=True
```

Reuses `INTELLIGENCE_SYNC_GENERATION` for dev sync mode.

---

## Frontend

- `/documents/[id]/commercial-proposal` — vendor profile, gap questionnaire, spreadsheet pricing editor, validate, generate, PDF
- Links from briefing page and document actions menu

---

## Future-proofing hooks

| Capability | Extension point |
|------------|-----------------|
| Multi-currency | `vendor_profile.currency`, `requirements.currency` |
| Regional tax rules | `commercial_pricing_engine` tax strategy plugins |
| Rate card versioning | `vendor_profile.rate_cards[]` with `version` |
| Approval workflows | `workbench.approval_chain` + status gates |
| Discounting | `pricing.discount_rules[]` in engine |
| Bid/No-Bid | `workbench.bid_analysis` pre-generation gate |

---

## Migration plan

1. ✅ `0003_generated_commercial_proposal` — new table
2. No changes to `GeneratedProposal`
3. Optional later: `CommercialRateCard` DB model for org-level reuse across documents

---

## Implementation status

| Phase | Status |
|-------|--------|
| Commercial requirement extraction | ✅ |
| Vendor commercial profile | ✅ |
| Gap detection | ✅ |
| Dynamic questionnaire | ✅ |
| Pricing engine | ✅ |
| Assumptions / exclusions | ✅ |
| Section planner | ✅ |
| Editable pricing tables | ✅ |
| Validation | ✅ |
| Proposal generation | ✅ |
| PDF output | ✅ |
| APIs | ✅ |
| Frontend workflow | ✅ |
