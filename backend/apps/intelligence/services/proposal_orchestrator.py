"""Orchestrate proposal generation lifecycle."""

from __future__ import annotations

import logging
import uuid

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import ValidationServiceError
from apps.documents.models import Document
from apps.intelligence.choices import ProposalStatus
from apps.intelligence.models import GeneratedProposal
from apps.intelligence.services.proposal_cancel import ProposalCancelledError, start_run
from apps.intelligence.services.proposal_service import ProposalService
from apps.processing.errors import StructuredProcessingError
from apps.processing.choices import ProcessingErrorType, PipelineStage
from apps.processing.services.job_service import ProcessingJobService

logger = logging.getLogger(__name__)


class ProposalOrchestrator:
    @staticmethod
    @transaction.atomic
    def start_new_draft(
        document: Document,
        *,
        bidder_profile: dict | None = None,
    ) -> GeneratedProposal:
        """Archive the current proposal and create a fresh pending draft."""
        active = GeneratedProposal.objects.filter(
            document=document, is_current=True
        ).first()
        if active and active.status == ProposalStatus.PROCESSING:
            raise ValidationServiceError(
                "Proposal generation is in progress. Stop it before starting a new proposal.",
                code="proposal_in_progress",
            )

        GeneratedProposal.objects.filter(document=document, is_current=True).update(
            is_current=False
        )
        last_version = (
            GeneratedProposal.objects.filter(document=document)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
            or 0
        )
        profile = ProposalService.normalize_bidder_profile(bidder_profile)
        return GeneratedProposal.objects.create(
            document=document,
            status=ProposalStatus.PENDING,
            version=last_version + 1,
            is_current=True,
            bidder_profile_snapshot=profile,
            proposal_json={},
            model_metadata={},
            total_tokens=0,
            error_message="",
            last_error={},
        )

    @staticmethod
    @transaction.atomic
    def prepare_proposal_record(
        document: Document, *, regenerate: bool
    ) -> GeneratedProposal:
        ProposalService.ensure_prerequisites(document)

        if regenerate:
            GeneratedProposal.objects.filter(document=document, is_current=True).update(
                is_current=False
            )
            last_version = (
                GeneratedProposal.objects.filter(document=document)
                .order_by("-version")
                .values_list("version", flat=True)
                .first()
                or 0
            )
            version = last_version + 1
        else:
            existing = GeneratedProposal.objects.filter(
                document=document, is_current=True
            ).first()
            if existing and existing.status == ProposalStatus.COMPLETED:
                raise ValidationServiceError(
                    "Proposal already exists. Set regenerate=true to replace.",
                    code="proposal_exists",
                )
            if existing and existing.status == ProposalStatus.PROCESSING:
                raise ValidationServiceError(
                    "Proposal generation already in progress.",
                    code="proposal_in_progress",
                )
            version = 1
            if existing:
                version = existing.version
                existing.delete()

        return GeneratedProposal.objects.create(
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
        bidder_profile: dict | None = None,
    ) -> GeneratedProposal:
        document = Document.objects.get(pk=document_id)
        run_id = str(uuid.uuid4())
        start_run(str(document_id), run_id)
        proposal = ProposalOrchestrator.prepare_proposal_record(
            document, regenerate=regenerate
        )
        meta = dict(proposal.model_metadata or {})
        meta["run_id"] = run_id
        proposal.model_metadata = meta
        proposal.bidder_profile_snapshot = ProposalService.normalize_bidder_profile(
            bidder_profile
        )
        proposal.save(
            update_fields=["model_metadata", "bidder_profile_snapshot", "updated_at"]
        )
        logger.info(
            "proposal_begin_processing document_id=%s proposal_id=%s regenerate=%s",
            document_id,
            proposal.id,
            regenerate,
        )
        return proposal

    @staticmethod
    def run(
        document_id,
        *,
        regenerate: bool = False,
        bidder_profile: dict | None = None,
    ) -> dict:
        document = Document.objects.get(pk=document_id)
        proposal = GeneratedProposal.objects.filter(
            document=document,
            is_current=True,
            status=ProposalStatus.PROCESSING,
        ).first()

        if not proposal:
            proposal = ProposalOrchestrator.prepare_proposal_record(
                document, regenerate=regenerate
            )

        profile = bidder_profile
        if profile is None and proposal.bidder_profile_snapshot:
            profile = proposal.bidder_profile_snapshot

        try:
            proposal = ProposalService.generate_proposal(
                document, proposal, bidder_profile=profile
            )
            return {
                "proposal_id": str(proposal.id),
                "version": proposal.version,
                "status": proposal.status,
                "total_tokens": proposal.total_tokens,
            }
        except ProposalCancelledError:
            logger.info("proposal_cancelled document_id=%s", document_id)
            proposal.refresh_from_db()
            return {
                "proposal_id": str(proposal.id),
                "version": proposal.version,
                "status": proposal.status,
                "cancelled": True,
            }
        except Exception as exc:
            logger.exception("proposal_failed document_id=%s", document_id)
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
