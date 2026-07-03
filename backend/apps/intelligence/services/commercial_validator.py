"""Validate commercial proposal workbench before generation."""

from __future__ import annotations

from typing import Any


def validate_commercial_workbench(
    workbench: dict[str, Any],
    vendor_profile: dict[str, Any],
    *,
    strict: bool = True,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    pricing = workbench.get("pricing") or {}
    resource_lines = pricing.get("resource_lines") or []
    summary = pricing.get("summary") or {}
    terms = workbench.get("terms") or {}
    assumptions = workbench.get("assumptions") or []
    exclusions = workbench.get("exclusions") or []

    if not resource_lines:
        errors.append("At least one resource pricing line is required.")
    else:
        for line in resource_lines:
            role = line.get("role_label") or line.get("role_key") or "Line item"
            billing = str(line.get("billing_basis") or "monthly").lower()
            unit = float(line.get("unit_cost_monthly") or 0)
            if unit <= 0:
                errors.append(f"Missing or invalid unit price for {role}.")
            if int(line.get("quantity") or 0) <= 0:
                errors.append(f"Invalid quantity for {role}.")
            margin = float(
                line.get("margin_percent") if line.get("margin_percent") is not None else -1
            )
            if margin < 0:
                errors.append(f"Missing margin for {role}.")
            if billing not in {"monthly", "one_time", "annual"}:
                warnings.append(f"Unknown billing basis for {role}; treated as monthly.")

    payment_days = terms.get("payment_terms_days") or vendor_profile.get("payment_terms_days")
    if not payment_days:
        errors.append("Missing payment terms.")

    validity = terms.get("price_validity_days") or vendor_profile.get("price_validity_days")
    if not validity:
        errors.append("Missing price validity period.")

    gst = vendor_profile.get("default_gst_percent")
    if gst is None:
        warnings.append("GST / tax percentage not set; defaulting in pricing engine.")

    if not assumptions:
        warnings.append("No commercial assumptions documented.")
    if not exclusions:
        warnings.append("No commercial exclusions documented.")

    if not summary.get("total_with_tax") and resource_lines:
        warnings.append("Pricing summary totals not calculated; run pricing engine.")

    blocked = strict and bool(errors)
    return {
        "status": "FAILED" if blocked else "PASSED",
        "blocked": blocked,
        "errors": errors,
        "warnings": warnings,
        "blocking_reason": "; ".join(errors) if blocked else "",
    }
