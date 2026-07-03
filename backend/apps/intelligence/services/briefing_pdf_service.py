"""Generate a structured procurement briefing PDF from summary JSON."""

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
from apps.intelligence.models import GeneratedSummary

NOT_FOUND = "Not found in document."

CHECKLIST_GROUP_LABELS: dict[str, str] = {
    "core_proposals": "Proposal volumes",
    "commercial_pricing": "Commercial & pricing documents",
    "forms_compliance": "Forms, annexures & compliance",
    "guarantees_bonds": "Guarantees & bonds",
    "team_references": "Team credentials & references",
    "other": "Other mandatory items",
}

CHECKLIST_GROUP_ORDER = [
    "core_proposals",
    "commercial_pricing",
    "forms_compliance",
    "guarantees_bonds",
    "team_references",
    "other",
]

SIGNAL_PRIORITY_ORDER = ("high", "medium", "low")
SIGNAL_PRIORITY_LABELS = {
    "high": "High priority",
    "medium": "Medium priority",
    "low": "Low priority",
}
SIGNAL_PRIORITY_HEADER_BG = {
    "high": colors.HexColor("#fee2e2"),
    "medium": colors.HexColor("#fef3c7"),
    "low": colors.HexColor("#f1f5f9"),
}
SIGNAL_PRIORITY_HEADER_FG = {
    "high": colors.HexColor("#991b1b"),
    "medium": colors.HexColor("#92400e"),
    "low": colors.HexColor("#475569"),
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


def _has_text(value: Any) -> bool:
    return bool(_clean_text(value))


class BriefingPdfService:
    @staticmethod
    def suggested_filename_for_variant(
        document: Document, summary: GeneratedSummary, *, variant: str
    ) -> str:
        stem = re.sub(r"[^\w\-]+", "_", document.original_filename.rsplit(".", 1)[0])
        stem = stem.strip("_")[:80] or "document"
        label = "executive_summary" if variant == "executive" else "briefing"
        return f"{stem}_procurement_{label}_v{summary.version}.pdf"

    @staticmethod
    def render(
        summary: GeneratedSummary,
        document: Document,
        *,
        variant: str = "full",
    ) -> bytes:
        data = summary.summary_json or {}
        meta = data.get("_meta") or {}
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=0.85 * inch,
            rightMargin=0.85 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
            title=f"Procurement Briefing — {document.original_filename}",
        )

        styles = BriefingPdfService._build_styles(getSampleStyleSheet())
        story: list = []

        story.extend(
            BriefingPdfService._cover_block(
                document, summary, meta, styles
            )
        )

        BriefingPdfService._add_executive_summary(story, data, styles)

        if variant == "executive":
            BriefingPdfService._add_signals(story, data, styles)
            story.append(Spacer(1, 0.15 * inch))
            story.append(
                Paragraph(
                    "<i>Executive edition — use the full report download for "
                    "deadlines, scope, commercial terms, risks, and checklist.</i>",
                    styles["subtitle"],
                )
            )
            doc.build(story)
            return buffer.getvalue()

        BriefingPdfService._add_signals(story, data, styles)
        BriefingPdfService._add_strategy_insights(story, data, styles)
        BriefingPdfService._add_list_section(
            story, "Key Requirements", data.get("key_requirements"), styles
        )
        BriefingPdfService._add_deadlines(story, data, styles)
        BriefingPdfService._add_text_section(
            story, "Technical Scope", data.get("technical_scope"), styles
        )
        BriefingPdfService._add_text_section(
            story, "Commercial Terms", data.get("commercial_terms"), styles
        )
        BriefingPdfService._add_risks(story, data, styles)
        BriefingPdfService._add_checklist(story, data, styles)

        story.append(Spacer(1, 0.25 * inch))
        story.append(
            Paragraph(
                "<font size='8' color='#64748b'>"
                "AI-generated procurement intelligence. Verify figures and dates "
                "against the source tender before bid decisions."
                "</font>",
                styles["body"],
            )
        )

        doc.build(story)
        return buffer.getvalue()

    @staticmethod
    def _build_styles(base) -> dict[str, ParagraphStyle]:
        return {
            "title": ParagraphStyle(
                "BriefTitle",
                parent=base["Heading1"],
                fontSize=20,
                leading=24,
                spaceAfter=6,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#0f172a"),
            ),
            "subtitle": ParagraphStyle(
                "BriefSubtitle",
                parent=base["Normal"],
                fontSize=10,
                leading=14,
                textColor=colors.HexColor("#475569"),
                spaceAfter=4,
                alignment=TA_LEFT,
            ),
            "section": ParagraphStyle(
                "SectionHeading",
                parent=base["Heading2"],
                fontSize=13,
                leading=16,
                spaceBefore=16,
                spaceAfter=10,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#1e40af"),
            ),
            "body": ParagraphStyle(
                "Body",
                parent=base["Normal"],
                fontSize=10,
                leading=15,
                alignment=TA_JUSTIFY,
                textColor=colors.HexColor("#0f172a"),
            ),
            "body_left": ParagraphStyle(
                "BodyLeft",
                parent=base["Normal"],
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#0f172a"),
            ),
            "empty": ParagraphStyle(
                "Empty",
                parent=base["Normal"],
                fontSize=10,
                leading=14,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#64748b"),
                fontName="Helvetica-Oblique",
            ),
            "check_group": ParagraphStyle(
                "CheckGroup",
                parent=base["Normal"],
                fontSize=10,
                leading=13,
                spaceBefore=8,
                spaceAfter=4,
                alignment=TA_LEFT,
                textColor=colors.HexColor("#1e293b"),
                fontName="Helvetica-Bold",
            ),
        }

    @staticmethod
    def _cover_block(
        document: Document,
        summary: GeneratedSummary,
        meta: dict,
        styles: dict[str, ParagraphStyle],
    ) -> list:
        generated_at = meta.get("generated_at") or summary.completed_at
        if generated_at and hasattr(generated_at, "strftime"):
            gen_label = generated_at.strftime("%d %b %Y %H:%M UTC")
        elif generated_at:
            try:
                gen_label = datetime.fromisoformat(
                    str(generated_at).replace("Z", "+00:00")
                ).strftime("%d %b %Y %H:%M")
            except ValueError:
                gen_label = str(generated_at)[:19]
        else:
            gen_label = "—"

        block = [
            Paragraph("Procurement Intelligence Briefing", styles["title"]),
            Paragraph(_xml_escape(document.original_filename), styles["subtitle"]),
            Paragraph(
                f"Report version {summary.version} · Generated {gen_label}",
                styles["subtitle"],
            ),
        ]
        if meta.get("prompt_version"):
            block.append(
                Paragraph(
                    f"Analysis prompt v{_xml_escape(str(meta['prompt_version']))}",
                    styles["subtitle"],
                )
            )
        block.append(Spacer(1, 0.22 * inch))
        return block

    @staticmethod
    def _section_heading(story: list, title: str, styles: dict) -> None:
        story.append(Paragraph(title, styles["section"]))

    @staticmethod
    def _add_paragraphs_justified(
        story: list, text: str, styles: dict[str, ParagraphStyle]
    ) -> None:
        for para in re.split(r"\n\s*\n", text):
            chunk = _clean_text(para)
            if chunk:
                story.append(Paragraph(_xml_escape(chunk), styles["body"]))
                story.append(Spacer(1, 0.07 * inch))

    @staticmethod
    def _add_executive_summary(story: list, data: dict, styles: dict) -> None:
        BriefingPdfService._section_heading(story, "Executive Summary", styles)
        text = _clean_text((data.get("executive_summary") or {}).get("text"))
        if text:
            BriefingPdfService._add_paragraphs_justified(story, text, styles)
        else:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))

    @staticmethod
    def _collect_signals(data: dict) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {p: [] for p in SIGNAL_PRIORITY_ORDER}
        for raw in data.get("procurement_critical_signals") or []:
            if not isinstance(raw, dict):
                continue
            signal = _clean_text(raw.get("signal"))
            if not signal:
                continue
            priority = _clean_text(raw.get("priority")).lower() or "medium"
            if priority not in grouped:
                priority = "medium"
            grouped[priority].append(signal)
        return grouped

    @staticmethod
    def _add_signals(story: list, data: dict, styles: dict) -> None:
        BriefingPdfService._section_heading(
            story, "Procurement Critical Signals", styles
        )
        grouped = BriefingPdfService._collect_signals(data)
        total = sum(len(v) for v in grouped.values())
        if total == 0:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))
            return

        cell_style = ParagraphStyle(
            "SignalCell",
            parent=styles["body"],
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
        )
        num_style = ParagraphStyle(
            "SignalNum",
            parent=styles["body_left"],
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
        )

        for priority in SIGNAL_PRIORITY_ORDER:
            signals = grouped.get(priority) or []
            if not signals:
                continue

            label = SIGNAL_PRIORITY_LABELS[priority]
            count = len(signals)
            header = Table(
                [[Paragraph(f"{label} ({count})", styles["check_group"])]],
                colWidths=[6.3 * inch],
            )
            header.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), SIGNAL_PRIORITY_HEADER_BG[priority]),
                        ("TEXTCOLOR", (0, 0), (-1, -1), SIGNAL_PRIORITY_HEADER_FG[priority]),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(header)

            rows = [["#", "Signal"]]
            for idx, signal in enumerate(signals, start=1):
                rows.append(
                    [
                        Paragraph(str(idx), num_style),
                        Paragraph(_xml_escape(signal), cell_style),
                    ]
                )
            table = Table(rows, colWidths=[0.45 * inch, 5.85 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ]
                )
            )
            story.append(table)
            story.append(Spacer(1, 0.12 * inch))

    @staticmethod
    def _add_strategy_insights(story: list, data: dict, styles: dict) -> None:
        BriefingPdfService._section_heading(
            story, "Procurement Strategy Insights", styles
        )
        insights = [
            raw
            for raw in (data.get("procurement_strategy_insights") or [])
            if isinstance(raw, dict) and _has_text(raw.get("insight"))
        ]
        if not insights:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))
            return

        rows = [["#", "Insight", "Implication"]]
        cell = ParagraphStyle(
            "InsightCell",
            parent=styles["body"],
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
        )
        for idx, raw in enumerate(insights, start=1):
            rows.append(
                [
                    str(idx),
                    Paragraph(_xml_escape(_clean_text(raw.get("insight"))), cell),
                    Paragraph(
                        _xml_escape(_clean_text(raw.get("implication")) or "—"),
                        cell,
                    ),
                ]
            )
        table = Table(
            rows, colWidths=[0.4 * inch, 3.0 * inch, 2.9 * inch], repeatRows=1
        )
        table.setStyle(BriefingPdfService._standard_table_style())
        story.append(table)

    @staticmethod
    def _add_list_section(
        story: list,
        title: str,
        items_raw: list | None,
        styles: dict,
        *,
        text_key: str = "text",
    ) -> None:
        BriefingPdfService._section_heading(story, title, styles)
        items = [
            raw
            for raw in (items_raw or [])
            if isinstance(raw, dict)
            and _has_text(raw.get(text_key) or raw.get("item"))
        ]
        if not items:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))
            return

        cell = ParagraphStyle(
            "ListCell",
            parent=styles["body"],
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
        )
        rows = [["#", "Requirement"]]
        for idx, raw in enumerate(items, start=1):
            rows.append(
                [
                    str(idx),
                    Paragraph(
                        _xml_escape(_clean_text(raw.get(text_key) or raw.get("item"))),
                        cell,
                    ),
                ]
            )
        table = Table(rows, colWidths=[0.4 * inch, 5.9 * inch], repeatRows=1)
        table.setStyle(BriefingPdfService._standard_table_style())
        story.append(table)

    @staticmethod
    def _add_deadlines(story: list, data: dict, styles: dict) -> None:
        BriefingPdfService._section_heading(story, "Important Deadlines", styles)
        deadlines = [
            raw
            for raw in (data.get("important_deadlines") or [])
            if isinstance(raw, dict)
            and (_has_text(raw.get("text")) or _has_text(raw.get("item")) or _has_text(raw.get("date")))
        ]
        if not deadlines:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))
            return

        cell = ParagraphStyle(
            "DeadlineCell",
            parent=styles["body"],
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
        )
        rows = [["Milestone", "Date / detail"]]
        for raw in deadlines:
            label = _clean_text(raw.get("text") or raw.get("item")) or "—"
            date_val = _clean_text(raw.get("date")) or "—"
            rows.append(
                [
                    Paragraph(_xml_escape(label), cell),
                    Paragraph(_xml_escape(date_val), cell),
                ]
            )
        table = Table(rows, colWidths=[2.5 * inch, 3.8 * inch], repeatRows=1)
        table.setStyle(BriefingPdfService._standard_table_style())
        story.append(table)

    @staticmethod
    def _add_text_section(
        story: list,
        title: str,
        block: dict | None,
        styles: dict,
    ) -> None:
        BriefingPdfService._section_heading(story, title, styles)
        text = _clean_text((block or {}).get("text")) if isinstance(block, dict) else ""
        if text:
            BriefingPdfService._add_paragraphs_justified(story, text, styles)
        else:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))

    @staticmethod
    def _add_risks(story: list, data: dict, styles: dict) -> None:
        BriefingPdfService._section_heading(story, "Risks and Concerns", styles)
        order = {"critical": 0, "medium": 1, "low": 2}
        risks = sorted(
            [
                raw
                for raw in (data.get("risks_and_concerns") or [])
                if isinstance(raw, dict) and _has_text(raw.get("text"))
            ],
            key=lambda r: order.get(_clean_text(r.get("severity")).lower(), 1),
        )
        if not risks:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))
            return

        cell = ParagraphStyle(
            "RiskCell",
            parent=styles["body"],
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
        )
        rows = [["Severity", "Risk"]]
        for raw in risks:
            sev = _clean_text(raw.get("severity")).upper() or "—"
            rows.append(
                [
                    sev,
                    Paragraph(_xml_escape(_clean_text(raw.get("text"))), cell),
                ]
            )
        table = Table(rows, colWidths=[0.9 * inch, 5.4 * inch], repeatRows=1)
        table.setStyle(BriefingPdfService._standard_table_style())
        story.append(table)

    @staticmethod
    def _add_checklist(story: list, data: dict, styles: dict) -> None:
        BriefingPdfService._section_heading(story, "Submission Checklist", styles)
        checklist = data.get("submission_checklist") or []
        by_category: dict[str, list[str]] = {k: [] for k in CHECKLIST_GROUP_ORDER}
        uncategorized: list[str] = []

        for raw in checklist:
            if not isinstance(raw, dict):
                continue
            label = _clean_text(raw.get("item") or raw.get("text"))
            if not label:
                continue
            cat = _clean_text(raw.get("category")) or "other"
            if cat in by_category:
                by_category[cat].append(label)
            else:
                uncategorized.append(label)

        total = sum(len(v) for v in by_category.values()) + len(uncategorized)
        if total == 0:
            story.append(Paragraph(NOT_FOUND, styles["empty"]))
            return

        item_style = ParagraphStyle(
            "CheckItem",
            parent=styles["body"],
            fontSize=9.5,
            leading=13,
            alignment=TA_LEFT,
        )

        def render_category(cat_key: str, labels: list[str]) -> None:
            if not labels:
                return
            story.append(
                Paragraph(
                    _xml_escape(CHECKLIST_GROUP_LABELS.get(cat_key, cat_key)),
                    styles["check_group"],
                )
            )
            rows = [["#", "Deliverable", "Include"]]
            for idx, label in enumerate(labels, start=1):
                rows.append(
                    [
                        str(idx),
                        Paragraph(_xml_escape(label), item_style),
                        "[ ]",
                    ]
                )
            table = Table(
                rows, colWidths=[0.4 * inch, 5.15 * inch, 0.55 * inch], repeatRows=1
            )
            style = BriefingPdfService._standard_table_style()
            style.add("ALIGN", (2, 0), (2, -1), "CENTER")
            table.setStyle(style)
            story.append(table)
            story.append(Spacer(1, 0.1 * inch))

        for cat in CHECKLIST_GROUP_ORDER:
            render_category(cat, by_category.get(cat) or [])

        if uncategorized:
            render_category("other", uncategorized)

    @staticmethod
    def _standard_table_style() -> TableStyle:
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eff6ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#f8fafc")],
                ),
            ]
        )
