"use client";

import { useState } from "react";

import { SourceCitationList } from "@/components/summary/SourceCitationList";
import { SummaryContentBox } from "@/components/summary/SummaryContentBox";
import {
  groupByRiskSeverity,
  resolveItemSeverity,
  RISK_SEVERITY_SECTIONS,
  riskSeverityLabel,
  type RiskSeverity,
} from "@/lib/riskSeverity";
import type {
  ExtractedInsightItem,
  SourceCitation,
  SummarySectionBlock,
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

function severityBadgeClass(level: RiskSeverity): string {
  if (level === "critical") {
    return "bg-red-100 text-red-800 ring-red-200";
  }
  if (level === "medium") {
    return "bg-amber-100 text-amber-900 ring-amber-200";
  }
  return "bg-surface-muted text-ink-muted ring-surface-border";
}

type RowItem = ExtractedInsightItem | SummarySectionBlock;

function rowText(item: RowItem): string {
  if ("requirement" in item && item.requirement) return item.requirement;
  if ("text" in item && item.text) return String(item.text);
  if ("item" in item && item.item) return String(item.item);
  return "—";
}

function rowSources(item: RowItem): SourceCitation[] | undefined {
  if ("requirement" in item) return itemSources(item as ExtractedInsightItem);
  return (item as SummarySectionBlock).sources;
}

function SeveritySection({
  level,
  items,
  showIndex,
}: {
  level: RiskSeverity;
  items: RowItem[];
  showIndex: boolean;
}) {
  if (!items.length) return null;

  return (
    <SummaryContentBox className="mb-0">
      <h4 className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-ink-muted">
        <span
          className={`rounded px-1.5 py-0.5 text-[10px] font-semibold normal-case tracking-normal ring-1 ${severityBadgeClass(level)}`}
        >
          {riskSeverityLabel(level)}
        </span>
        <span className="font-normal normal-case text-ink-muted">
          ({items.length})
        </span>
      </h4>
      <ul className="divide-y divide-surface-border/80">
        {items.map((item, i) => (
          <li key={i} className="py-3 first:pt-0 last:pb-0">
            <div className="flex items-start gap-2.5">
              {showIndex && (
                <span
                  className="w-5 shrink-0 pt-0.5 text-right text-xs font-medium tabular-nums text-ink-muted"
                  aria-hidden
                >
                  {i + 1}.
                </span>
              )}
              <div className="min-w-0 flex-1">
                <SourceCitationList
                  signal={rowText(item)}
                  sources={rowSources(item)}
                />
              </div>
            </div>
          </li>
        ))}
      </ul>
    </SummaryContentBox>
  );
}

export function PenaltiesRisksInsightList({
  items,
  initialVisible = 8,
}: {
  items: ExtractedInsightItem[];
  initialVisible?: number;
}) {
  const [showAll, setShowAll] = useState(items.length <= initialVisible);
  const visible = showAll ? items : items.slice(0, initialVisible);
  const groups = groupByRiskSeverity(
    visible as Array<{ severity?: RiskSeverity }>,
    (row) => resolveItemSeverity(row as unknown as ExtractedInsightItem) as RiskSeverity
  );

  return (
    <div className="space-y-4">
      {items.length > initialVisible && !showAll && (
        <p className="text-xs text-ink-muted">
          Showing {visible.length} of {items.length} extracted items
        </p>
      )}
      {RISK_SEVERITY_SECTIONS.map((level) => (
        <SeveritySection
          key={level}
          level={level}
          items={groups[level]}
          showIndex
        />
      ))}
      {items.length > initialVisible && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="text-xs text-ink-muted underline-offset-2 hover:text-ink hover:underline"
        >
          {showAll ? "Show less" : `Show all ${items.length} items`}
        </button>
      )}
    </div>
  );
}

export function RisksConcernsList({
  items,
}: {
  items: SummarySectionBlock[];
}) {
  const groups = groupByRiskSeverity(
    items as Array<{ severity?: RiskSeverity }>,
    (row) => resolveItemSeverity(row as unknown as ExtractedInsightItem) as RiskSeverity
  );

  return (
    <div className="space-y-4">
      {RISK_SEVERITY_SECTIONS.map((level) => (
        <SeveritySection
          key={level}
          level={level}
          items={groups[level]}
          showIndex={false}
        />
      ))}
    </div>
  );
}
