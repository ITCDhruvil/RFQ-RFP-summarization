"use client";

import { SourceCitationList } from "@/components/summary/SourceCitationList";
import { SummaryContentBox } from "@/components/summary/SummaryContentBox";
import type { ProcurementStrategyInsight } from "@/lib/types/intelligence";

export function StrategyInsightsList({
  insights,
}: {
  insights: ProcurementStrategyInsight[];
}) {
  if (!insights.length) return null;

  return (
    <SummaryContentBox>
      <ul className="divide-y divide-surface-border/80">
        {insights.map((row, i) => (
          <li key={i} className="py-3 first:pt-0 last:pb-0">
            <SourceCitationList
              signal={row.insight}
              subtext={row.implication}
              sources={row.sources}
            />
          </li>
        ))}
      </ul>
    </SummaryContentBox>
  );
}
