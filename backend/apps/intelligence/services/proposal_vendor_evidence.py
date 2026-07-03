"""Build searchable vendor evidence index from bidder profile."""

from __future__ import annotations

import re
from typing import Any

from apps.intelligence.services.proposal_schemas import (
    EvidenceRecord,
    EvidenceSourceType,
)


def build_vendor_evidence_index(profile: dict[str, Any]) -> list[EvidenceRecord]:
    """Flatten vendor profile into provenance-tracked evidence records."""
    records: list[EvidenceRecord] = []
    idx = 0

    def _add(
        source_type: EvidenceSourceType,
        excerpt: str,
        field_path: str,
        source_ref: str = "",
    ) -> None:
        text = excerpt.strip()
        if not text:
            return
        nonlocal idx
        idx += 1
        records.append(
            EvidenceRecord(
                evidence_id=f"VE-{idx:03d}",
                source_type=source_type.value,
                source_ref=source_ref or field_path,
                excerpt=text,
                field_path=field_path,
            )
        )

    company = str(profile.get("company_name") or "").strip()
    if company:
        _add(
            EvidenceSourceType.SOURCE_VENDOR_PROFILE,
            company,
            "company_name",
            "Bidder Profile — Company Name",
        )

    for i, cap in enumerate(profile.get("capabilities") or []):
        _add(
            EvidenceSourceType.SOURCE_VENDOR_PROFILE,
            str(cap),
            f"capabilities[{i}]",
            "Bidder Profile — Capability",
        )

    for i, cert in enumerate(profile.get("certifications") or []):
        _add(
            EvidenceSourceType.SOURCE_CERTIFICATION,
            str(cert),
            f"certifications[{i}]",
            "Bidder Profile — Certification",
        )

    for i, person in enumerate(profile.get("key_personnel") or []):
        if not isinstance(person, dict):
            continue
        parts = [
            str(person.get("name") or "").strip(),
            str(person.get("role") or "").strip(),
            str(person.get("experience") or "").strip(),
        ]
        text = " — ".join(p for p in parts if p)
        if text:
            _add(
                EvidenceSourceType.SOURCE_VENDOR_PROFILE,
                text,
                f"key_personnel[{i}]",
                f"Bidder Profile — {person.get('name') or 'Personnel'}",
            )

    for i, project in enumerate(profile.get("reference_projects") or []):
        if not isinstance(project, dict):
            continue
        parts = [
            str(project.get("name") or "").strip(),
            str(project.get("client") or "").strip(),
            str(project.get("description") or "").strip(),
        ]
        text = " | ".join(p for p in parts if p)
        if text:
            _add(
                EvidenceSourceType.SOURCE_CASE_STUDY,
                text,
                f"reference_projects[{i}]",
                f"Case Study — {project.get('name') or 'Project'}",
            )

    notes = str(profile.get("additional_notes") or "").strip()
    if notes:
        _add(
            EvidenceSourceType.SOURCE_VENDOR_PROFILE,
            notes,
            "additional_notes",
            "Bidder Profile — Additional Notes",
        )

    assets = profile.get("knowledge_assets") or {}
    if isinstance(assets, dict):
        for i, policy in enumerate(assets.get("policies") or []):
            _add(
                EvidenceSourceType.SOURCE_POLICY,
                str(policy),
                f"knowledge_assets.policies[{i}]",
                "Vendor KB — Policy",
            )
        for i, sop in enumerate(assets.get("sops") or []):
            _add(
                EvidenceSourceType.SOURCE_POLICY,
                str(sop),
                f"knowledge_assets.sops[{i}]",
                "Vendor KB — SOP",
            )
        for i, item in enumerate(assets.get("service_catalog") or []):
            _add(
                EvidenceSourceType.SOURCE_KNOWLEDGE_BASE,
                str(item),
                f"knowledge_assets.service_catalog[{i}]",
                "Vendor KB — Service Catalog",
            )
        for i, prog in enumerate(assets.get("training_programs") or []):
            _add(
                EvidenceSourceType.SOURCE_KNOWLEDGE_BASE,
                str(prog),
                f"knowledge_assets.training_programs[{i}]",
                "Vendor KB — Training Program",
            )
        for i, resume in enumerate(assets.get("resumes") or []):
            _add(
                EvidenceSourceType.SOURCE_VENDOR_PROFILE,
                str(resume),
                f"knowledge_assets.resumes[{i}]",
                "Vendor KB — Resume",
            )
        org = str(assets.get("org_structure") or "").strip()
        if org:
            _add(
                EvidenceSourceType.SOURCE_KNOWLEDGE_BASE,
                org,
                "knowledge_assets.org_structure",
                "Vendor KB — Org Structure",
            )

    return records


def evidence_by_id(index: list[EvidenceRecord]) -> dict[str, EvidenceRecord]:
    return {r["evidence_id"]: r for r in index if r.get("evidence_id")}


def tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{3,}", text.lower()) if len(t) >= 3}
