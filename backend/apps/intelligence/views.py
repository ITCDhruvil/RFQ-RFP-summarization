import logging

from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import ServiceError, ValidationServiceError
from apps.documents.services.document_service import DocumentService
from apps.intelligence.choices import SummaryStatus
from apps.intelligence.models import (
    ExtractedInsight,
    GeneratedCommercialProposal,
    GeneratedProposal,
    GeneratedSummary,
)
from apps.intelligence.services.briefing_pdf_service import BriefingPdfService
from apps.intelligence.services.proposal_pdf_service import ProposalPdfService
from apps.intelligence.serializers import (
    CommercialProposalStatusSerializer,
    ExtractedInsightSerializer,
    GeneratedCommercialProposalSerializer,
    GeneratedProposalSerializer,
    GeneratedSummarySerializer,
    ProposalStatusSerializer,
    SummaryStatusSerializer,
)
from apps.intelligence.services.generation_dispatch import dispatch_summary_generation
from apps.intelligence.services.proposal_dispatch import dispatch_proposal_generation
from apps.intelligence.services.commercial_proposal_cancel import (
    request_cancel as request_commercial_cancel,
)
from apps.intelligence.services.commercial_proposal_dispatch import (
    dispatch_commercial_proposal_generation,
)
from apps.intelligence.services.commercial_proposal_orchestrator import (
    CommercialProposalOrchestrator,
)
from apps.intelligence.services.commercial_proposal_service import CommercialProposalService
from apps.intelligence.services.commercial_proposal_pdf_service import (
    CommercialProposalPdfService,
)
from apps.intelligence.services.proposal_cancel import request_cancel
from apps.intelligence.services.proposal_orchestrator import ProposalOrchestrator
from apps.processing.choices import PipelineStage
from apps.processing.services.job_service import ProcessingJobService

logger = logging.getLogger(__name__)


class GenerateSummaryView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        regenerate = request.data.get("regenerate", False) in (True, "true", "1")

        if not regenerate:
            current = GeneratedSummary.objects.filter(
                document=document, is_current=True, status="completed"
            ).first()
            if current:
                return Response(
                    {
                        "message": "Summary exists. Set regenerate=true to replace.",
                        "summary_id": str(current.id),
                    },
                    status=status.HTTP_200_OK,
                )

        try:
            body, http_status = dispatch_summary_generation(
                document.id, regenerate=regenerate
            )
        except ServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=exc.status_code,
            )
        except ValidationServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(body, status=http_status)


class RegenerateSummaryView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        try:
            body, http_status = dispatch_summary_generation(
                document.id, regenerate=True
            )
        except ServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=exc.status_code,
            )
        except ValidationServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(body, status=http_status)


class GeneratedSummaryDetailView(APIView):
    def get(self, request, document_id):
        summary = GeneratedSummary.objects.filter(
            document_id=document_id, is_current=True
        ).first()
        if not summary:
            raise ValidationServiceError(
                "No summary found for this document.",
                code="summary_not_found",
            )
        return Response(GeneratedSummarySerializer(summary).data)


class SummaryPdfDownloadView(APIView):
    """Download the current briefing as a structured PDF report."""

    def get(self, request, document_id):
        variant = (request.query_params.get("variant") or "full").strip().lower()
        if variant not in ("full", "executive"):
            raise ValidationServiceError(
                "variant must be 'full' or 'executive'.",
                code="invalid_variant",
            )

        document = DocumentService.get_document(document_id)
        summary = GeneratedSummary.objects.filter(
            document_id=document_id,
            is_current=True,
            status=SummaryStatus.COMPLETED,
        ).first()
        if not summary or not summary.summary_json:
            raise ValidationServiceError(
                "No completed briefing available to export.",
                code="summary_not_ready",
            )

        pdf_bytes = BriefingPdfService.render(
            summary, document, variant=variant
        )
        filename = BriefingPdfService.suggested_filename_for_variant(
            document, summary, variant=variant
        )
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(pdf_bytes)
        return response


class ExtractedInsightsListView(APIView):
    def get(self, request, document_id):
        summary_id = request.query_params.get("summary_id")
        qs = ExtractedInsight.objects.filter(document_id=document_id).order_by(
            "extraction_type"
        )
        if summary_id:
            qs = qs.filter(generated_summary_id=summary_id)
        else:
            current = GeneratedSummary.objects.filter(
                document_id=document_id, is_current=True
            ).first()
            if current:
                qs = qs.filter(generated_summary=current)
        return Response(ExtractedInsightSerializer(qs, many=True).data)


class CancelSummaryView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        summary = GeneratedSummary.objects.filter(
            document=document, is_current=True
        ).first()

        # If already in a terminal state, nothing to do.
        if summary and summary.status in ("completed", "failed"):
            return Response(
                {"message": "Nothing to cancel.", "status": summary.status},
                status=status.HTTP_200_OK,
            )

        # Revoke the Celery task (best-effort — may not exist yet if parsing hasn't
        # handed off to intelligence, or may already be done).
        job = ProcessingJobService.get_latest_job_for_document(document.id)
        if job and job.celery_task_id:
            try:
                from celery import current_app as celery_app
                celery_app.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")
            except Exception as exc:
                logger.warning(
                    "cancel_revoke_failed document_id=%s task_id=%s error=%s",
                    document_id,
                    job.celery_task_id,
                    exc,
                )

        # Mark the summary failed — create a placeholder row if none exists yet
        # (e.g. cancelled during early parsing before the intelligence worker ran).
        if summary:
            summary.status = "failed"
            summary.error_message = "Cancelled by user."
            summary.completed_at = timezone.now()
            summary.save(update_fields=["status", "error_message", "completed_at"])
        else:
            summary = GeneratedSummary.objects.create(
                document=document,
                status="failed",
                error_message="Cancelled by user.",
                is_current=True,
                completed_at=timezone.now(),
            )

        # Always mark the document itself as failed — this is what the dashboard
        # badge reads. Without this the document stays in "parsing_processing" /
        # "queued" indefinitely after the user cancels.
        document.status = PipelineStage.FAILED
        document.save(update_fields=["status", "updated_at"])

        if job:
            try:
                from apps.processing.errors import StructuredProcessingError
                from apps.processing.choices import ProcessingErrorType
                structured = StructuredProcessingError(
                    error_type=ProcessingErrorType.EXTRACTION_FAILURE,
                    stage=job.current_stage,
                    recoverable=True,
                    retry_count=job.retry_count,
                    message="Cancelled by user.",
                )
                ProcessingJobService.mark_failed(job, structured)
            except Exception as exc:
                logger.warning("cancel_job_mark_failed error=%s", exc)

        logger.info(
            "processing_cancelled document_id=%s summary_id=%s",
            document_id,
            summary.id,
        )
        return Response({"message": "Processing cancelled.", "summary_id": str(summary.id)})


class CancelProposalView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = GeneratedProposal.objects.filter(
            document=document, is_current=True
        ).first()

        if proposal and proposal.status in (
            SummaryStatus.COMPLETED,
            SummaryStatus.FAILED,
        ):
            return Response(
                {
                    "message": "Nothing to cancel.",
                    "status": proposal.status,
                    "proposal_id": str(proposal.id),
                },
                status=status.HTTP_200_OK,
            )

        request_cancel(str(document_id), (proposal.model_metadata or {}).get("run_id") if proposal else None)

        task_id = (proposal.model_metadata or {}).get("celery_task_id") if proposal else None
        if task_id:
            try:
                from celery import current_app as celery_app

                celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            except Exception as exc:
                logger.warning(
                    "proposal_cancel_revoke_failed document_id=%s task_id=%s error=%s",
                    document_id,
                    task_id,
                    exc,
                )

        if proposal:
            proposal.status = SummaryStatus.FAILED
            proposal.error_message = "Cancelled by user."
            proposal.completed_at = timezone.now()
            proposal.save(
                update_fields=["status", "error_message", "completed_at", "updated_at"]
            )
        else:
            proposal = GeneratedProposal.objects.create(
                document=document,
                status=SummaryStatus.FAILED,
                error_message="Cancelled by user.",
                is_current=True,
                completed_at=timezone.now(),
            )

        logger.info(
            "proposal_cancelled document_id=%s proposal_id=%s",
            document_id,
            proposal.id,
        )
        return Response(
            {
                "message": "Proposal generation cancelled.",
                "proposal_id": str(proposal.id),
            }
        )


class SummaryStatusView(APIView):
    def get(self, request, document_id):
        document = DocumentService.get_document(document_id)
        summary = GeneratedSummary.objects.filter(
            document_id=document_id, is_current=True
        ).first()

        # Intelligence stages — pass through as-is for the UI progress bar.
        _INTEL_STAGES = frozenset(
            {
                PipelineStage.CHUNKING_PROCESSING,
                PipelineStage.CHUNKING_COMPLETED,
                PipelineStage.EMBEDDING_PROCESSING,
                PipelineStage.EMBEDDING_COMPLETED,
                PipelineStage.EXTRACTION_PROCESSING,
                PipelineStage.EXTRACTION_COMPLETED,
                PipelineStage.SUMMARY_PROCESSING,
            }
        )
        if document.status in _INTEL_STAGES:
            progress_stage = document.status
        elif (
            document.status == PipelineStage.COMPLETED
            and summary
            and summary.status == "completed"
        ):
            # Full pipeline done — briefing is actually ready.
            progress_stage = PipelineStage.COMPLETED
        elif document.status == PipelineStage.COMPLETED:
            # Parse finished but intelligence not done — never send "completed"
            # to the UI or it flashes 100% before extraction starts.
            progress_stage = PipelineStage.PARSING_COMPLETED
        else:
            progress_stage = document.status

        payload = {
            "document_id": document.id,
            "document_status": document.status,
            "summary_status": summary.status if summary else None,
            "summary_id": summary.id if summary else None,
            "version": summary.version if summary else None,
            "progress_stage": progress_stage,
            "total_tokens": summary.total_tokens if summary else None,
            "error_message": summary.error_message if summary else None,
        }
        return Response(SummaryStatusSerializer(payload).data)


class GenerateProposalView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        regenerate = request.data.get("regenerate", False) in (True, "true", "1")
        bidder_profile = request.data.get("bidder_profile")

        if not regenerate:
            current = GeneratedProposal.objects.filter(
                document=document, is_current=True, status="completed"
            ).first()
            if current:
                return Response(
                    {
                        "message": "Proposal exists. Set regenerate=true to replace.",
                        "proposal_id": str(current.id),
                    },
                    status=status.HTTP_200_OK,
                )

        try:
            body, http_status = dispatch_proposal_generation(
                document.id,
                regenerate=regenerate,
                bidder_profile=bidder_profile,
            )
        except ServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=exc.status_code,
            )
        except ValidationServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(body, status=http_status)


class NewProposalView(APIView):
    """Archive the current technical proposal and return a fresh pending draft."""

    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        bidder_profile = request.data.get("bidder_profile")
        try:
            proposal = ProposalOrchestrator.start_new_draft(
                document, bidder_profile=bidder_profile
            )
        except ValidationServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "message": "Ready to create a new technical proposal.",
                "proposal_id": str(proposal.id),
                "version": proposal.version,
                "status": proposal.status,
            },
            status=status.HTTP_200_OK,
        )


class GeneratedProposalDetailView(APIView):
    def get(self, request, document_id):
        proposal = GeneratedProposal.objects.filter(
            document_id=document_id, is_current=True
        ).first()
        if not proposal:
            raise ValidationServiceError(
                "No proposal found for this document.",
                code="proposal_not_found",
            )
        return Response(GeneratedProposalSerializer(proposal).data)


class ProposalStatusView(APIView):
    def get(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = GeneratedProposal.objects.filter(
            document_id=document_id, is_current=True
        ).first()
        summary = GeneratedSummary.objects.filter(
            document_id=document_id, is_current=True
        ).first()

        payload = {
            "document_id": document.id,
            "proposal_status": proposal.status if proposal else None,
            "proposal_id": proposal.id if proposal else None,
            "version": proposal.version if proposal else None,
            "total_tokens": proposal.total_tokens if proposal else None,
            "error_message": proposal.error_message if proposal else None,
            "summary_status": summary.status if summary else None,
        }
        return Response(ProposalStatusSerializer(payload).data)


class ProposalPdfDownloadView(APIView):
    """Download the current proposal as a structured PDF."""

    def get(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = GeneratedProposal.objects.filter(
            document_id=document_id,
            is_current=True,
            status=SummaryStatus.COMPLETED,
        ).first()
        if not proposal or not proposal.proposal_json:
            raise ValidationServiceError(
                "No completed proposal available to export.",
                code="proposal_not_ready",
            )

        pdf_bytes = ProposalPdfService.render(proposal, document)
        filename = ProposalPdfService.suggested_filename(document, proposal)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(pdf_bytes)
        return response


def _get_commercial_proposal(document_id, *, require_current: bool = True):
    qs = GeneratedCommercialProposal.objects.filter(document_id=document_id)
    if require_current:
        qs = qs.filter(is_current=True)
    return qs.first()


class PrepareCommercialProposalView(APIView):
    """Initialize or refresh commercial workbench (questionnaire + pricing draft)."""

    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        vendor_profile = request.data.get("vendor_profile")
        try:
            proposal = CommercialProposalOrchestrator.get_or_create_draft(
                document, vendor_profile=vendor_profile
            )
        except ValidationServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(GeneratedCommercialProposalSerializer(proposal).data)


class CommercialProposalDetailView(APIView):
    def get(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = _get_commercial_proposal(document.id)
        if not proposal:
            raise ValidationServiceError(
                "No commercial proposal found. Call prepare first.",
                code="commercial_proposal_not_found",
            )
        return Response(GeneratedCommercialProposalSerializer(proposal).data)


class CommercialProposalStatusView(APIView):
    def get(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = _get_commercial_proposal(document.id)
        summary = GeneratedSummary.objects.filter(
            document_id=document_id, is_current=True
        ).first()
        payload = {
            "document_id": document.id,
            "commercial_proposal_status": proposal.status if proposal else None,
            "commercial_proposal_id": proposal.id if proposal else None,
            "version": proposal.version if proposal else None,
            "total_tokens": proposal.total_tokens if proposal else None,
            "error_message": proposal.error_message if proposal else None,
            "summary_status": summary.status if summary else None,
        }
        return Response(CommercialProposalStatusSerializer(payload).data)


class CommercialProposalQuestionnaireView(APIView):
    def get(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = _get_commercial_proposal(document.id)
        if not proposal:
            proposal = CommercialProposalOrchestrator.get_or_create_draft(document)
        gap = (proposal.workbench or {}).get("gap_report") or {}
        return Response(
            {
                "questions": gap.get("questions") or [],
                "missing_commercial_inputs": gap.get("missing_commercial_inputs") or [],
                "ready_for_pricing": gap.get("ready_for_pricing", False),
            }
        )


class CommercialProposalPricingView(APIView):
    def put(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = _get_commercial_proposal(document.id)
        if not proposal:
            proposal = CommercialProposalOrchestrator.get_or_create_draft(document)
        pricing = request.data.get("pricing") or request.data
        proposal = CommercialProposalOrchestrator.update_workbench(proposal, pricing=pricing)
        proposal = CommercialProposalService.prepare_draft(document, proposal)
        return Response(GeneratedCommercialProposalSerializer(proposal).data)


class CommercialProposalAssumptionsView(APIView):
    def put(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = _get_commercial_proposal(document.id)
        if not proposal:
            proposal = CommercialProposalOrchestrator.get_or_create_draft(document)
        assumptions = request.data.get("assumptions") or request.data
        proposal = CommercialProposalOrchestrator.update_workbench(
            proposal, assumptions=assumptions
        )
        return Response(GeneratedCommercialProposalSerializer(proposal).data)


class CommercialProposalTermsView(APIView):
    def put(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = _get_commercial_proposal(document.id)
        if not proposal:
            proposal = CommercialProposalOrchestrator.get_or_create_draft(document)
        terms = request.data.get("terms") or request.data
        questionnaire_answers = request.data.get("questionnaire_answers")
        proposal = CommercialProposalOrchestrator.update_workbench(
            proposal,
            terms=terms,
            questionnaire_answers=questionnaire_answers,
        )
        proposal = CommercialProposalService.prepare_draft(document, proposal)
        return Response(GeneratedCommercialProposalSerializer(proposal).data)


class CommercialProposalValidateView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = _get_commercial_proposal(document.id)
        if not proposal:
            proposal = CommercialProposalOrchestrator.get_or_create_draft(document)
        report = CommercialProposalOrchestrator.validate(proposal)
        return Response(report)


class GenerateCommercialProposalView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        regenerate = request.data.get("regenerate", False) in (True, "true", "1")
        vendor_profile = request.data.get("vendor_profile")

        if not regenerate:
            current = GeneratedCommercialProposal.objects.filter(
                document=document, is_current=True, status="completed"
            ).first()
            if current:
                return Response(
                    {
                        "message": "Commercial proposal exists. Set regenerate=true to replace.",
                        "commercial_proposal_id": str(current.id),
                    },
                    status=status.HTTP_200_OK,
                )

        try:
            body, http_status = dispatch_commercial_proposal_generation(
                document.id,
                regenerate=regenerate,
                vendor_profile=vendor_profile,
            )
        except ServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=exc.status_code,
            )
        except ValidationServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(body, status=http_status)


class NewCommercialProposalView(APIView):
    """Archive the current commercial proposal and return a fresh workbench draft."""

    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        vendor_profile = request.data.get("vendor_profile")
        try:
            proposal = CommercialProposalOrchestrator.start_new_draft(
                document, vendor_profile=vendor_profile
            )
        except ValidationServiceError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            GeneratedCommercialProposalSerializer(proposal).data,
            status=status.HTTP_200_OK,
        )


class CancelCommercialProposalView(APIView):
    def post(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = GeneratedCommercialProposal.objects.filter(
            document=document, is_current=True
        ).first()

        if proposal and proposal.status in (
            SummaryStatus.COMPLETED,
            SummaryStatus.FAILED,
        ):
            return Response(
                {
                    "message": "Nothing to cancel.",
                    "status": proposal.status,
                    "commercial_proposal_id": str(proposal.id),
                },
                status=status.HTTP_200_OK,
            )

        request_commercial_cancel(
            str(document_id),
            (proposal.model_metadata or {}).get("run_id") if proposal else None,
        )

        task_id = (proposal.model_metadata or {}).get("celery_task_id") if proposal else None
        if task_id:
            try:
                from celery import current_app as celery_app

                celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
            except Exception as exc:
                logger.warning(
                    "commercial_cancel_revoke_failed document_id=%s error=%s",
                    document_id,
                    exc,
                )

        if proposal:
            proposal.status = SummaryStatus.FAILED
            proposal.error_message = "Cancelled by user."
            proposal.completed_at = timezone.now()
            proposal.save(
                update_fields=["status", "error_message", "completed_at", "updated_at"]
            )
        else:
            proposal = GeneratedCommercialProposal.objects.create(
                document=document,
                status=SummaryStatus.FAILED,
                error_message="Cancelled by user.",
                is_current=True,
                completed_at=timezone.now(),
            )

        return Response(
            {
                "message": "Commercial proposal generation cancelled.",
                "commercial_proposal_id": str(proposal.id),
            }
        )


class CommercialProposalPdfDownloadView(APIView):
    def get(self, request, document_id):
        document = DocumentService.get_document(document_id)
        proposal = GeneratedCommercialProposal.objects.filter(
            document_id=document_id,
            is_current=True,
            status=SummaryStatus.COMPLETED,
        ).first()
        if not proposal or not proposal.commercial_json:
            raise ValidationServiceError(
                "No completed commercial proposal available to export.",
                code="commercial_proposal_not_ready",
            )
        pdf_bytes = CommercialProposalPdfService.render(proposal, document)
        filename = CommercialProposalPdfService.suggested_filename(document, proposal)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = len(pdf_bytes)
        return response
