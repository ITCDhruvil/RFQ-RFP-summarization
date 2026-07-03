"""Commercial proposal generation — deterministic pricing + LLM narratives."""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from django.conf import settings
from django.utils import timezone

from apps.core.exceptions import ValidationServiceError
from apps.documents.models import Document
from apps.intelligence.choices import SummaryStatus
from apps.intelligence.models import ExtractedInsight, GeneratedCommercialProposal, GeneratedSummary
from apps.intelligence.prompts.commercial_proposal_templates import (
    COMMERCIAL_SYSTEM_PROMPT,
    commercial_user_prompt,
)
from apps.intelligence.services.commercial_pipeline_context import (
    build_commercial_workbench,
    refresh_pricing_in_workbench,
)
from apps.intelligence.services.commercial_proposal_cancel import (
    CommercialProposalCancelledError,
    is_run_cancelled,
)
from apps.intelligence.services.commercial_schemas import (
    COMMERCIAL_PIPELINE_VERSION,
    normalize_commercial_vendor_profile,
)
from apps.intelligence.services.commercial_enrichment import enrich_commercial_narrative
from apps.intelligence.services.commercial_validator import validate_commercial_workbench
from apps.intelligence.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


def _raise_if_cancelled(document_id, proposal: GeneratedCommercialProposal) -> None:
    proposal.refresh_from_db()
    if proposal.status != SummaryStatus.PROCESSING:
        raise CommercialProposalCancelledError(proposal.error_message or "Cancelled by user.")
    run_id = (proposal.model_metadata or {}).get("run_id")
    if is_run_cancelled(str(document_id), run_id):
        proposal.status = SummaryStatus.FAILED
        proposal.error_message = "Cancelled by user."
        proposal.completed_at = timezone.now()
        proposal.save(update_fields=["status", "error_message", "completed_at", "updated_at"])
        raise CommercialProposalCancelledError("Cancelled by user.")


def _chat_json_with_cancel(
    client: OpenAIService,
    *,
    document_id,
    proposal: GeneratedCommercialProposal,
    system: str,
    user: str,
) -> tuple[dict, dict]:
    poll_seconds = 0.75
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.chat_json, system=system, user=user)
        while True:
            _raise_if_cancelled(document_id, proposal)
            try:
                return future.result(timeout=poll_seconds)
            except FuturesTimeoutError:
                continue


class CommercialProposalService:
    @staticmethod
    def ensure_prerequisites(document: Document) -> GeneratedSummary:
        summary = GeneratedSummary.objects.filter(
            document=document,
            is_current=True,
            status=SummaryStatus.COMPLETED,
        ).first()
        if not summary or not summary.summary_json:
            raise ValidationServiceError(
                "A completed procurement briefing is required before generating a commercial proposal.",
                code="summary_required",
            )
        return summary

    @staticmethod
    def load_insights(document: Document, summary: GeneratedSummary) -> list[ExtractedInsight]:
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
        return insights

    @staticmethod
    def prepare_draft(
        document: Document,
        proposal: GeneratedCommercialProposal,
        *,
        vendor_profile: dict | None = None,
    ) -> GeneratedCommercialProposal:
        summary = CommercialProposalService.ensure_prerequisites(document)
        profile = normalize_commercial_vendor_profile(
            vendor_profile or proposal.vendor_profile
        )
        insights = CommercialProposalService.load_insights(document, summary)
        workbench = build_commercial_workbench(
            insights, profile, proposal.workbench or None
        )
        proposal.vendor_profile = profile
        proposal.workbench = workbench
        proposal.save(update_fields=["vendor_profile", "workbench", "updated_at"])
        return proposal

    @staticmethod
    def merge_deterministic_sections(
        narrative: dict,
        workbench: dict,
        vendor_profile: dict,
        document_name: str,
    ) -> dict:
        pricing = workbench.get("pricing") or {}
        terms = workbench.get("terms") or {}
        return {
            **narrative,
            "pricing_summary": pricing.get("summary") or {},
            "resource_pricing_table": pricing.get("resource_lines") or [],
            "cost_breakdown": {
                "lines": pricing.get("resource_lines") or [],
                "summary": pricing.get("summary") or {},
            },
            "assumptions": workbench.get("assumptions") or [],
            "exclusions": workbench.get("exclusions") or [],
            "terms": terms,
            "requirements": workbench.get("requirements") or {},
            "section_plan": workbench.get("section_plan") or [],
            "meta": {
                **(narrative.get("meta") or {}),
                "document_name": document_name,
                "volumes": ["commercial"],
                "currency": terms.get("currency") or vendor_profile.get("currency"),
                "pipeline_version": COMMERCIAL_PIPELINE_VERSION,
                "pricing_source": "commercial_pricing_engine",
            },
        }

    @staticmethod
    def generate_commercial_proposal(
        document: Document,
        proposal: GeneratedCommercialProposal,
    ) -> GeneratedCommercialProposal:
        _raise_if_cancelled(document.id, proposal)
        summary = CommercialProposalService.ensure_prerequisites(document)
        profile = normalize_commercial_vendor_profile(proposal.vendor_profile)
        insights = CommercialProposalService.load_insights(document, summary)

        workbench = build_commercial_workbench(insights, profile, proposal.workbench)
        workbench = refresh_pricing_in_workbench(workbench)
        validation = validate_commercial_workbench(
            workbench,
            profile,
            strict=getattr(settings, "COMMERCIAL_PROPOSAL_STRICT_VALIDATION", True),
        )
        workbench["validation_report"] = validation
        proposal.workbench = workbench

        if validation.get("blocked"):
            proposal.status = SummaryStatus.FAILED
            proposal.error_message = validation.get("blocking_reason") or (
                "Commercial proposal failed validation."
            )
            proposal.completed_at = timezone.now()
            proposal.save()
            raise ValidationServiceError(
                proposal.error_message,
                code="commercial_validation_failed",
            )

        user = commercial_user_prompt(
            document_name=document.original_filename,
            requirements_json=json.dumps(workbench.get("requirements") or {}, indent=2),
            vendor_profile_json=json.dumps(profile, indent=2),
            pricing_engine_json=json.dumps(workbench.get("pricing") or {}, indent=2),
            assumptions_json=json.dumps(workbench.get("assumptions") or [], indent=2),
            exclusions_json=json.dumps(workbench.get("exclusions") or [], indent=2),
            terms_json=json.dumps(workbench.get("terms") or {}, indent=2),
            section_plan_json=json.dumps(workbench.get("section_plan") or [], indent=2),
        )

        client = OpenAIService()
        narrative, usage = _chat_json_with_cancel(
            client,
            document_id=document.id,
            proposal=proposal,
            system=COMMERCIAL_SYSTEM_PROMPT,
            user=user,
        )
        _raise_if_cancelled(document.id, proposal)

        pricing_summary = (workbench.get("pricing") or {}).get("summary") or {}
        terms = workbench.get("terms") or {}
        narrative = enrich_commercial_narrative(
            narrative,
            document_name=document.original_filename,
            vendor_profile=profile,
            pricing_summary=pricing_summary,
            terms=terms,
        )

        commercial_json = CommercialProposalService.merge_deterministic_sections(
            narrative,
            workbench,
            profile,
            document.original_filename,
        )
        commercial_json["_workbench"] = workbench
        commercial_json["_meta"] = {
            "model": client.model,
            "prompt_version": getattr(
                settings, "COMMERCIAL_PROPOSAL_PROMPT_VERSION", "1.0.0"
            ),
            "pipeline_version": COMMERCIAL_PIPELINE_VERSION,
            "generated_at": timezone.now().isoformat(),
            "summary_id": str(summary.id),
            "validation": validation,
            "token_usage": usage,
            "disclaimer": (
                "AI-generated commercial narrative for internal review only. "
                "Verify all pricing, tax, and legal terms before submission."
            ),
        }

        proposal.refresh_from_db()
        if proposal.status != SummaryStatus.PROCESSING:
            raise CommercialProposalCancelledError(proposal.error_message or "Cancelled by user.")

        proposal.commercial_json = commercial_json
        proposal.workbench = workbench
        proposal.vendor_profile = profile
        proposal.model_metadata = {
            **(proposal.model_metadata or {}),
            "model": client.model,
            "prompt_version": getattr(
                settings, "COMMERCIAL_PROPOSAL_PROMPT_VERSION", "1.0.0"
            ),
        }
        proposal.total_tokens = usage.get("total_tokens", 0)
        proposal.status = SummaryStatus.COMPLETED
        proposal.completed_at = timezone.now()
        proposal.save()

        logger.info(
            "commercial_proposal_generated document_id=%s proposal_id=%s",
            document.id,
            proposal.id,
        )
        return proposal
