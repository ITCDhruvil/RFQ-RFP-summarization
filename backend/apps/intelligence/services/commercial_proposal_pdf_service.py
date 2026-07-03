"""Generate commercial proposal PDF from structured JSON."""

from __future__ import annotations

import re
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from apps.documents.models import Document
from apps.intelligence.models import GeneratedCommercialProposal


def _xml_escape(text: str) -> str:
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


class CommercialProposalPdfService:
    @staticmethod
    def suggested_filename(document: Document, proposal: GeneratedCommercialProposal) -> str:
        stem = re.sub(r"[^\w\-]+", "_", document.original_filename.rsplit(".", 1)[0])
        stem = stem.strip("_")[:80] or "document"
        return f"{stem}_commercial_proposal_v{proposal.version}.pdf"

    @staticmethod
    def render(proposal: GeneratedCommercialProposal, document: Document) -> bytes:
        data = proposal.commercial_json or {}
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)
        base = getSampleStyleSheet()
        title_style = ParagraphStyle("CTitle", parent=base["Title"], fontSize=16, spaceAfter=12)
        heading_style = ParagraphStyle("CHeading", parent=base["Heading2"], fontSize=12, spaceBefore=12, spaceAfter=6)
        body_style = ParagraphStyle("CBody", parent=base["Normal"], fontSize=10, leading=14, alignment=TA_JUSTIFY)

        story: list = []
        story.append(Paragraph(_xml_escape("Commercial Proposal"), title_style))
        story.append(Paragraph(_xml_escape(document.original_filename), body_style))
        story.append(Spacer(1, 12))

        sections = [
            ("Commercial Cover Letter", (data.get("cover_letter") or {}).get("body")),
            ("Commercial Executive Summary", (data.get("executive_summary") or {}).get("body")),
            ("Pricing Summary", _format_pricing_summary(data.get("pricing_summary") or {})),
            ("Resource Pricing Table", None),
            ("Commercial Assumptions", _format_bullets(data.get("assumptions") or [])),
            ("Commercial Exclusions", _format_bullets(data.get("exclusions") or [])),
            ("Taxes & Duties", (data.get("taxes_and_duties") or {}).get("body")),
            ("Payment Terms", (data.get("payment_terms") or {}).get("body")),
            ("Price Validity", (data.get("price_validity") or {}).get("body")),
            ("Commercial Terms & Conditions", (data.get("commercial_terms") or {}).get("body")),
            ("Sign-Off", _format_sign_off(data.get("sign_off") or {})),
        ]

        for title, body in sections:
            story.append(Paragraph(_xml_escape(title), heading_style))
            if title == "Resource Pricing Table":
                story.extend(_pricing_table(data.get("resource_pricing_table") or [], body_style))
            elif body:
                story.append(Paragraph(_xml_escape(body), body_style))
            story.append(Spacer(1, 8))

        disclaimer = (data.get("_meta") or {}).get("disclaimer") or ""
        if disclaimer:
            story.append(Spacer(1, 16))
            story.append(Paragraph(_xml_escape(disclaimer), body_style))

        doc.build(story)
        return buffer.getvalue()


def _format_pricing_summary(summary: dict) -> str:
    if not summary:
        return ""
    parts = []
    for key, val in summary.items():
        if key == "currency_note":
            continue
        label = key.replace("_", " ").title()
        parts.append(f"{label}: {val}")
    return " | ".join(parts)


def _format_bullets(items: list) -> str:
    lines = []
    for item in items:
        if isinstance(item, dict):
            lines.append(f"• {item.get('text', '')}")
        else:
            lines.append(f"• {item}")
    return "\n".join(lines)


def _format_sign_off(sign_off: dict) -> str:
    parts = [sign_off.get("body") or ""]
    if sign_off.get("authorized_signatory"):
        parts.append(f"Authorized signatory: {sign_off['authorized_signatory']}")
    if sign_off.get("designation"):
        parts.append(f"Designation: {sign_off['designation']}")
    return "\n".join(p for p in parts if p)


def _pricing_table(rows: list, body_style) -> list:
    if not rows:
        return [Paragraph("No pricing lines.", body_style)]
    headers = ["Role", "Qty", "Unit/mo", "Monthly", "Annual", "w/ Margin"]
    table_data = [headers]
    for row in rows:
        table_data.append(
            [
                _clean(row.get("role_label")),
                str(row.get("quantity", "")),
                str(row.get("unit_cost_monthly", "")),
                str(row.get("monthly_cost", "")),
                str(row.get("annual_cost", "")),
                str(row.get("total_with_margin", "")),
            ]
        )
    table = Table(table_data, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return [table]
