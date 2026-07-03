"""Start or run commercial proposal generation (sync dev path vs Celery)."""

from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.db import close_old_connections

from apps.intelligence.services.commercial_proposal_orchestrator import (
    CommercialProposalOrchestrator,
)
from apps.intelligence.tasks import generate_commercial_proposal_task

logger = logging.getLogger(__name__)


def dispatch_commercial_proposal_generation(
    document_id,
    *,
    regenerate: bool,
    vendor_profile: dict | None = None,
) -> tuple[dict, int]:
    if getattr(settings, "INTELLIGENCE_SYNC_GENERATION", False):
        proposal = CommercialProposalOrchestrator.begin_processing(
            str(document_id),
            regenerate=regenerate,
            vendor_profile=vendor_profile,
        )
        doc_id = str(document_id)
        profile = vendor_profile

        def _run_sync() -> None:
            close_old_connections()
            try:
                CommercialProposalOrchestrator.run(
                    doc_id, regenerate=regenerate, vendor_profile=profile
                )
            except Exception:
                logger.exception(
                    "commercial_proposal_sync_failed document_id=%s", doc_id
                )
            finally:
                close_old_connections()

        threading.Thread(
            target=_run_sync,
            name=f"commercial-proposal-sync-{doc_id[:8]}",
            daemon=True,
        ).start()
        return {
            "message": "Commercial proposal generation started.",
            "document_id": doc_id,
            "commercial_proposal_id": str(proposal.id),
            "regenerate": regenerate,
            "sync": True,
        }, 202

    proposal = CommercialProposalOrchestrator.begin_processing(
        str(document_id),
        regenerate=regenerate,
        vendor_profile=vendor_profile,
    )
    async_result = generate_commercial_proposal_task.delay(
        str(document_id),
        regenerate=regenerate,
        vendor_profile=vendor_profile,
    )
    meta = dict(proposal.model_metadata or {})
    meta["celery_task_id"] = async_result.id
    proposal.model_metadata = meta
    proposal.save(update_fields=["model_metadata", "updated_at"])
    return {
        "message": "Commercial proposal generation started.",
        "document_id": str(document_id),
        "commercial_proposal_id": str(proposal.id),
        "celery_task_id": async_result.id,
        "regenerate": regenerate,
        "sync": False,
    }, 202
