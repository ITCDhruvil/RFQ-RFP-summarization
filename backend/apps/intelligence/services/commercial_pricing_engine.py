"""Deterministic commercial pricing engine — no LLM."""

from __future__ import annotations

from typing import Any

from apps.intelligence.services.commercial_schemas import ResourcePricingLine


def _line_total_monthly(quantity: int, unit_cost: float) -> float:
    return round(quantity * unit_cost, 2)


def _apply_margin(amount: float, margin_percent: float) -> float:
    return round(amount * (1 + margin_percent / 100.0), 2)


def build_resource_lines(
    requirements: dict[str, Any],
    vendor_profile: dict[str, Any],
    questionnaire_answers: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build editable resource pricing lines from requirements and user inputs."""
    answers = questionnaire_answers or {}
    margin = float(
        answers.get("desired_margin_percent")
        or vendor_profile.get("default_margin_percent")
        or 0
    )
    gst = float(
        answers.get("default_gst_percent") or vendor_profile.get("default_gst_percent") or 0
    )

    def rate_for(role_key: str) -> float:
        if answers.get(f"{role_key}_rate"):
            return float(answers[f"{role_key}_rate"])
        if role_key == "security_guard" and answers.get("security_guard_rate"):
            return float(answers["security_guard_rate"])
        if role_key == "supervisor" and answers.get("supervisor_rate"):
            return float(answers["supervisor_rate"])
        for row in vendor_profile.get("resource_rates") or []:
            if isinstance(row, dict) and row.get("role_key") == role_key:
                return float(row.get("unit_cost_monthly") or 0)
        return 0.0

    resource_count = int(requirements.get("resource_count") or 0)
    lines: list[dict[str, Any]] = []
    profile_rates = {
        str(r.get("role_key")): r
        for r in (vendor_profile.get("resource_rates") or [])
        if isinstance(r, dict) and r.get("role_key")
    }

    if resource_count > 0:
        guard_row = profile_rates.get("security_guard") or {}
        supervisor_row = profile_rates.get("supervisor") or {}
        guard_qty = int(guard_row.get("quantity") or max(resource_count - max(resource_count // 10, 1), 1))
        supervisor_qty = int(supervisor_row.get("quantity") or max(resource_count // 10, 1))
        lines.append(
            {
                "role_key": "security_guard",
                "role_label": str(guard_row.get("role_label") or "Security Guard"),
                "line_type": "personnel",
                "billing_basis": "monthly",
                "quantity": guard_qty,
                "unit_cost_monthly": float(guard_row.get("unit_cost_monthly") or rate_for("security_guard")),
                "margin_percent": float(guard_row.get("margin_percent") or margin),
                "gst_percent": float(guard_row.get("gst_percent") or gst),
            }
        )
        lines.append(
            {
                "role_key": "supervisor",
                "role_label": str(supervisor_row.get("role_label") or "Supervisor"),
                "line_type": "personnel",
                "billing_basis": "monthly",
                "quantity": supervisor_qty,
                "unit_cost_monthly": float(supervisor_row.get("unit_cost_monthly") or rate_for("supervisor")),
                "margin_percent": float(supervisor_row.get("margin_percent") or margin),
                "gst_percent": float(supervisor_row.get("gst_percent") or gst),
            }
        )

    for row in vendor_profile.get("resource_rates") or []:
        if not isinstance(row, dict):
            continue
        role_key = str(row.get("role_key") or "")
        if role_key in {"security_guard", "supervisor"} and resource_count > 0:
            continue
        if not role_key:
            continue
        lines.append(
            {
                "role_key": role_key,
                "role_label": str(row.get("role_label") or role_key.replace("_", " ").title()),
                "line_type": str(row.get("line_type") or "personnel"),
                "billing_basis": str(row.get("billing_basis") or "monthly"),
                "quantity": int(row.get("quantity") or 1),
                "unit_cost_monthly": float(row.get("unit_cost_monthly") or 0),
                "margin_percent": float(row.get("margin_percent") or margin),
                "gst_percent": float(row.get("gst_percent") or gst),
            }
        )

    return lines


def calculate_pricing(resource_lines: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate pricing summary from resource lines."""
    computed: list[ResourcePricingLine] = []
    subtotal_monthly = 0.0
    subtotal_annual = 0.0
    total_with_margin = 0.0
    total_with_tax = 0.0

    for row in resource_lines:
        qty = int(row.get("quantity") or 0)
        unit = float(row.get("unit_cost_monthly") or 0)
        margin = float(row.get("margin_percent") or 0)
        gst = float(row.get("gst_percent") or 0)
        billing = str(row.get("billing_basis") or "monthly").lower()

        if billing == "one_time":
            monthly = 0.0
            annual = round(qty * unit, 2)
        elif billing == "annual":
            annual = round(qty * unit, 2)
            monthly = round(annual / 12, 2)
        else:
            monthly = _line_total_monthly(qty, unit)
            annual = round(monthly * 12, 2)

        with_margin = _apply_margin(annual, margin)
        with_tax = round(with_margin * (1 + gst / 100.0), 2)
        if billing != "one_time":
            subtotal_monthly += monthly
        subtotal_annual += annual
        total_with_margin += with_margin
        total_with_tax += with_tax
        computed.append(
            ResourcePricingLine(
                role_key=str(row.get("role_key") or ""),
                role_label=str(row.get("role_label") or ""),
                line_type=str(row.get("line_type") or "personnel"),
                billing_basis=billing,
                quantity=qty,
                unit_cost_monthly=unit,
                margin_percent=margin,
                gst_percent=gst,
                monthly_cost=monthly,
                annual_cost=annual,
                total_with_margin=with_margin,
            )
        )

    return {
        "resource_lines": computed,
        "summary": {
            "subtotal_monthly": round(subtotal_monthly, 2),
            "subtotal_annual": round(subtotal_annual, 2),
            "total_before_tax": round(total_with_margin, 2),
            "total_with_tax": round(total_with_tax, 2),
            "currency_note": "All figures from pricing engine; narrative sections must reference these values only.",
        },
    }
