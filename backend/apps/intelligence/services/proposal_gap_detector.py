"""Detect gaps between RFP requirements and vendor evidence."""

from __future__ import annotations

import re

from apps.intelligence.models import ExtractedInsight
from apps.intelligence.services.proposal_schemas import (
    ClassifiedRequirement,
    DetectedGap,
    EvidenceRecord,
)
from apps.intelligence.services.proposal_vendor_evidence import tokenize


def _cert_tokens_from_rfp(requirements: list[ClassifiedRequirement]) -> list[str]:
    patterns = (
        r"iso\s*\d+",
        r"psara",
        r"msme",
        r"gst",
        r"soc\s*2",
        r"pci",
    )
    found: list[str] = []
    for req in requirements:
        text = (req.get("requirement") or "").lower()
        for pat in patterns:
            match = re.search(pat, text)
            if match:
                found.append(match.group())
    return list(dict.fromkeys(found))


def _vendor_cert_tokens(evidence: list[EvidenceRecord]) -> set[str]:
    tokens: set[str] = set()
    for ev in evidence:
        if ev.get("source_type") != "SOURCE_CERTIFICATION":
            continue
        tokens |= tokenize(ev.get("excerpt") or "")
    return tokens


def detect_gaps(
    requirements: list[ClassifiedRequirement],
    evidence_index: list[EvidenceRecord],
    insights: list[ExtractedInsight],
    profile: dict,
) -> list[DetectedGap]:
    gaps: list[DetectedGap] = []

    rfp_certs = _cert_tokens_from_rfp(requirements)
    vendor_certs = _vendor_cert_tokens(evidence_index)
    for cert in rfp_certs:
        cert_tokens = tokenize(cert)
        if not cert_tokens & vendor_certs:
            gaps.append(
                DetectedGap(
                    field=f"Certification: {cert.upper()}",
                    rfp_requirement=f"RFP references {cert}",
                    reason="certification_not_in_profile",
                    action="Vendor to provide certification evidence",
                    category="COMPLIANCE",
                )
            )

    for insight in insights:
        if insight.extraction_type != "mandatory_documents":
            continue
        for item in (insight.payload or {}).get("items") or []:
            text = str(item.get("requirement") or "").strip()
            if not text:
                continue
            lowered = text.lower()
            if any(
                k in lowered
                for k in ("financial statement", "audit report", "bank guarantee")
            ):
                gaps.append(
                    DetectedGap(
                        field=text[:120],
                        rfp_requirement=text,
                        reason="document_upload_required",
                        action="Vendor to attach supporting document",
                        category="COMPLIANCE",
                    )
                )

    staffing_reqs = [r for r in requirements if r.get("category") == "STAFFING"]
    has_workforce_evidence = any(
        "capabilities" in (e.get("field_path") or "")
        or "reference_projects" in (e.get("field_path") or "")
        or "additional_notes" in (e.get("field_path") or "")
        for e in evidence_index
    )
    if staffing_reqs and not has_workforce_evidence:
        gaps.append(
            DetectedGap(
                field="Workforce capacity evidence",
                rfp_requirement="Staffing requirements identified in RFP",
                reason="workforce_evidence_missing",
                action="Vendor to provide guard pool size, deployment capacity, or registry",
                category="STAFFING",
            )
        )

    gaps.append(
        DetectedGap(
            field="Commercial pricing",
            rfp_requirement="Commercial proposal / pricing schedule",
            reason="pricing_required",
            action="Vendor to complete commercial volume separately",
            category="COMMERCIAL",
        )
    )

    if not profile.get("key_personnel"):
        gaps.append(
            DetectedGap(
                field="Named key personnel",
                rfp_requirement="CVs / resumes may be required",
                reason="personnel_not_in_profile",
                action="Vendor to provide key personnel details and CVs",
                category="STAFFING",
            )
        )

    return gaps
