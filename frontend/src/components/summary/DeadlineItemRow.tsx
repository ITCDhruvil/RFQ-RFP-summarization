"use client";

import { useState } from "react";

import { deadlineDisplayLabel, resolveDeadlineDisplay } from "@/lib/deadlineDisplay";
import type { ExtractedInsightItem, SourceCitation, SummarySectionBlock } from "@/lib/types/intelligence";

import { CitationPanel, CitationToggle } from "./SourceCitationList";

type DeadlineInput = SummarySectionBlock | ExtractedInsightItem;

function toDisplayInput(item: DeadlineInput, sources?: SourceCitation[]) {
  if ("requirement" in item && item.requirement) {
    return {
      requirement: item.requirement,
      date_time: item.date_time,
      value: item.value,
      sourceText: item.source_text,
      sources,
    };
  }
  const block = item as SummarySectionBlock;
  return {
    text: block.text,
    item: block.item,
    date: block.date,
    sources: block.sources ?? sources,
  };
}

export function DeadlineItemRow({
  item,
  index,
  sources,
  showSources = false,
}: {
  item: DeadlineInput;
  index: number;
  sources?: SourceCitation[];
  showSources?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const citSources =
    sources ??
    ("sources" in item ? item.sources : undefined) ??
    ("source_text" in item && item.source_text
      ? [
          {
            page: "page" in item ? item.page : undefined,
            section: "section" in item ? item.section : undefined,
            section_path: "section_path" in item ? item.section_path : undefined,
            source_text: item.source_text,
          },
        ]
      : undefined);

  const { label, value } = resolveDeadlineDisplay(toDisplayInput(item, citSources));
  const displayLabel = deadlineDisplayLabel(label);
  const hasCitations = Boolean(citSources?.length);

  return (
    <li className="py-3 first:pt-0 last:pb-0">
      <div className="flex items-start gap-2.5">
        <span
          className="w-5 shrink-0 pt-0.5 text-right text-xs font-medium tabular-nums text-ink-muted"
          aria-hidden
        >
          {index + 1}.
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-4">
            <div className="w-[70%] min-w-0">
              <p className="text-sm font-medium text-ink">{displayLabel}</p>
              {value ? (
                <p className="mt-1 text-sm leading-relaxed text-ink-muted">
                  {value}
                </p>
              ) : (
                <p className="mt-1 text-xs italic text-ink-muted">
                  See citation for details
                </p>
              )}
            </div>
            {hasCitations && (
              <div className="flex w-[30%] min-w-[7.5rem] shrink-0 justify-end">
                <CitationToggle
                  open={open}
                  count={citSources!.length}
                  onToggle={() => setOpen((v) => !v)}
                />
              </div>
            )}
          </div>
          {open && hasCitations && <CitationPanel sources={citSources!} />}
        </div>
      </div>
    </li>
  );
}
