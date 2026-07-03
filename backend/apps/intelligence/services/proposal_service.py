"""Generate technical proposal drafts from RFP intelligence."""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from django.conf import settings
from django.utils import timezone

from apps.chat.services.retrieval_service import RetrievalService
from apps.core.exceptions import ValidationServiceError
from apps.documents.models import Document
from apps.intelligence.choices import SummaryStatus
from apps.intelligence.models import ExtractedInsight, GeneratedProposal, GeneratedSummary
from apps.intelligence.prompts.proposal_templates import (
    PROPOSAL_SYSTEM_PROMPT_V2,
    proposal_user_prompt_v2,
)
from apps.intelligence.services.openai_service import OpenAIService
from apps.intelligence.services.proposal_cancel import (
    ProposalCancelledError,
    is_run_cancelled,
)
from apps.intelligence.services.proposal_compliance_matrix_builder import (
    merge_llm_matrix_responses,
)
from apps.intelligence.services.proposal_pipeline_context import (
    build_pipeline_context,
    pipeline_context_to_json,
)
from apps.intelligence.services.proposal_enrichment import enrich_proposal_from_pipeline
from apps.intelligence.services.proposal_postprocess import (
    count_placeholders_in_text,
    postprocess_proposal,
)
from apps.intelligence.services.proposal_schemas import (
    build_briefing_context_for_proposal,
    pipeline_context_to_llm_json,
)
from apps.intelligence.services.proposal_validator import (
    compute_section_confidence,
    validate_proposal,
)

logger = logging.getLogger(__name__)

_CANCEL_POLL_SECONDS = 0.75
_CANCEL_DB_CHECK_SECONDS = 3.0


def _raise_if_cancelled(document_id, proposal: GeneratedProposal) -> None:
    proposal.refresh_from_db()
    if proposal.status != SummaryStatus.PROCESSING:
        raise ProposalCancelledError(proposal.error_message or "Cancelled by user.")

    run_id = (proposal.model_metadata or {}).get("run_id")
    if not is_run_cancelled(str(document_id), run_id):
        return

    proposal.status = SummaryStatus.FAILED
    proposal.error_message = "Cancelled by user."
    proposal.completed_at = timezone.now()
    proposal.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
    raise ProposalCancelledError("Cancelled by user.")


def _cancelled_in_cache(document_id, proposal: GeneratedProposal) -> bool:
    run_id = (proposal.model_metadata or {}).get("run_id")
    return is_run_cancelled(str(document_id), run_id)


def _chat_json_with_cancel(
    client: OpenAIService,
    *,
    document_id,
    proposal: GeneratedProposal,
    system: str,
    user: str,
) -> tuple[dict, dict]:
    """Run OpenAI call in a worker thread and poll for user cancellation."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(
            client.chat_json,
            system=system,
            user=user,
        )
        last_db_check = 0.0
        while True:
            now = time.monotonic()
            if now - last_db_check >= _CANCEL_DB_CHECK_SECONDS:
                _raise_if_cancelled(document_id, proposal)
                last_db_check = now
            elif _cancelled_in_cache(document_id, proposal):
                _raise_if_cancelled(document_id, proposal)
            try:
                return future.result(timeout=_CANCEL_POLL_SECONDS)
            except FuturesTimeoutError:
                continue


_RETRIEVAL_QUERIES = (
    "technical requirements scope of work deliverables specifications",
    "evaluation criteria scoring methodology technical commercial weight",
    "implementation plan timeline milestones staffing deployment",
    "SLA service levels penalties risks compliance mandatory documents",
)


def _retrieval_queries() -> tuple[str, ...]:
    count = max(1, int(getattr(settings, "PROPOSAL_RETRIEVAL_QUERY_COUNT", 4)))
    return _RETRIEVAL_QUERIES[:count]

DEFAULT_BIDDER_PROFILE: dict = {
    "company_name": "",
    "capabilities": [],
    "certifications": [],
    "key_personnel": [],
    "reference_projects": [],
    "additional_notes": "",
    "knowledge_assets": {
        "policies": [],
        "sops": [],
        "service_catalog": [],
        "training_programs": [],
        "resumes": [],
        "certifications": [],
        "org_structure": "",
    },
}


class ProposalService:
    @staticmethod
    def normalize_bidder_profile(raw: dict | None) -> dict:
        if not raw or not isinstance(raw, dict):
            return dict(DEFAULT_BIDDER_PROFILE)
        return {
            "company_name": str(raw.get("company_name") or "").strip(),
            "capabilities": [
                str(c).strip() for c in (raw.get("capabilities") or []) if str(c).strip()
            ],
            "certifications": [
                str(c).strip()
                for c in (raw.get("certifications") or [])
                if str(c).strip()
            ],
            "key_personnel": [
                p
                for p in (raw.get("key_personnel") or [])
                if isinstance(p, dict) and any(p.values())
            ],
            "reference_projects": [
                p
                for p in (raw.get("reference_projects") or [])
                if isinstance(p, dict) and any(p.values())
            ],
            "additional_notes": str(raw.get("additional_notes") or "").strip(),
            "knowledge_assets": ProposalService._normalize_knowledge_assets(
                raw.get("knowledge_assets")
            ),
        }

    @staticmethod
    def _normalize_knowledge_assets(raw: dict | None) -> dict:
        if not raw or not isinstance(raw, dict):
            return dict(DEFAULT_BIDDER_PROFILE["knowledge_assets"])
        return {
            "policies": [str(x).strip() for x in (raw.get("policies") or []) if str(x).strip()],
            "sops": [str(x).strip() for x in (raw.get("sops") or []) if str(x).strip()],
            "service_catalog": [
                str(x).strip() for x in (raw.get("service_catalog") or []) if str(x).strip()
            ],
            "training_programs": [
                str(x).strip()
                for x in (raw.get("training_programs") or [])
                if str(x).strip()
            ],
            "resumes": [str(x).strip() for x in (raw.get("resumes") or []) if str(x).strip()],
            "certifications": [
                str(x).strip()
                for x in (raw.get("certifications") or [])
                if str(x).strip()
            ],
            "org_structure": str(raw.get("org_structure") or "").strip(),
        }

    @staticmethod
    def ensure_prerequisites(document: Document) -> GeneratedSummary:
        summary = GeneratedSummary.objects.filter(
            document=document,
            is_current=True,
            status=SummaryStatus.COMPLETED,
        ).first()
        if not summary or not summary.summary_json:
            raise ValidationServiceError(
                "A completed procurement briefing is required before generating a proposal.",
                code="summary_required",
            )
        return summary

    @staticmethod
    def build_supplemental_chunks(document_id: str, proposal: GeneratedProposal | None = None) -> list[dict]:
        if proposal is not None:
            _raise_if_cancelled(document_id, proposal)

        chunk_chars = int(getattr(settings, "PROPOSAL_SUPPLEMENTAL_CHUNK_CHARS", 3000))
        chunk_limit = int(getattr(settings, "PROPOSAL_SUPPLEMENTAL_CHUNK_LIMIT", 8))
        hits = RetrievalService.retrieve_batch(document_id, list(_retrieval_queries()))
        by_id: dict[str, dict] = {}
        for chunk in hits:
            prev = by_id.get(chunk.chunk_id)
            if prev is None or chunk.score > prev.get("score", 0):
                by_id[chunk.chunk_id] = {
                    "chunk_id": chunk.chunk_id,
                    "section_title": chunk.section_title,
                    "page_start": chunk.page_start,
                    "page_end": chunk.page_end,
                    "text": chunk.text[:chunk_chars],
                    "score": chunk.score,
                }
        ordered = sorted(by_id.values(), key=lambda c: (-c["score"], c.get("page_start", 1)))
        return ordered[:chunk_limit]

    @staticmethod
    def generate_proposal(
        document: Document,
        proposal: GeneratedProposal,
        *,
        bidder_profile: dict | None = None,
    ) -> GeneratedProposal:
        t0 = time.perf_counter()
        _raise_if_cancelled(document.id, proposal)
        summary = ProposalService.ensure_prerequisites(document)
        profile = ProposalService.normalize_bidder_profile(bidder_profile)

        insights = list(
            ExtractedInsight.objects.filter(
                document=document, generated_summary=summary
            ).order_by("extraction_type")
        )
        if not insights:
            insights = list(
                ExtractedInsight.objects.filter(document=document).order_by(
                    "extraction_type"
                )
            )

        pipeline_ctx = build_pipeline_context(insights, profile)
        t_pipeline = time.perf_counter()
        _raise_if_cancelled(document.id, proposal)

        chunks = ProposalService.build_supplemental_chunks(str(document.id), proposal)
        t_retrieval = time.perf_counter()

        llm_refines_matrix = bool(
            getattr(settings, "PROPOSAL_MATRIX_DETERMINISTIC", True)
            and getattr(settings, "PROPOSAL_MATRIX_LLM_REFINE", False)
        )
        pipeline_json = json.dumps(
            pipeline_context_to_llm_json(
                pipeline_ctx,
                include_compliance_matrix=llm_refines_matrix,
            ),
            indent=2,
            ensure_ascii=False,
        )
        briefing_json = json.dumps(
            build_briefing_context_for_proposal(summary.summary_json or {}),
            indent=2,
            ensure_ascii=False,
        )
        supplemental_json = json.dumps(chunks, indent=2, ensure_ascii=False)

        user = proposal_user_prompt_v2(
            document_name=document.original_filename,
            pipeline_context_json=pipeline_json,
            briefing_json=briefing_json,
            supplemental_chunks_json=supplemental_json,
            llm_refines_compliance_matrix=llm_refines_matrix,
        )

        client = OpenAIService()
        data, usage = _chat_json_with_cancel(
            client,
            document_id=document.id,
            proposal=proposal,
            system=PROPOSAL_SYSTEM_PROMPT_V2,
            user=user,
        )
        t_llm = time.perf_counter()
        _raise_if_cancelled(document.id, proposal)

        data = postprocess_proposal(data)
        pipeline_json_dict = pipeline_context_to_json(pipeline_ctx)
        data = enrich_proposal_from_pipeline(
            data,
            profile,
            pipeline_json_dict,
            document_name=document.original_filename,
        )
        _raise_if_cancelled(document.id, proposal)

        pre_matrix = pipeline_ctx.get("pre_built_compliance_matrix") or []
        if getattr(settings, "PROPOSAL_MATRIX_DETERMINISTIC", True):
            if getattr(settings, "PROPOSAL_MATRIX_LLM_REFINE", True):
                data["compliance_matrix"] = merge_llm_matrix_responses(
                    pre_matrix, data.get("compliance_matrix") or []
                )
            else:
                data["compliance_matrix"] = pre_matrix

        data["traceability_matrix"] = pipeline_ctx.get("traceability_matrix") or []

        req_count = len(pipeline_ctx.get("requirements") or [])
        _violations, validation_report = validate_proposal(
            data, profile, requirement_count=req_count
        )
        section_confidence = compute_section_confidence(
            data, pipeline_context_to_json(pipeline_ctx), validation_report
        )

        if validation_report.get("blocked"):
            proposal.status = SummaryStatus.FAILED
            proposal.error_message = validation_report.get("blocking_reason") or (
                "Proposal failed validation."
            )
            proposal.proposal_json = {
                "_pipeline": pipeline_context_to_json(pipeline_ctx),
                "_meta": {
                    "validation": validation_report,
                    "pipeline_version": "2.1.0",
                },
            }
            proposal.completed_at = timezone.now()
            proposal.save()
            raise ValidationServiceError(
                proposal.error_message,
                code="proposal_validation_failed",
            )

        placeholder_count = count_placeholders_in_text(data)
        gap_count = len(data.get("gaps_and_placeholders") or [])

        data["_pipeline"] = pipeline_context_to_json(pipeline_ctx)
        data["_meta"] = {
            "model": client.model,
            "prompt_version": settings.PROPOSAL_PROMPT_VERSION,
            "pipeline_version": pipeline_ctx.get("pipeline_version") or "2.1.0",
            "generated_at": timezone.now().isoformat(),
            "summary_id": str(summary.id),
            "summary_version": summary.version,
            "supplemental_chunk_count": len(chunks),
            "requirement_count": req_count,
            "placeholder_count": placeholder_count,
            "gap_count": gap_count,
            "validation": validation_report,
            "section_confidence": section_confidence,
            "token_usage": usage,
            "disclaimer": (
                "AI-generated draft for internal review only. "
                "Verify all facts before submission."
            ),
        }
        if data.get("meta") and isinstance(data["meta"], dict):
            data["meta"]["document_name"] = document.original_filename
            data["meta"]["volumes"] = data["meta"].get("volumes") or ["technical"]

        proposal.refresh_from_db()
        if proposal.status != SummaryStatus.PROCESSING:
            raise ProposalCancelledError(proposal.error_message or "Cancelled by user.")

        proposal.proposal_json = data
        proposal.bidder_profile_snapshot = profile
        proposal.model_metadata = {
            "model": client.model,
            "prompt_version": settings.PROPOSAL_PROMPT_VERSION,
            "summary_id": str(summary.id),
            "placeholder_count": placeholder_count,
        }
        proposal.total_tokens = usage.get("total_tokens", 0)
        proposal.status = SummaryStatus.COMPLETED
        proposal.completed_at = timezone.now()
        proposal.save()

        logger.info(
            "proposal_generated document_id=%s proposal_id=%s version=%s "
            "timing_ms pipeline=%.0f retrieval=%.0f llm=%.0f post=%.0f total=%.0f "
            "tokens=%s prompt_chars=%s",
            document.id,
            proposal.id,
            proposal.version,
            (t_pipeline - t0) * 1000,
            (t_retrieval - t_pipeline) * 1000,
            (t_llm - t_retrieval) * 1000,
            (time.perf_counter() - t_llm) * 1000,
            (time.perf_counter() - t0) * 1000,
            usage.get("total_tokens", 0),
            len(user),
        )
        return proposal
