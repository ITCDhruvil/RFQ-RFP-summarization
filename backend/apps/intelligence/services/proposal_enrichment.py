"""Fill thin or missing proposal sections from bidder profile and pipeline context."""

from __future__ import annotations

from collections import Counter
from typing import Any

from apps.intelligence.services.proposal_methodology_templates import (
    get_methodology_framework,
)
from apps.intelligence.services.proposal_schemas import VENDOR_PLACEHOLDER


def _company(profile: dict[str, Any]) -> str:
    return str(profile.get("company_name") or "Our organization").strip()


def _text_len(value: Any) -> int:
    return len(str(value or "").strip())


def enrich_team_and_staffing(data: dict[str, Any], profile: dict[str, Any]) -> None:
    existing = data.get("team_and_staffing")
    roles = existing.get("roles") if isinstance(existing, dict) else None
    if isinstance(roles, list) and roles:
        return

    built: list[dict[str, str]] = []
    for person in profile.get("key_personnel") or []:
        if not isinstance(person, dict):
            continue
        name = str(person.get("name") or "").strip()
        role = str(person.get("role") or "").strip()
        experience = str(person.get("experience") or "").strip()
        if not role and not name:
            continue
        built.append(
            {
                "title": role or "Key role",
                "profile_ref": name or "Named in bidder profile",
                "responsibilities": experience
                or "Account governance, SLA oversight, and client escalation.",
            }
        )

    if not built:
        built = [
            {
                "title": "Project Director",
                "profile_ref": VENDOR_PLACEHOLDER,
                "responsibilities": "Single point of accountability for contract delivery and governance.",
            },
            {
                "title": "Operations Manager",
                "profile_ref": VENDOR_PLACEHOLDER,
                "responsibilities": "Day-to-day staffing, shift coverage, and incident command.",
            },
            {
                "title": "Compliance & Quality Lead",
                "profile_ref": VENDOR_PLACEHOLDER,
                "responsibilities": "SOP compliance, audits, training records, and client reporting.",
            },
        ]

    data["team_and_staffing"] = {"roles": built}


def enrich_staffing_approach(data: dict[str, Any], profile: dict[str, Any]) -> None:
    block = data.get("staffing_approach")
    if not isinstance(block, dict):
        block = {}
        data["staffing_approach"] = block
    if _text_len(block.get("text")) >= 400:
        return

    company = _company(profile)
    caps = [str(c).strip() for c in (profile.get("capabilities") or []) if str(c).strip()]
    cap_line = ", ".join(caps[:4]) if caps else "workforce deployment and supervision"
    framework = get_methodology_framework("STAFFING")
    slots = "; ".join(f"{k.replace('_', ' ').title()}: {v}" for k, v in framework.items())

    block["text"] = (
        f"{company} will deploy a structured staffing model aligned to the RFP scope, "
        f"leveraging our experience in {cap_line}. "
        f"Our approach covers: {slots}. "
        "Site supervisors maintain daily roll-call, backup pools activate within agreed SLA windows, "
        "and escalation routes to the Operations Manager and Project Director. "
        "Pre-deployment vetting, uniform/PPE readiness, and client induction are completed "
        "before personnel are assigned to posts."
    )


def enrich_technical_approach(
    data: dict[str, Any],
    pipeline_ctx: dict[str, Any],
    profile: dict[str, Any],
) -> None:
    tech = data.get("technical_approach")
    if not isinstance(tech, dict):
        tech = {"sections": []}
        data["technical_approach"] = tech
    sections = tech.get("sections")
    if not isinstance(sections, list):
        sections = []
        tech["sections"] = sections

    substantive = [
        s
        for s in sections
        if isinstance(s, dict) and _text_len(s.get("content")) >= 200
    ]
    if len(substantive) >= 3:
        return

    requirements = pipeline_ctx.get("requirements") or []
    counts = Counter(
        str(r.get("category") or "TECHNICAL") for r in requirements if isinstance(r, dict)
    )
    company = _company(profile)

    category_titles = {
        "STAFFING": "Workforce Deployment & Shift Management",
        "SECURITY": "Security Operations & Patrol Model",
        "OPERATIONAL": "24/7 Coverage & SLA Operations",
        "TRAINING": "Training, Competency & SOP Compliance",
        "TRANSITION": "Mobilization & Transition Governance",
        "REPORTING": "Reporting, KPIs & Governance",
        "TECHNICAL": "Technical Service Delivery",
        "COMPLIANCE": "Regulatory & Contract Compliance",
        "IMPLEMENTATION": "Implementation Methodology",
    }

    built: list[dict[str, str]] = []
    for category, _count in counts.most_common(6):
        framework = get_methodology_framework(category)
        bullets = "\n".join(
            f"- **{label.replace('_', ' ').title()}:** {detail}"
            for label, detail in framework.items()
        )
        built.append(
            {
                "title": category_titles.get(category, category.replace("_", " ").title()),
                "content": (
                    f"{company} addresses {category.lower()} requirements through a documented "
                    f"operating model with named controls and measurable checkpoints:\n\n{bullets}\n\n"
                    "Controls are embedded in site SOPs, supervisor checklists, and monthly "
                    "governance reviews with the client."
                ),
                "methodology_focus": category,
            }
        )

    if not built:
        for category in ("SECURITY", "STAFFING", "OPERATIONAL"):
            framework = get_methodology_framework(category)
            bullets = "\n".join(
                f"- {label.replace('_', ' ').title()}: {detail}"
                for label, detail in framework.items()
            )
            built.append(
                {
                    "title": category_titles[category],
                    "content": (
                        f"{company} will execute the following methodology:\n\n{bullets}"
                    ),
                    "methodology_focus": category,
                }
            )

    tech["sections"] = built


def enrich_cover_letter(data: dict[str, Any], profile: dict[str, Any], document_name: str) -> None:
    block = data.get("cover_letter")
    if not isinstance(block, dict):
        block = {}
        data["cover_letter"] = block
    if _text_len(block.get("text")) >= 500:
        return

    company = _company(profile)
    refs = profile.get("reference_projects") or []
    ref_snippet = ""
    if refs and isinstance(refs[0], dict):
        ref = refs[0]
        ref_snippet = (
            f" Our relevant experience includes {ref.get('name') or 'a comparable program'} "
            f"for {ref.get('client') or 'a public-sector client'}."
        )

    block["text"] = (
        f"Dear Evaluation Committee,\n\n"
        f"We are pleased to submit {company}'s technical proposal in response to "
        f"\"{document_name}\". We have reviewed the scope, evaluation criteria, and "
        f"operational requirements in detail and confirm our ability to deliver a "
        f"compliant, audit-ready service model.{ref_snippet}\n\n"
        f"This submission describes our methodology for mobilization, staffing, supervision, "
        f"training, incident management, and governance. Commercial pricing is provided in the "
        f"accompanying commercial volume. We welcome the opportunity to present our approach "
        f"and clarify any points during evaluation.\n\n"
        f"Respectfully submitted,\n"
        f"Authorized Signatory\n{company}"
    )


def enrich_transition_plan(data: dict[str, Any], profile: dict[str, Any]) -> None:
    plan = data.get("transition_plan")
    if not isinstance(plan, dict):
        plan = {}
        data["transition_plan"] = plan
    phases = plan.get("phases")
    if isinstance(phases, list) and len(phases) >= 3:
        return

    company = _company(profile)
    plan["phases"] = [
        {
            "name": "Phase 1 — Mobilization Planning (Weeks 1–2)",
            "duration": "2 weeks",
            "deliverables": [
                "Governance charter and escalation matrix",
                "Site readiness checklist and access plan",
                "Recruitment pipeline and backup pool sizing",
            ],
        },
        {
            "name": "Phase 2 — Deployment & Stabilization (Weeks 3–6)",
            "duration": "4 weeks",
            "deliverables": [
                "Personnel onboarding and client induction",
                "SOP rollout and supervisor briefings",
                "Daily attendance and incident reporting live",
            ],
        },
        {
            "name": "Phase 3 — Steady-State Operations (Week 7+)",
            "duration": "Ongoing",
            "deliverables": [
                "Monthly SLA/KPI governance reviews",
                "Training refreshers and audit cycles",
                f"Continuous improvement led by {company} operations leadership",
            ],
        },
    ]


def enrich_operational_risks(data: dict[str, Any], profile: dict[str, Any]) -> None:
    risks = data.get("operational_risks")
    if isinstance(risks, list) and len(risks) >= 5:
        return

    personnel = profile.get("key_personnel") or []
    owner = "Operations Manager"
    if personnel and isinstance(personnel[0], dict) and personnel[0].get("name"):
        owner = str(personnel[0].get("role") or owner)

    data["operational_risks"] = [
        {
            "risk": "Unplanned absenteeism affecting post coverage",
            "likelihood": "medium",
            "impact": "high",
            "mitigation": "Maintain backup pool at 10–15% of deployed headcount; supervisor activates replacements within SLA window.",
            "owner": owner,
        },
        {
            "risk": "Attrition during mobilization",
            "likelihood": "medium",
            "impact": "medium",
            "mitigation": "Parallel recruitment pipeline, retention incentives, and phased onboarding.",
            "owner": "Project Director",
        },
        {
            "risk": "Delayed incident escalation",
            "likelihood": "low",
            "impact": "high",
            "mitigation": "Tiered escalation matrix, 24/7 control-room monitoring, and weekly drill reviews.",
            "owner": owner,
        },
        {
            "risk": "Training non-compliance at site",
            "likelihood": "medium",
            "impact": "medium",
            "mitigation": "Competency register, refresher calendar, and supervisor sign-off before deployment.",
            "owner": "Compliance & Quality Lead",
        },
        {
            "risk": "Transport or access disruption",
            "likelihood": "low",
            "impact": "medium",
            "mitigation": "Alternate routing plan, cab inspection SOP, and client coordination protocol.",
            "owner": owner,
        },
        {
            "risk": "Report submission delays",
            "likelihood": "low",
            "impact": "low",
            "mitigation": "Automated report templates, named owners, and monthly governance cadence.",
            "owner": "Compliance & Quality Lead",
        },
    ]


def enrich_assumptions_exclusions(data: dict[str, Any], pipeline_ctx: dict[str, Any]) -> None:
    block = data.get("assumptions_and_exclusions")
    if not isinstance(block, dict):
        block = {"assumptions": [], "exclusions": []}
        data["assumptions_and_exclusions"] = block

    assumptions = block.get("assumptions")
    exclusions = block.get("exclusions")
    if not isinstance(assumptions, list):
        assumptions = []
    if not isinstance(exclusions, list):
        exclusions = []

    if len(assumptions) < 3:
        assumptions.extend(
            [
                "Client will provide timely site access, induction slots, and named SPOCs.",
                "Agreed staffing numbers and shift patterns are as per RFP scope.",
                "Force majeure events are handled per contract terms.",
            ]
        )
    if len(exclusions) < 2:
        exclusions.extend(
            [
                "Costs for client-provided infrastructure beyond agreed scope.",
                "Statutory fee increases unless contractually pass-through.",
            ]
        )
    block["assumptions"] = assumptions[:12]
    block["exclusions"] = exclusions[:10]


def enrich_gaps_from_pipeline(data: dict[str, Any], pipeline_ctx: dict[str, Any]) -> None:
    gaps = data.get("gaps_and_placeholders")
    if not isinstance(gaps, list):
        gaps = []
        data["gaps_and_placeholders"] = gaps

    existing_fields = {str(g.get("field") or "").lower() for g in gaps if isinstance(g, dict)}
    for gap in pipeline_ctx.get("gaps") or []:
        if not isinstance(gap, dict):
            continue
        field = str(gap.get("field") or gap.get("rfp_requirement") or "").strip()
        if not field or field.lower() in existing_fields:
            continue
        gaps.append(
            {
                "field": field,
                "reason": str(gap.get("reason") or "vendor_evidence_missing"),
                "action": str(gap.get("action") or "Provide supporting evidence in bidder profile"),
            }
        )
        existing_fields.add(field.lower())


def enrich_training_framework(data: dict[str, Any], profile: dict[str, Any]) -> None:
    block = data.get("training_framework")
    if not isinstance(block, dict):
        block = {}
        data["training_framework"] = block
    if _text_len(block.get("text")) >= 200:
        return
    programs = (profile.get("knowledge_assets") or {}).get("training_programs") or []
    program_line = "; ".join(str(p) for p in programs[:3]) if programs else (
        "induction, quarterly refreshers, and supervisor academy modules"
    )
    block["text"] = (
        f"{_company(profile)} operates a structured training framework covering {program_line}. "
        "Competency is verified before site deployment and tracked in a central register with "
        "refresher triggers aligned to client SOP changes."
    )


def enrich_company_overview(data: dict[str, Any], profile: dict[str, Any]) -> None:
    block = data.get("company_overview")
    if not isinstance(block, dict):
        block = {}
        data["company_overview"] = block
    if _text_len(block.get("text")) >= 300:
        return
    company = _company(profile)
    certs = [str(c) for c in (profile.get("certifications") or []) if str(c).strip()]
    cert_line = ", ".join(certs[:4]) if certs else "applicable industry registrations"
    notes = str(profile.get("additional_notes") or "").strip()
    block["text"] = (
        f"{company} is an established service provider with credentials including {cert_line}. "
        f"{notes} "
        "Our delivery model combines regional operations leadership, audit-ready documentation, "
        "and proven experience across multi-site public-sector programs."
    ).strip()


def enrich_proposal_from_pipeline(
    data: dict[str, Any],
    profile: dict[str, Any],
    pipeline_ctx: dict[str, Any],
    *,
    document_name: str = "",
) -> dict[str, Any]:
    """Backfill professional sections when the LLM output is thin or incomplete."""
    enrich_cover_letter(data, profile, document_name)
    enrich_company_overview(data, profile)
    enrich_staffing_approach(data, profile)
    enrich_training_framework(data, profile)
    enrich_team_and_staffing(data, profile)
    enrich_technical_approach(data, pipeline_ctx, profile)
    enrich_transition_plan(data, profile)
    enrich_operational_risks(data, profile)
    enrich_assumptions_exclusions(data, pipeline_ctx)
    enrich_gaps_from_pipeline(data, pipeline_ctx)
    return data
