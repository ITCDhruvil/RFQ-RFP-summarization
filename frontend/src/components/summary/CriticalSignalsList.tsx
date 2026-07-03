"use client";

import { SourceCitationList } from "@/components/summary/SourceCitationList";
import { SummaryContentBox } from "@/components/summary/SummaryContentBox";
import {
  groupSignalsByPriority,
  PRIORITY_SECTIONS,
  prioritySectionLabel,
} from "@/lib/signalPriority";
import type { ProcurementSignal } from "@/lib/types/intelligence";

export function CriticalSignalsList({ signals }: { signals: ProcurementSignal[] }) {
  const groups = groupSignalsByPriority(signals);

  return (
    <div className="space-y-4">
      {PRIORITY_SECTIONS.map((level) => {
        const items = groups[level];
        if (!items.length) return null;

        return (
          <SummaryContentBox key={level} className="mb-0">
            <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-ink-muted">
              {prioritySectionLabel(level)}
            </h4>
            <ul className="divide-y divide-surface-border/80">
              {items.map((s, i) => (
                <li key={i} className="py-3 first:pt-0 last:pb-0">
                  <SourceCitationList
                    signal={s.signal}
                    sources={s.sources}
                  />
                </li>
              ))}
            </ul>
          </SummaryContentBox>
        );
      })}
    </div>
  );
}
