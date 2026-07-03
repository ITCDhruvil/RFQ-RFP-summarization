"""Orchestrate commercial proposal lifecycle."""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ValidationServiceError
from apps.documents.models import Document
from apps.intelligence.choices import ProposalStatus
from apps.intelligence.models import GeneratedCommercialProposal
from apps.intelligence.services.commercial_pipeline_context import refresh_pricing_in_workbench
from apps.intelligence.services.commercial_proposal_cancel import (
    CommercialProposalCancelledError,
    start_run,
)
from apps.intelligence.services.commercial_proposal_service import CommercialProposalService
from apps.intelligence.services.commercial_schemas import normalize_commercial_vendor_profile
from apps.intelligence.services.commercial_validator import validate_commercial_workbench
from apps.processing.errors import StructuredProcessingError
from apps.processing.choices import ProcessingErrorType, PipelineStage
from apps.processing.services.job_service import ProcessingJobService

logger = logging.getLogger(__name__)


class CommercialProposalOrchestrator:
    @staticmethod
    @transaction.atomic
    def start_new_draft(
        document: Document,
        *,
        vendor_profile: dict | None = None,
    ) -> GeneratedCommercialProposal:
        """Archive the current commercial proposal and create a fresh pending draft."""
        active = GeneratedCommercialProposal.objects.filter(
            document=document, is_current=True
        ).first()
        if active and active.status == ProposalStatus.PROCESSING:
            raise ValidationServiceError(
                "Commercial proposal generation is in progress. Stop it before starting a new proposal.",
                code="commercial_proposal_in_progress",
            )

        GeneratedCommercialProposal.objects.filter(
            document=document, is_current=True
        ).update(is_current=False)
        last_version = (
            GeneratedCommercialProposal.objects.filter(document=document)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
            or 0
        )
        proposal = GeneratedCommercialProposal.objects.create(
            document=document,
            status=ProposalStatus.PENDING,
            version=last_version + 1,
            is_current=True,
            commercial_json={},
            workbench={},
            model_metadata={},
            total_tokens=0,
            error_message="",
            last_error={},
        )
        return CommercialProposalService.prepare_draft(
            document, proposal, vendor_profile=vendor_profile
        )

    @staticmethod
    @transaction.atomic
    def get_or_create_draft(
        document: Document,
        *,
        vendor_profile: dict | None = None,
    ) -> GeneratedCommercialProposal:
        existing = GeneratedCommercialProposal.objects.filter(
            document=document, is_current=True
        ).first()
        if existing and existing.status == ProposalStatus.COMPLETED:
            return existing
        if existing and existing.status == ProposalStatus.PROCESSING:
            raise ValidationServiceError(
                "Commercial proposal generation already in progress.",
                code="commercial_proposal_in_progress",
            )
        if not existing:
            existing = GeneratedCommercialProposal.objects.create(
                document=document,
                status=ProposalStatus.PENDING,
                version=1,
                is_current=True,
            )
        return CommercialProposalService.prepare_draft(
            document, existing, vendor_profile=vendor_profile
        )

    @staticmethod
    @transaction.atomic
    def prepare_proposal_record(
        document: Document, *, regenerate: bool
    ) -> GeneratedCommercialProposal:
        CommercialProposalService.ensure_prerequisites(document)

        if regenerate:
            GeneratedCommercialProposal.objects.filter(
                document=document, is_current=True
            ).update(is_current=False)
            last_version = (
                GeneratedCommercialProposal.objects.filter(document=document)
                .order_by("-version")
                .values_list("version", flat=True)
                .first()
                or 0
            )
            version = last_version + 1
        else:
            existing = GeneratedCommercialProposal.objects.filter(
                document=document, is_current=True
            ).first()
            if existing and existing.status == ProposalStatus.COMPLETED:
                raise ValidationServiceError(
                    "Commercial proposal exists. Set regenerate=true to replace.",
                    code="commercial_proposal_exists",
                )
            if existing and existing.status == ProposalStatus.PROCESSING:
                raise ValidationServiceError(
                    "Commercial proposal generation already in progress.",
                    code="commercial_proposal_in_progress",
                )
            version = existing.version if existing else 1
            if existing:
                existing.delete()

        return GeneratedCommercialProposal.objects.create(
            document=document,
            status=ProposalStatus.PROCESSING,
            version=version,
            is_current=True,
            started_at=timezone.now(),
        )

    @staticmethod
    @transaction.atomic
    def begin_processing(
        document_id,
        *,
        regenerate: bool,
        vendor_profile: dict | None = None,
    ) -> GeneratedCommercialProposal:
        document = Document.objects.get(pk=document_id)
        run_id = str(uuid.uuid4())
        start_run(str(document_id), run_id)

        draft = GeneratedCommercialProposal.objects.filter(
            document=document, is_current=True
        ).first()
        workbench = draft.workbench if draft else {}
        profile = normalize_commercial_vendor_profile(
            vendor_profile or (draft.vendor_profile if draft else None)
        )

        proposal = CommercialProposalOrchestrator.prepare_proposal_record(
            document, regenerate=regenerate
        )
        proposal.vendor_profile = profile
        proposal.workbench = workbench
        proposal.model_metadata = {**(proposal.model_metadata or {}), "run_id": run_id}
        proposal.save(
            update_fields=["vendor_profile", "workbench", "model_metadata", "updated_at"]
        )
        CommercialProposalService.prepare_draft(document, proposal, vendor_profile=profile)
        return proposal

    @staticmethod
    def update_workbench(
        proposal: GeneratedCommercialProposal,
        *,
        pricing: dict | None = None,
        assumptions: list | None = None,
        exclusions: list | None = None,
        terms: dict | None = None,
        questionnaire_answers: dict | None = None,
    ) -> GeneratedCommercialProposal:
        workbench = dict(proposal.workbench or {})
        if questionnaire_answers is not None:
            workbench["questionnaire_answers"] = questionnaire_answers
        if pricing is not None:
            workbench["pricing"] = pricing
            workbench = refresh_pricing_in_workbench(workbench)
        if assumptions is not None:
            workbench["assumptions"] = assumptions
        if exclusions is not None:
            workbench["exclusions"] = exclusions
        if terms is not None:
            workbench["terms"] = {**(workbench.get("terms") or {}), **terms}
        proposal.workbench = workbench
        proposal.save(update_fields=["workbench", "updated_at"])
        return proposal

    @staticmethod
    def validate(proposal: GeneratedCommercialProposal) -> dict:
        profile = normalize_commercial_vendor_profile(proposal.vendor_profile)
        report = validate_commercial_workbench(
            proposal.workbench or {},
            profile,
            strict=getattr(settings, "COMMERCIAL_PROPOSAL_STRICT_VALIDATION", True),
        )
        workbench = dict(proposal.workbench or {})
        workbench["validation_report"] = report
        proposal.workbench = workbench
        proposal.save(update_fields=["workbench", "updated_at"])
        return report

    @staticmethod
    def run(
        document_id,
        *,
        regenerate: bool = False,
        vendor_profile: dict | None = None,
    ) -> dict:
        document = Document.objects.get(pk=document_id)
        proposal = GeneratedCommercialProposal.objects.filter(
            document=document,
            is_current=True,
            status=ProposalStatus.PROCESSING,
        ).first()
        if not proposal:
            proposal = CommercialProposalOrchestrator.begin_processing(
                document_id, regenerate=regenerate, vendor_profile=vendor_profile
            )

        try:
            proposal = CommercialProposalService.generate_commercial_proposal(
                document, proposal
            )
            return {
                "commercial_proposal_id": str(proposal.id),
                "version": proposal.version,
                "status": proposal.status,
                "total_tokens": proposal.total_tokens,
            }
        except CommercialProposalCancelledError:
            proposal.refresh_from_db()
            return {
                "commercial_proposal_id": str(proposal.id),
                "version": proposal.version,
                "status": proposal.status,
                "cancelled": True,
            }
        except Exception as exc:
            logger.exception("commercial_proposal_failed document_id=%s", document_id)
            proposal.status = ProposalStatus.FAILED
            proposal.error_message = str(exc)[:2000]
            proposal.completed_at = timezone.now()
            structured = StructuredProcessingError.from_exception(
                exc,
                stage=PipelineStage.SUMMARY_PROCESSING,
                error_type=ProcessingErrorType.SUMMARY_FAILURE,
                recoverable=False,
                retry_count=0,
            )
            proposal.last_error = structured.to_dict()
            proposal.save()
            job = ProcessingJobService.get_latest_job_for_document(document.id)
            if job:
                ProcessingJobService.mark_failed(job, structured)
            raise
