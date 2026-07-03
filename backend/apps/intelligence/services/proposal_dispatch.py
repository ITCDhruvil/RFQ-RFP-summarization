"""Start or run proposal generation (sync dev path vs Celery)."""

from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.db import close_old_connections

from apps.intelligence.services.proposal_orchestrator import ProposalOrchestrator
from apps.intelligence.tasks import generate_proposal_task

logger = logging.getLogger(__name__)


def dispatch_proposal_generation(
    document_id,
    *,
    regenerate: bool,
    bidder_profile: dict | None = None,
) -> tuple[dict, int]:
    """
    Returns (response_body, http_status).
    Sync mode runs generation in a background thread (dev-friendly).
    """
    if getattr(settings, "INTELLIGENCE_SYNC_GENERATION", False):
        proposal = ProposalOrchestrator.begin_processing(
            str(document_id),
            regenerate=regenerate,
            bidder_profile=bidder_profile,
        )
        doc_id = str(document_id)
        profile = bidder_profile

        def _run_sync() -> None:
            close_old_connections()
            try:
                ProposalOrchestrator.run(
                    doc_id, regenerate=regenerate, bidder_profile=profile
                )
            except Exception:
                logger.exception(
                    "proposal_sync_failed document_id=%s regenerate=%s",
                    doc_id,
                    regenerate,
                )
            finally:
                close_old_connections()

        thread = threading.Thread(
            target=_run_sync,
            name=f"proposal-sync-{doc_id[:8]}",
            daemon=True,
        )
        thread.start()
        return {
            "message": "Proposal generation started.",
            "document_id": doc_id,
            "proposal_id": str(proposal.id),
            "regenerate": regenerate,
            "sync": True,
        }, 202

    proposal = ProposalOrchestrator.begin_processing(
        str(document_id),
        regenerate=regenerate,
        bidder_profile=bidder_profile,
    )
    async_result = generate_proposal_task.delay(
        str(document_id),
        regenerate=regenerate,
        bidder_profile=bidder_profile,
    )
    meta = dict(proposal.model_metadata or {})
    meta["celery_task_id"] = async_result.id
    proposal.model_metadata = meta
    proposal.save(update_fields=["model_metadata", "updated_at"])
    return {
        "message": "Proposal generation started.",
        "document_id": str(document_id),
        "proposal_id": str(proposal.id),
        "celery_task_id": async_result.id,
        "regenerate": regenerate,
        "sync": False,
    }, 202
