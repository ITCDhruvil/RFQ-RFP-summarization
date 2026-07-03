"""Cooperative cancellation for in-flight proposal generation."""

from __future__ import annotations

from django.core.cache import cache

_CACHE_TTL = 3600
_ACTIVE_RUN_PREFIX = "proposal_active_run:"
_CANCEL_RUN_PREFIX = "proposal_cancel_run:"
# Legacy boolean flag (kept for compatibility).
_LEGACY_CANCEL_PREFIX = "proposal_cancel:"


class ProposalCancelledError(Exception):
    """Raised when proposal generation was stopped by the user."""


def _active_key(document_id: str) -> str:
    return f"{_ACTIVE_RUN_PREFIX}{document_id}"


def _cancel_key(document_id: str) -> str:
    return f"{_CANCEL_RUN_PREFIX}{document_id}"


def _legacy_key(document_id: str) -> str:
    return f"{_LEGACY_CANCEL_PREFIX}{document_id}"


def start_run(document_id: str, run_id: str) -> None:
    """Mark a new generation run; clears any prior cancel flag for this document."""
    doc_id = str(document_id)
    cache.set(_active_key(doc_id), str(run_id), timeout=_CACHE_TTL)
    cache.delete(_cancel_key(doc_id))
    cache.delete(_legacy_key(doc_id))


def request_cancel(document_id: str, run_id: str | None = None) -> None:
    """Request cancellation for the active run (or a specific run id)."""
    doc_id = str(document_id)
    target = str(run_id) if run_id else cache.get(_active_key(doc_id))
    if target:
        cache.set(_cancel_key(doc_id), str(target), timeout=_CACHE_TTL)
    else:
        cache.set(_cancel_key(doc_id), "*", timeout=_CACHE_TTL)
    cache.set(_legacy_key(doc_id), True, timeout=_CACHE_TTL)


def is_run_cancelled(document_id: str, run_id: str | None) -> bool:
    doc_id = str(document_id)
    cancelled = cache.get(_cancel_key(doc_id))
    if cancelled == "*":
        return True
    if cancelled and run_id:
        return str(cancelled) == str(run_id)
    return bool(cache.get(_legacy_key(doc_id)))


def clear_cancel(document_id: str) -> None:
    doc_id = str(document_id)
    cache.delete(_active_key(doc_id))
    cache.delete(_cancel_key(doc_id))
    cache.delete(_legacy_key(doc_id))
