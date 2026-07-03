"""Backfill commercial narrative sections when LLM output is thin."""

from __future__ import annotations

from typing import Any


def _body_len(block: Any) -> int:
    if not isinstance(block, dict):
        return 0
    return len(str(block.get("body") or "").strip())


def enrich_commercial_narrative(
    narrative: dict[str, Any],
    *,
    document_name: str,
    vendor_profile: dict[str, Any],
    pricing_summary: dict[str, Any],
    terms: dict[str, Any],
) -> dict[str, Any]:
    company = (
        str(vendor_profile.get("company_legal_name") or "").strip()
        or "Our organization"
    )
    currency = str(terms.get("currency") or vendor_profile.get("currency") or "INR")
    payment_days = terms.get("payment_terms_days") or vendor_profile.get("payment_terms_days") or 45
    validity_days = terms.get("price_validity_days") or vendor_profile.get("price_validity_days") or 90
    annual = pricing_summary.get("total_annual_with_tax") or pricing_summary.get(
        "total_annual_with_margin"
    )
    monthly = pricing_summary.get("total_monthly_with_tax") or pricing_summary.get(
        "total_monthly_with_margin"
    )
    price_ref = ""
    if annual:
        price_ref = f" The all-in annual commercial value is {currency} {annual:,.2f} (inclusive of margin and GST as computed)."
    elif monthly:
        price_ref = f" The indicative monthly commercial value is {currency} {monthly:,.2f}."

    if _body_len(narrative.get("cover_letter")) < 300:
        narrative["cover_letter"] = {
            "body": (
                f"Dear Evaluation Committee,\n\n"
                f"We are pleased to submit the commercial proposal of {company} for "
                f"\"{document_name}\". Our pricing has been prepared in accordance with "
                f"the RFP commercial requirements and reflects the resource deployment "
                f"schedule detailed in the accompanying pricing tables.{price_ref}\n\n"
                f"We confirm adherence to the stated payment terms, price validity, and "
                f"tax treatment described in this volume. We remain available to clarify "
                f"any commercial queries during evaluation.\n\n"
                f"Respectfully submitted,\n"
                f"{vendor_profile.get('authorized_signatory') or 'Authorized Signatory'}\n"
                f"{vendor_profile.get('signatory_designation') or company}"
            )
        }

    if _body_len(narrative.get("executive_summary")) < 200:
        narrative["executive_summary"] = {
            "body": (
                f"{company} offers a transparent, line-item commercial structure aligned "
                f"to the RFP scope. Pricing is built from role-level unit rates, agreed "
                f"margins, and applicable GST.{price_ref} "
                f"Payment is proposed on Net {payment_days} days from invoice acceptance. "
                f"Prices remain valid for {validity_days} days from submission."
            )
        }

    if _body_len(narrative.get("payment_terms")) < 120:
        narrative["payment_terms"] = {
            "body": (
                f"Invoices will be submitted monthly in arrears. Payment terms are Net "
                f"{payment_days} days from receipt of a valid tax invoice and supporting "
                f"attendance/SLA reports. Disputed amounts will be resolved through the "
                f"governance process without withholding undisputed portions."
            )
        }

    if _body_len(narrative.get("price_validity")) < 80:
        narrative["price_validity"] = {
            "body": (
                f"Our commercial offer remains valid for {validity_days} days from the "
                f"proposal submission date. Beyond this period, rates may be revised to "
                f"reflect statutory wage or tax changes."
            )
        }

    signatory = narrative.get("sign_off")
    if not isinstance(signatory, dict):
        signatory = {}
    if not signatory.get("authorized_signatory"):
        signatory["authorized_signatory"] = vendor_profile.get("authorized_signatory") or ""
    if not signatory.get("designation"):
        signatory["designation"] = vendor_profile.get("signatory_designation") or ""
    narrative["sign_off"] = signatory

    return narrative
