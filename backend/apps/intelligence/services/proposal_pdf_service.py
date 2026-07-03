"""Generate a structured technical proposal PDF from proposal JSON."""

from __future__ import annotations

import re
from datetime import datetime
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.documents.models import Document
from apps.intelligence.models import GeneratedProposal

COMPLIANCE_LABELS = {
    "compliant": "Compliant",
    "fully": "Compliant",
    "partial": "Partial",
    "gap": "Gap",
    "planned": "Planned",
    "na": "N/A",
}


def _xml_escape(text: str) -> str:
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


class ProposalPdfService:
    @staticmethod
    def suggested_filename(document: Document, proposal: GeneratedProposal) -> str:
        stem = re.sub(r"[^\w\-]+", "_", document.original_filename.rsplit(".", 1)[0])
        stem = stem.strip("_")[:80] or "document"
        return f"{stem}_technical_proposal_v{proposal.version}.pdf"

    @staticmethod
    def _build_styles(base):
        return {
            "title": ParagraphStyle(
                "PropTitle",
                parent=base["Title"],
                fontSize=18,
                spaceAfter=12,
                textColor=colors.HexColor("#0f172a"),
            ),
            "subtitle": ParagraphStyle(
                "PropSubtitle",
                parent=base["Normal"],
                fontSize=11,
                textColor=colors.HexColor("#64748b"),
                spaceAfter=16,
            ),
            "heading": ParagraphStyle(
                "PropHeading",
                parent=base["Heading2"],
                fontSize=13,
                spaceBefore=14,
                spaceAfter=8,
                textColor=colors.HexColor("#1e293b"),
            ),
            "body": ParagraphStyle(
                "PropBody",
                parent=base["Normal"],
                fontSize=10,
                leading=14,
                alignment=TA_JUSTIFY,
                spaceAfter=8,
            ),
            "disclaimer": ParagraphStyle(
                "PropDisclaimer",
                parent=base["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#b45309"),
                backColor=colors.HexColor("#fffbeb"),
                borderPadding=6,
                spaceAfter=12,
            ),
            "table_header": ParagraphStyle(
                "PropTableHeader",
                parent=base["Normal"],
                fontSize=9,
                textColor=colors.white,
            ),
            "table_cell": ParagraphStyle(
                "PropTableCell",
                parent=base["Normal"],
                fontSize=8,
                leading=11,
            ),
        }

    @staticmethod
    def _para(text: str, style: ParagraphStyle) -> Paragraph:
        return Paragraph(_xml_escape(_clean_text(text)), style)

    @staticmethod
    def render(proposal: GeneratedProposal, document: Document) -> bytes:
        data = proposal.proposal_json or {}
        meta = data.get("_meta") or {}
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.85 * inch,
            rightMargin=0.85 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Technical Proposal — {document.original_filename}",
        )

        styles = ProposalPdfService._build_styles(getSampleStyleSheet())
        story: list = []

        company = (proposal.bidder_profile_snapshot or {}).get("company_name") or ""
        story.append(
            ProposalPdfService._para("Technical Proposal (Draft)", styles["title"])
        )
        story.append(
            ProposalPdfService._para(
                f"In response to: {_clean_text(document.original_filename)}",
                styles["subtitle"],
            )
        )
        if company:
            story.append(
                ProposalPdfService._para(f"Prepared by: {company}", styles["subtitle"])
            )
        story.append(
            ProposalPdfService._para(
                f"Generated {datetime.now().strftime('%d %B %Y')} · Version {proposal.version}",
                styles["subtitle"],
            )
        )
        story.append(
            ProposalPdfService._para(
                meta.get("disclaimer")
                or "AI-generated draft for internal review only. Verify all facts before submission.",
                styles["disclaimer"],
            )
        )
        story.append(Spacer(1, 0.15 * inch))

        def _section(title: str, text: str | None) -> None:
            if not _clean_text(text):
                return
            story.append(ProposalPdfService._para(title, styles["heading"]))
            story.append(ProposalPdfService._para(text, styles["body"]))

        _section("Cover Letter", (data.get("cover_letter") or {}).get("text"))
        _section("Executive Summary", (data.get("executive_summary") or {}).get("text"))
        _section("Company Overview", (data.get("company_overview") or {}).get("text"))
        _section(
            "Understanding of Requirements",
            (data.get("understanding_of_requirements") or {}).get("text"),
        )

        why = data.get("why_choose_us") or {}
        diffs = why.get("differentiators") or []
        if diffs:
            story.append(ProposalPdfService._para("Why Choose Us", styles["heading"]))
            for d in diffs:
                if isinstance(d, dict):
                    story.append(
                        ProposalPdfService._para(
                            _clean_text(d.get("claim")), styles["body"]
                        )
                    )

        _section("Staffing Approach", (data.get("staffing_approach") or {}).get("text"))
        _section("Training Framework", (data.get("training_framework") or {}).get("text"))

        approach = data.get("technical_approach") or {}
        sections = approach.get("sections") or []
        if sections:
            story.append(ProposalPdfService._para("Technical Approach", styles["heading"]))
            for sec in sections:
                if not isinstance(sec, dict):
                    continue
                title = _clean_text(sec.get("title"))
                content = _clean_text(sec.get("content"))
                if title:
                    story.append(
                        ProposalPdfService._para(title, styles["heading"])
                    )
                if content:
                    story.append(ProposalPdfService._para(content, styles["body"]))

        matrix = data.get("compliance_matrix") or []
        if matrix:
            story.append(Spacer(1, 0.1 * inch))
            story.append(
                ProposalPdfService._para("Compliance Matrix", styles["heading"])
            )
            table_data = [
                [
                    ProposalPdfService._para("Ref", styles["table_header"]),
                    ProposalPdfService._para("Requirement", styles["table_header"]),
                    ProposalPdfService._para("Response", styles["table_header"]),
                    ProposalPdfService._para("Status", styles["table_header"]),
                ]
            ]
            for row in matrix[:40]:
                if not isinstance(row, dict):
                    continue
                status = COMPLIANCE_LABELS.get(
                    str(
                        row.get("compliance_status") or row.get("compliance") or "planned"
                    ).lower(),
                    "Planned",
                )
                response = row.get("vendor_response") or row.get("response") or ""
                table_data.append(
                    [
                        ProposalPdfService._para(
                            row.get("requirement_ref") or "", styles["table_cell"]
                        ),
                        ProposalPdfService._para(
                            row.get("requirement_text") or "", styles["table_cell"]
                        ),
                        ProposalPdfService._para(response, styles["table_cell"]),
                        ProposalPdfService._para(status, styles["table_cell"]),
                    ]
                )
            table = Table(
                table_data,
                colWidths=[0.55 * inch, 2.0 * inch, 2.4 * inch, 0.85 * inch],
                repeatRows=1,
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ]
                )
            )
            story.append(table)

        plan = data.get("transition_plan") or data.get("implementation_plan") or {}
        phases = plan.get("phases") or []
        if phases:
            story.append(Spacer(1, 0.1 * inch))
            story.append(
                ProposalPdfService._para("Implementation Plan", styles["heading"])
            )
            for phase in phases:
                if not isinstance(phase, dict):
                    continue
                name = _clean_text(phase.get("name"))
                duration = _clean_text(phase.get("duration"))
                deliverables = phase.get("deliverables") or []
                line = name
                if duration:
                    line += f" ({duration})"
                story.append(ProposalPdfService._para(line, styles["body"]))
                for d in deliverables:
                    story.append(
                        ProposalPdfService._para(f"• {_clean_text(d)}", styles["body"])
                    )

        team = data.get("team_and_staffing") or {}
        roles = team.get("roles") or []
        if roles:
            story.append(Spacer(1, 0.1 * inch))
            story.append(
                ProposalPdfService._para("Team & Staffing", styles["heading"])
            )
            for role in roles:
                if not isinstance(role, dict):
                    continue
                title = _clean_text(role.get("title"))
                resp = _clean_text(role.get("responsibilities"))
                ref = _clean_text(role.get("profile_ref"))
                block = f"{title}: {resp}"
                if ref:
                    block += f" ({ref})"
                story.append(ProposalPdfService._para(block, styles["body"]))

        risks = data.get("operational_risks") or data.get("risks_and_mitigations") or []
        if risks:
            story.append(Spacer(1, 0.1 * inch))
            story.append(
                ProposalPdfService._para("Operational Risks", styles["heading"])
            )
            for item in risks:
                if not isinstance(item, dict):
                    continue
                risk = _clean_text(item.get("risk"))
                mit = _clean_text(item.get("mitigation"))
                likelihood = _clean_text(item.get("likelihood"))
                impact = _clean_text(item.get("impact"))
                owner = _clean_text(item.get("owner"))
                meta_line = " / ".join(
                    x for x in (f"L:{likelihood}", f"I:{impact}", f"Owner:{owner}") if x
                )
                story.append(
                    ProposalPdfService._para(f"Risk: {risk}", styles["body"])
                )
                if meta_line:
                    story.append(ProposalPdfService._para(meta_line, styles["body"]))
                story.append(
                    ProposalPdfService._para(f"Mitigation: {mit}", styles["body"])
                )

        gaps = data.get("gaps_and_placeholders") or []
        if gaps:
            story.append(Spacer(1, 0.1 * inch))
            story.append(
                ProposalPdfService._para("Items Requiring Completion", styles["heading"])
            )
            for gap in gaps:
                if not isinstance(gap, dict):
                    continue
                field = _clean_text(gap.get("field"))
                reason = _clean_text(gap.get("reason"))
                story.append(
                    ProposalPdfService._para(f"• {field} ({reason})", styles["body"])
                )

        doc.build(story)
        return buffer.getvalue()
