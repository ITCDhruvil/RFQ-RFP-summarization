"use client";

import { useMemo, useState } from "react";

import { DeadlineItemRow } from "@/components/summary/DeadlineItemRow";
import { PenaltiesRisksInsightList } from "@/components/summary/SeverityGroupedInsightList";
import { SourceCitationList } from "@/components/summary/SourceCitationList";
import { SummaryContentBox } from "@/components/summary/SummaryContentBox";
import {
  confidenceTone,
  groupInsightsByPhase,
  INITIAL_VISIBLE,
  INSIGHT_TYPE_LABELS,
  isLargeInsight,
  sortInsights,
} from "@/lib/insightCategories";
import type {
  ExtractedInsight,
  ExtractedInsightItem,
  SourceCitation,
} from "@/lib/types/intelligence";

function itemSources(item: ExtractedInsightItem): SourceCitation[] {
  if (!item.source_text || item.citation_verified === false) return [];
  return [
    {
      page: item.page,
      section: item.section,
      section_path: item.section_path,
      source_text: item.source_text,
      citation_verified: item.citation_verified ?? true,
    },
  ];
}

function ConfidenceIndicator({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const tone = confidenceTone(score);
  const bar =
    tone === "strong"
      ? "bg-emerald-500"
      : tone === "moderate"
        ? "bg-amber-400"
        : "bg-slate-300";

  return (
    <span
      className="inline-flex min-w-[4.5rem] items-center gap-1.5 text-xs text-ink-muted"
      title={`Average grounding confidence ${pct}%`}
    >
      <span
        className="h-1 w-10 overflow-hidden rounded-full bg-surface-border"
        aria-hidden
      >
        <span className={`block h-full ${bar}`} style={{ width: `${pct}%` }} />
      </span>
      {pct}%
    </span>
  );
}

function InsightItemsList({
  items,
  extractionType,
}: {
  items: ExtractedInsightItem[];
  extractionType: string;
}) {
  const isDeadline = extractionType === "submission_deadlines";

  return (
    <ol className="space-y-2.5">
      {items.map((item, index) =>
        isDeadline ? (
          <DeadlineItemRow
            key={index}
            item={item}
            index={index}
            sources={itemSources(item)}
          />
        ) : (
          <li key={index} className="flex items-start gap-2.5">
            <span
              className="w-5 shrink-0 pt-0.5 text-right text-xs font-medium tabular-nums text-ink-muted"
              aria-hidden
            >
              {index + 1}.
            </span>
            <div className="min-w-0 flex-1">
              <SourceCitationList
                signal={item.requirement}
                sources={itemSources(item)}
              />
            </div>
          </li>
        ),
      )}
    </ol>
  );
}

function InsightPanel({ insight }: { insight: ExtractedInsight }) {
  const items = insight.payload.items ?? [];
  const isPenalties = insight.extraction_type === "penalties_and_risks";
  const [showAll, setShowAll] = useState(!isLargeInsight(insight));

  if (isPenalties) {
    return (
      <div className="border-t border-surface-border/80 px-3 pb-3 pt-2">
        {items.length ? (
          <PenaltiesRisksInsightList
            items={items}
            initialVisible={INITIAL_VISIBLE}
          />
        ) : (
          <p className="py-2 text-xs text-ink-muted">No items extracted.</p>
        )}
      </div>
    );
  }
  const large = isLargeInsight(insight);
  const visible = showAll ? items : items.slice(0, INITIAL_VISIBLE);
  const hiddenCount = items.length - visible.length;

  return (
    <div className="border-t border-surface-border/80 px-3 pb-3 pt-2">
      {large && hiddenCount > 0 && (
        <p className="mb-2 text-xs text-ink-muted">
          Showing {visible.length} of {items.length} extracted items
        </p>
      )}
      <InsightItemsList items={visible} extractionType={insight.extraction_type} />
      {large && hiddenCount > 0 && (
        <button
          type="button"
          onClick={() => setShowAll(true)}
          className="mt-3 text-xs text-ink-muted underline-offset-2 hover:text-ink hover:underline"
        >
          Show all {items.length} items
        </button>
      )}
      {large && showAll && items.length > INITIAL_VISIBLE && (
        <button
          type="button"
          onClick={() => setShowAll(false)}
          className="mt-3 text-xs text-ink-muted underline-offset-2 hover:text-ink hover:underline"
        >
          Show less
        </button>
      )}
      {!items.length && (
        <p className="py-2 text-xs text-ink-muted">No items extracted.</p>
      )}
    </div>
  );
}

function InsightAccordionRow({ insight }: { insight: ExtractedInsight }) {
  const [open, setOpen] = useState(false);
  const label =
    INSIGHT_TYPE_LABELS[insight.extraction_type] ?? insight.extraction_type;
  const count = insight.item_count ?? insight.payload.items?.length ?? 0;

  return (
    <div className="rounded-md border border-surface-border/80 bg-surface">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="min-w-0 flex-1 text-sm font-medium text-ink">
          {label}
        </span>
        <span className="shrink-0 text-xs text-ink-muted">{count} items</span>
        <ConfidenceIndicator score={insight.confidence_score} />
        <span className="w-4 shrink-0 text-center text-ink-muted">
          {open ? "−" : "+"}
        </span>
      </button>
      {open && <InsightPanel insight={insight} />}
    </div>
  );
}

export function InsightsViewer({ insights }: { insights: ExtractedInsight[] }) {
  const sorted = useMemo(() => sortInsights(insights), [insights]);
  const phases = useMemo(() => groupInsightsByPhase(sorted), [sorted]);

  if (!insights.length) {
    return (
      <p className="text-sm text-ink-muted">No extracted insights yet.</p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs leading-relaxed text-ink-muted">
        Raw extractions used to build the briefing above. Expand a category to
        review source-grounded items. Large sections open with a preview first.
      </p>

      {phases.map((phase) => (
        <SummaryContentBox key={phase.groupLabel}>
          <h4 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-ink-muted">
            {phase.groupLabel}
          </h4>
          <div className="space-y-2">
            {phase.insights.map((insight) => (
              <InsightAccordionRow key={insight.id} insight={insight} />
            ))}
          </div>
        </SummaryContentBox>
      ))}
    </div>
  );
}
