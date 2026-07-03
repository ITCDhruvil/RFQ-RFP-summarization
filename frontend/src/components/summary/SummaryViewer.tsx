"use client";

import { useState } from "react";

import { CriticalSignalsList } from "@/components/summary/CriticalSignalsList";
import { StrategyInsightsList } from "@/components/summary/StrategyInsightsList";
import { RisksConcernsList } from "@/components/summary/SeverityGroupedInsightList";
import { SubmissionChecklistView } from "@/components/summary/SubmissionChecklistView";
import { SummaryItemsList } from "@/components/summary/SummaryItemsList";
import { SummaryTextBlock } from "@/components/summary/SummaryTextBlock";
import type { GeneratedSummaryData } from "@/lib/types/intelligence";

const NOT_FOUND = "Not found in document.";

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

function EmptySection() {
  return <p className="text-sm italic text-ink-muted">{NOT_FOUND}</p>;
}

export function SummaryViewer({ data }: { data: GeneratedSummaryData }) {
  const hasSignals = Boolean(data.procurement_critical_signals?.length);
  const hasStrategy = Boolean(data.procurement_strategy_insights?.length);
  const hasKeyReqs = Boolean(data.key_requirements?.length);
  const hasDeadlines = Boolean(data.important_deadlines?.length);
  const hasTechnical = Boolean(data.technical_scope?.text?.trim());
  const hasCommercial = Boolean(data.commercial_terms?.text?.trim());
  const hasRisks = Boolean(data.risks_and_concerns?.length);
  const hasChecklist = Boolean(data.submission_checklist?.length);

  return (
    <div className="rounded-lg border border-surface-border bg-surface px-5">
      <SectionPanel title="Executive Summary">
        <SummaryTextBlock
          text={data.executive_summary?.text}
          sources={data.executive_summary?.sources}
        />
      </SectionPanel>

      <SectionPanel title="Procurement critical signals" defaultOpen>
        {hasSignals ? (
          <CriticalSignalsList signals={data.procurement_critical_signals!} />
        ) : (
          <EmptySection />
        )}
      </SectionPanel>

      <SectionPanel title="Procurement strategy insights" defaultOpen={false}>
        {hasStrategy ? (
          <StrategyInsightsList insights={data.procurement_strategy_insights!} />
        ) : (
          <EmptySection />
        )}
      </SectionPanel>

      <SectionPanel title="Key Requirements" defaultOpen={false}>
        {hasKeyReqs ? (
          <SummaryItemsList items={data.key_requirements!} />
        ) : (
          <EmptySection />
        )}
      </SectionPanel>

      <SectionPanel title="Important Deadlines" defaultOpen={false}>
        {hasDeadlines ? (
          <SummaryItemsList
            items={data.important_deadlines!}
            variant="deadline"
          />
        ) : (
          <EmptySection />
        )}
      </SectionPanel>

      <SectionPanel title="Technical Scope" defaultOpen={false}>
        <SummaryTextBlock
          text={data.technical_scope?.text}
          sources={data.technical_scope?.sources}
        />
      </SectionPanel>

      <SectionPanel title="Commercial Terms" defaultOpen={false}>
        <SummaryTextBlock
          text={data.commercial_terms?.text}
          sources={data.commercial_terms?.sources}
        />
      </SectionPanel>

      <SectionPanel title="Risks and Concerns" defaultOpen={false}>
        {hasRisks ? (
          <RisksConcernsList items={data.risks_and_concerns!} />
        ) : (
          <EmptySection />
        )}
      </SectionPanel>

      <SectionPanel title="Submission Checklist" defaultOpen={false}>
        {hasChecklist ? (
          <SubmissionChecklistView items={data.submission_checklist!} />
        ) : (
          <EmptySection />
        )}
      </SectionPanel>
    </div>
  );
}
