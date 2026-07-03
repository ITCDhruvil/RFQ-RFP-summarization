"use client";

import { SourceCitationList } from "@/components/summary/SourceCitationList";
import { SummaryContentBox } from "@/components/summary/SummaryContentBox";
import { groupSubmissionChecklist } from "@/lib/submissionChecklist";
import type { SummarySectionBlock } from "@/lib/types/intelligence";

export function SubmissionChecklistView({
  items,
  showSources = false,
}: {
  items: SummarySectionBlock[];
  showSources?: boolean;
}) {
  const groups = groupSubmissionChecklist(items);
  if (!groups.length) return null;

  return (
    <SummaryContentBox>
      <div className="divide-y divide-surface-border/70">
        {groups.map((group) => (
          <section key={group.category} className="py-4 first:pt-0 last:pb-0">
            <h5 className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-ink-muted">
              {group.label}
            </h5>
            <ol className="space-y-2.5">
              {group.items.map((entry, index) => {
                const label = entry.item || entry.text || "—";
                return (
                  <li
                    key={`${group.category}-${index}`}
                    className="flex items-start gap-2.5"
                  >
                    <span
                      className="w-5 shrink-0 pt-0.5 text-center text-sm text-ink-muted"
                      aria-hidden
                    >
                      ☐
                    </span>
                    <span
                      className="w-5 shrink-0 pt-0.5 text-right text-xs font-medium tabular-nums text-ink-muted"
                      aria-hidden
                    >
                      {index + 1}.
                    </span>
                    <div className="min-w-0 flex-1">
                      <SourceCitationList
                        signal={label}
                        sources={entry.sources}
                      />
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        ))}
      </div>
    </SummaryContentBox>
  );
}
