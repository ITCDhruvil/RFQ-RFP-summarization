"""Cooperative cancellation for commercial proposal generation."""

from __future__ import annotations

from django.core.cache import cache

_CACHE_TTL = 3600
_ACTIVE_RUN_PREFIX = "commercial_cancel_active:"
_CANCEL_RUN_PREFIX = "commercial_cancel_run:"


class CommercialProposalCancelledError(Exception):
    """Raised when commercial proposal generation was stopped by the user."""


def _active_key(document_id: str) -> str:
    return f"{_ACTIVE_RUN_PREFIX}{document_id}"


def _cancel_key(document_id: str) -> str:
    return f"{_CANCEL_RUN_PREFIX}{document_id}"


def start_run(document_id: str, run_id: str) -> None:
    doc_id = str(document_id)
    cache.set(_active_key(doc_id), str(run_id), timeout=_CACHE_TTL)
    cache.delete(_cancel_key(doc_id))


def request_cancel(document_id: str, run_id: str | None = None) -> None:
    doc_id = str(document_id)
    target = str(run_id) if run_id else cache.get(_active_key(doc_id))
    cache.set(_cancel_key(doc_id), str(target or "*"), timeout=_CACHE_TTL)


def is_run_cancelled(document_id: str, run_id: str | None) -> bool:
    doc_id = str(document_id)
    cancelled = cache.get(_cancel_key(doc_id))
    if cancelled == "*":
        return True
    if cancelled and run_id:
        return str(cancelled) == str(run_id)
    return False
