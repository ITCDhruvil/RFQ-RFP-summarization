import logging

from celery import shared_task
from django.conf import settings

from apps.intelligence.services.orchestrator import IntelligenceOrchestrator
from apps.intelligence.services.commercial_proposal_orchestrator import (
    CommercialProposalOrchestrator,
)
from apps.intelligence.services.proposal_orchestrator import ProposalOrchestrator

logger = logging.getLogger("apps.celery")


@shared_task(
    bind=True,
    name="intelligence.generate_summary",
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
)
def generate_summary_task(self, document_id: str, regenerate: bool = False) -> dict:
    logger.info(
        "generate_summary_started document_id=%s regenerate=%s",
        document_id,
        regenerate,
    )
    try:
        result = IntelligenceOrchestrator.run(document_id, regenerate=regenerate)
        logger.info("generate_summary_completed document_id=%s", document_id)
        return result
    except Exception as exc:
        logger.exception("generate_summary_failed document_id=%s", document_id)
        if self.request.retries < settings.CELERY_TASK_MAX_RETRIES:
            raise self.retry(exc=exc, countdown=settings.CELERY_TASK_DEFAULT_RETRY_DELAY)
        raise


@shared_task(
    bind=True,
    name="intelligence.generate_proposal",
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
)
def generate_proposal_task(
    self,
    document_id: str,
    regenerate: bool = False,
    bidder_profile: dict | None = None,
) -> dict:
    logger.info(
        "generate_proposal_started document_id=%s regenerate=%s",
        document_id,
        regenerate,
    )
    try:
        result = ProposalOrchestrator.run(
            document_id,
            regenerate=regenerate,
            bidder_profile=bidder_profile,
        )
        logger.info("generate_proposal_completed document_id=%s", document_id)
        return result
    except Exception as exc:
        logger.exception("generate_proposal_failed document_id=%s", document_id)
        if self.request.retries < settings.CELERY_TASK_MAX_RETRIES:
            raise self.retry(
                exc=exc, countdown=settings.CELERY_TASK_DEFAULT_RETRY_DELAY
            )
        raise


@shared_task(
    bind=True,
    name="intelligence.generate_commercial_proposal",
    max_retries=settings.CELERY_TASK_MAX_RETRIES,
)
def generate_commercial_proposal_task(
    self,
    document_id: str,
    regenerate: bool = False,
    vendor_profile: dict | None = None,
) -> dict:
    logger.info(
        "generate_commercial_proposal_started document_id=%s regenerate=%s",
        document_id,
        regenerate,
    )
    try:
        result = CommercialProposalOrchestrator.run(
            document_id,
            regenerate=regenerate,
            vendor_profile=vendor_profile,
        )
        logger.info("generate_commercial_proposal_completed document_id=%s", document_id)
        return result
    except Exception as exc:
        logger.exception("generate_commercial_proposal_failed document_id=%s", document_id)
        if self.request.retries < settings.CELERY_TASK_MAX_RETRIES:
            raise self.retry(
                exc=exc, countdown=settings.CELERY_TASK_DEFAULT_RETRY_DELAY
            )
        raise
