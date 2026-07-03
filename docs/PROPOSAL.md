# AI Proposal Generation

Generate a **technical proposal volume draft** from a completed procurement briefing, grounded in RFP extractions and optional bidder profile data.

## Prerequisites

1. Document parsed (`document_status=completed`)
2. Procurement briefing completed (`summary_status=completed`)
3. `OPENAI_API_KEY` configured

## Flow (v2.0.0)

```
Completed briefing + extractions
  → Requirement registry + classification
  → Vendor evidence index (from bidder profile)
  → Capability matching + gap detection
  → Dynamic section plan
  → OpenAI synthesis (pipeline-informed)
  → Validation + confidence scoring
  → Structured proposal draft + compliance matrix
  → In-app viewer + PDF export
```

See [PROPOSAL_ENTERPRISE_REDESIGN.md](PROPOSAL_ENTERPRISE_REDESIGN.md) for full architecture.

## Grounding rules

| Fact type | Source |
|-----------|--------|
| RFP requirements, scope, evaluation | Structured extractions + briefing + Chroma chunks |
| Vendor credentials, team, projects | Bidder profile only |
| Missing vendor data | `[TO BE COMPLETED: …]` placeholders + `gaps_and_placeholders` |

The system **never invents** prices, certifications, project names, or team members.

## Proposal sections (v1)

- Cover letter
- Executive summary
- Understanding of requirements
- Technical approach (4–8 sections, evaluation-weighted)
- Compliance matrix (one row per technical/scope requirement)
- Implementation plan
- Team & staffing
- Risks & mitigations
- Items requiring completion

Commercial pricing and legal forms are **not** generated in v1 — gaps are flagged for human completion.

## APIs

| Method | Path |
|--------|------|
| POST | `/api/v1/documents/{id}/proposal/generate/` |
| GET | `/api/v1/documents/{id}/proposal/` |
| GET | `/api/v1/documents/{id}/proposal/status/` |
| GET | `/api/v1/documents/{id}/proposal/download/` |

See [API_CONTRACTS.md](API_CONTRACTS.md) for request/response shapes.

## Configuration

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
PROPOSAL_PROMPT_VERSION=1.0.0
INTELLIGENCE_SYNC_GENERATION=True   # dev: run in background thread
```

## Frontend

- **Create proposal** button on `/documents/{id}/summary` (when briefing is ready)
- Full workflow at `/documents/{id}/proposal` — bidder profile form, generation progress, expandable viewer, PDF download

## Disclaimer

All generated proposals are **drafts for internal review**. A prominent banner and PDF watermark remind users to verify facts before submission.
