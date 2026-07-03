"use client";

import { useState } from "react";

import { SummaryTextBlock } from "@/components/summary/SummaryTextBlock";
import type { GeneratedProposalData } from "@/lib/types/proposal";

const COMPLIANCE_LABELS: Record<string, string> = {
  compliant: "Compliant",
  fully: "Compliant",
  partial: "Partial",
  gap: "Gap",
  planned: "Planned",
  na: "N/A",
};

function SectionPanel({
  title,
  children,
  defaultOpen = true,
}: {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-b border-surface-border last:border-0">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-3 text-left text-sm font-semibold"
      >
        {title}
        <span className="text-ink-muted">{open ? "−" : "+"}</span>
      </button>
      {open && <div className="pb-4 text-sm">{children}</div>}
    </div>
  );
}

function ComplianceMatrixTable({
  rows,
}: {
  rows: NonNullable<GeneratedProposalData["compliance_matrix"]>;
}) {
  if (!rows.length) {
    return (
      <p className="text-sm italic text-ink-muted">No compliance matrix generated.</p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-collapse text-left text-xs">
        <thead>
          <tr className="border-b border-surface-border bg-surface-muted">
            <th className="px-2 py-2 font-semibold">Ref</th>
            <th className="px-2 py-2 font-semibold">Requirement</th>
            <th className="px-2 py-2 font-semibold">Response</th>
            <th className="px-2 py-2 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr
              key={`${row.requirement_ref ?? idx}-${idx}`}
              className="border-b border-surface-border align-top"
            >
              <td className="px-2 py-2 font-medium text-ink-muted">
                {row.requirement_ref ?? `TR-${String(idx + 1).padStart(2, "0")}`}
              </td>
              <td className="px-2 py-2">{row.requirement_text}</td>
              <td className="px-2 py-2">{row.vendor_response ?? row.response}</td>
              <td className="px-2 py-2 whitespace-nowrap">
                {COMPLIANCE_LABELS[
                  (row.compliance_status ?? row.compliance ?? "planned").toLowerCase()
                ] ??
                  row.compliance_status ??
                  row.compliance ??
                  "Planned"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ProposalViewer({ data }: { data: GeneratedProposalData }) {
  const sections = data.technical_approach?.sections ?? [];
  const phases =
    data.transition_plan?.phases ?? data.implementation_plan?.phases ?? [];
  const roles = data.team_and_staffing?.roles ?? [];
  const risks = data.operational_risks ?? data.risks_and_mitigations ?? [];
  const gaps = data.gaps_and_placeholders ?? [];
  const validation = data._meta?.validation as
    | { passed?: boolean; error_count?: number; warning_count?: number }
    | undefined;
  const sectionConfidence = data._meta?.section_confidence as
    | Record<string, number>
    | undefined;

  return (
    <div className="space-y-4">
      {validation && (
        <div
          className={`rounded-md border px-4 py-3 text-sm ${
            validation.passed
              ? "border-green-200 bg-green-50 text-green-900"
              : "border-amber-200 bg-amber-50 text-amber-900"
          }`}
        >
          Validation: {validation.error_count ?? 0} errors,{" "}
          {validation.warning_count ?? 0} warnings
          {(validation as { blocked?: boolean }).blocked && (
            <span className="ml-2 font-medium text-red-800">· Blocked in strict mode</span>
          )}
          {sectionConfidence && (
            <span className="ml-2 text-xs text-ink-muted">
              · Compliance matrix confidence:{" "}
              {Math.round((sectionConfidence.compliance_matrix ?? 0) * 100)}%
            </span>
          )}
        </div>
      )}

      {(data.traceability_matrix?.length ?? 0) > 0 && (
        <details className="rounded-lg border border-surface-border bg-surface px-4 py-2 text-sm">
          <summary className="cursor-pointer font-medium">
            Requirement traceability ({data.traceability_matrix!.length} rows)
          </summary>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="border-b text-left">
                  <th className="py-1 pr-2">Req ID</th>
                  <th className="py-1 pr-2">Evidence</th>
                  <th className="py-1 pr-2">Section</th>
                  <th className="py-1 pr-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.traceability_matrix!.map((row, idx) => (
                  <tr key={idx} className="border-b border-surface-border">
                    <td className="py-1 pr-2 font-mono">{row.requirement_id}</td>
                    <td className="py-1 pr-2">
                      {(row.evidence_ids ?? []).join(", ") || "—"}
                    </td>
                    <td className="py-1 pr-2">{row.proposal_section}</td>
                    <td className="py-1 pr-2">{row.compliance_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      <div className="rounded-lg border border-surface-border bg-surface px-5">
      <SectionPanel title="Cover Letter">
        <SummaryTextBlock
          text={data.cover_letter?.text}
          sources={data.cover_letter?.sources}
        />
      </SectionPanel>

      <SectionPanel title="Executive Summary">
        <SummaryTextBlock
          text={data.executive_summary?.text}
          sources={data.executive_summary?.sources}
        />
      </SectionPanel>

      <SectionPanel title="Company Overview" defaultOpen={false}>
        <SummaryTextBlock
          text={data.company_overview?.text}
          sources={data.company_overview?.sources}
        />
      </SectionPanel>

      <SectionPanel title="Understanding of Requirements">
        <SummaryTextBlock
          text={data.understanding_of_requirements?.text}
          sources={data.understanding_of_requirements?.sources}
        />
      </SectionPanel>

      {(data.why_choose_us?.differentiators?.length ?? 0) > 0 && (
        <SectionPanel title="Why Choose Us" defaultOpen={false}>
          <ul className="space-y-2">
            {data.why_choose_us!.differentiators!.map((d, idx) => (
              <li key={idx}>{d.claim}</li>
            ))}
          </ul>
        </SectionPanel>
      )}

      <SectionPanel title="Technical Approach">
        {sections.length ? (
          <div className="space-y-4">
            {sections.map((sec, idx) => (
              <div key={`${sec.title ?? idx}-${idx}`}>
                {sec.title && (
                  <h4 className="mb-1 text-sm font-semibold">{sec.title}</h4>
                )}
                <SummaryTextBlock text={sec.content} sources={sec.sources} />
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm italic text-ink-muted">No technical sections generated.</p>
        )}
      </SectionPanel>

      {(data.staffing_approach?.text?.trim()?.length ?? 0) > 0 && (
        <SectionPanel title="Staffing Approach" defaultOpen={false}>
          <SummaryTextBlock
            text={data.staffing_approach?.text}
            sources={data.staffing_approach?.sources}
          />
        </SectionPanel>
      )}

      {(data.training_framework?.text?.trim()?.length ?? 0) > 0 && (
        <SectionPanel title="Training Framework" defaultOpen={false}>
          <SummaryTextBlock
            text={data.training_framework?.text}
            sources={data.training_framework?.sources}
          />
        </SectionPanel>
      )}

      <SectionPanel title="Compliance Matrix" defaultOpen>
        <ComplianceMatrixTable rows={data.compliance_matrix ?? []} />
      </SectionPanel>

      <SectionPanel title="Implementation Plan" defaultOpen={false}>
        {phases.length ? (
          <ul className="space-y-3">
            {phases.map((phase, idx) => (
              <li key={`${phase.name ?? idx}-${idx}`}>
                <p className="font-medium">
                  {phase.name}
                  {phase.duration ? (
                    <span className="font-normal text-ink-muted">
                      {" "}
                      ({phase.duration})
                    </span>
                  ) : null}
                </p>
                {phase.deliverables?.length ? (
                  <ul className="mt-1 list-inside list-disc text-ink-muted">
                    {phase.deliverables.map((d, i) => (
                      <li key={`${d}-${i}`}>{d}</li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm italic text-ink-muted">No implementation plan generated.</p>
        )}
      </SectionPanel>

      <SectionPanel title="Team & Staffing" defaultOpen={false}>
        {roles.length ? (
          <ul className="space-y-2">
            {roles.map((role, idx) => (
              <li key={`${role.title ?? idx}-${idx}`}>
                <span className="font-medium">{role.title}</span>
                {role.profile_ref ? (
                  <span className="text-ink-muted"> — {role.profile_ref}</span>
                ) : null}
                {role.responsibilities ? (
                  <p className="mt-0.5 text-ink-muted">{role.responsibilities}</p>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm italic text-ink-muted">No team structure generated.</p>
        )}
      </SectionPanel>

      <SectionPanel title="Operational Risks" defaultOpen={false}>
        {risks.length ? (
          <ul className="space-y-3">
            {risks.map((item, idx) => (
              <li key={`${item.risk ?? idx}-${idx}`}>
                <p>
                  <span className="font-medium">Risk:</span> {item.risk}
                </p>
                {Boolean((item as { likelihood?: unknown })?.likelihood) && (
                  <p className="text-xs text-ink-muted">
                    Likelihood: {(item as { likelihood?: string }).likelihood} · Impact:{" "}
                    {(item as { impact?: string }).impact} · Owner:{" "}
                    {(item as { owner?: string }).owner}
                  </p>
                )}
                <p className="mt-1 text-ink-muted">
                  <span className="font-medium text-ink">Mitigation:</span>{" "}
                  {item.mitigation}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm italic text-ink-muted">No risks listed.</p>
        )}
      </SectionPanel>

      {((data.assumptions_and_exclusions?.assumptions?.length ?? 0) > 0 ||
        (data.assumptions_and_exclusions?.exclusions?.length ?? 0) > 0) && (
        <SectionPanel title="Assumptions & Exclusions" defaultOpen={false}>
          {(data.assumptions_and_exclusions?.assumptions?.length ?? 0) > 0 && (
            <>
              <p className="mb-1 text-xs font-semibold uppercase text-ink-muted">
                Assumptions
              </p>
              <ul className="mb-3 list-inside list-disc space-y-1">
                {data.assumptions_and_exclusions!.assumptions!.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </>
          )}
          {(data.assumptions_and_exclusions?.exclusions?.length ?? 0) > 0 && (
            <>
              <p className="mb-1 text-xs font-semibold uppercase text-ink-muted">
                Exclusions
              </p>
              <ul className="list-inside list-disc space-y-1">
                {data.assumptions_and_exclusions!.exclusions!.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </>
          )}
        </SectionPanel>
      )}

      {gaps.length > 0 && (
        <SectionPanel title="Items Requiring Completion" defaultOpen>
          <ul className="space-y-1 text-sm">
            {gaps.map((gap, idx) => (
              <li key={`${gap.field ?? idx}-${idx}`} className="text-amber-800">
                {gap.field}
                {gap.reason ? (
                  <span className="text-ink-muted"> ({gap.reason})</span>
                ) : null}
              </li>
            ))}
          </ul>
        </SectionPanel>
      )}
      </div>
    </div>
  );
}
