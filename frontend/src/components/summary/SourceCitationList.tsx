"use client";

import { useState } from "react";

import {
  canHighlightInPdf,
  isJumpableCitation,
  normalizeCitationPage,
} from "@/lib/citationUtils";
import { usePdfNavigation } from "@/lib/pdfNavigationContext";
import type { SourceCitation } from "@/lib/types/intelligence";

function QuoteIcon() {
  return (
    <svg
      className="h-3 w-3 shrink-0 text-ink-muted/50"
      viewBox="0 0 12 12"
      fill="currentColor"
      aria-hidden
    >
      <path d="M1 3.5C1 2.67 1.67 2 2.5 2h2C5.33 2 6 2.67 6 3.5v2C6 6.33 5.33 7 4.5 7H3.5L2 9.5V7H2.5C1.67 7 1 6.33 1 5.5v-2zm6 0C7 2.67 7.67 2 8.5 2h2c.83 0 1.5.67 1.5 1.5v2c0 .83-.67 1.5-1.5 1.5H9.5L8 9.5V7H8.5C7.67 7 7 6.33 7 5.5v-2z" />
    </svg>
  );
}

function PageBadge({
  page,
  isActive,
  canJump,
  onJump,
}: {
  page: number;
  isActive: boolean;
  canJump: boolean;
  onJump: () => void;
}) {
  const [flashed, setFlashed] = useState(false);

  function handleClick() {
    if (!canJump) return;
    onJump();
    setFlashed(true);
    setTimeout(() => setFlashed(false), 1000);
  }

  const tooltip = !canJump
    ? "Preview not available for this file type"
    : page === 1
      ? "Jump to section in document preview"
      : `Jump to page ${page} in preview`;

  return (
    <div className="flex items-center gap-1">
      <span
        className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-medium tabular-nums transition-colors ${
          isActive
            ? "border-accent/30 bg-accent/10 text-accent"
            : "border-surface-border bg-surface-muted text-ink-muted"
        }`}
      >
        p.{page}
      </span>
      <button
        type="button"
        title={tooltip}
        aria-label={tooltip}
        disabled={!canJump}
        onClick={handleClick}
        className={`flex h-5 w-5 items-center justify-center rounded-full border transition-all ${
          !canJump
            ? "cursor-not-allowed border-surface-border bg-surface-muted text-ink-muted/40"
            : flashed
              ? "border-accent bg-accent text-white"
              : isActive
                ? "border-accent/40 bg-accent/10 text-accent hover:bg-accent hover:text-white"
                : "border-surface-border bg-surface text-ink-muted hover:border-accent/40 hover:bg-accent/10 hover:text-accent"
        }`}
      >
        <svg
          className="h-2.5 w-2.5"
          viewBox="0 0 10 10"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden
        >
          <path d="M2 5h6M5.5 2.5L8 5l-2.5 2.5" />
        </svg>
      </button>
    </div>
  );
}

export function CitationPanel({ sources }: { sources: SourceCitation[] }) {
  const { activeHighlight, jumpToCitation, canJump } = usePdfNavigation();

  return (
    <div className="mt-3 space-y-2">
      {sources.map((src, i) => {
        const jumpable = isJumpableCitation(src);
        const page = normalizeCitationPage(src.page);
        const activePage = normalizeCitationPage(activeHighlight?.page);
        const quote = src.source_text?.trim();
        const activeQuote = activeHighlight?.sourceText?.trim();
        const isActive =
          jumpable &&
          (quote && activeQuote
            ? activeQuote === quote ||
              activeQuote.startsWith(quote.slice(0, 48)) ||
              quote.startsWith(activeQuote.slice(0, 48))
            : page != null && activePage === page);
        return (
          <div
            key={i}
            className={`rounded-lg border px-3 py-2.5 transition-colors ${
              isActive
                ? "border-accent/30 bg-accent/5"
                : "border-surface-border bg-surface-muted/60"
            }`}
          >
            {/* Header: section + page badge */}
            <div className="flex flex-wrap items-start justify-between gap-x-3 gap-y-1">
              <div className="min-w-0 flex-1">
                {src.section && (
                  <p className="text-xs font-semibold leading-snug text-ink">
                    {src.section}
                  </p>
                )}
                {src.section_path && src.section_path !== src.section && (
                  <p className="mt-0.5 truncate text-[10px] leading-none text-ink-muted">
                    {src.section_path}
                  </p>
                )}
                {!src.section && !src.section_path && (
                  <p className="text-xs font-semibold text-ink-muted">
                    Source {i + 1}
                  </p>
                )}
              </div>
              {page != null && (
                <PageBadge
                  page={page}
                  isActive={isActive}
                  canJump={canJump && jumpable}
                  onJump={() =>
                    jumpToCitation({
                      page,
                      sourceText: canHighlightInPdf(src)
                        ? src.source_text
                        : undefined,
                    })
                  }
                />
              )}
            </div>

            {/* Quote */}
            {src.source_text && (
              <div className="mt-2 flex items-start gap-1.5 border-t border-surface-border pt-2">
                <QuoteIcon />
                <p className="text-[11px] leading-relaxed text-ink-muted">
                  <span className="italic">
                    {src.source_text.slice(0, 240)}
                    {src.source_text.length > 240 ? "…" : ""}
                  </span>
                </p>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function CitationToggle({
  open,
  count,
  onToggle,
}: {
  open: boolean;
  count: number;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      className="inline-flex items-center gap-1.5 rounded-full border border-surface-border bg-surface px-2.5 py-1 text-[11px] font-medium text-ink-muted transition-colors hover:border-accent/40 hover:bg-accent/5 hover:text-accent"
    >
      <svg
        className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}
        viewBox="0 0 12 12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        aria-hidden
      >
        <path d="M2 4l4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      {open ? "Hide sources" : `${count} source${count !== 1 ? "s" : ""}`}
    </button>
  );
}

export function SourceCitationList({
  sources,
  signal,
  subtext,
}: {
  sources?: SourceCitation[];
  signal?: string;
  subtext?: string;
}) {
  const [open, setOpen] = useState(false);

  if (!sources?.length && !signal) return null;

  const hasCitations = Boolean(sources?.length);

  if (signal) {
    return (
      <div>
        <div className="flex items-start gap-4">
          <div className="w-[70%] min-w-0">
            <p className="text-justify text-sm leading-relaxed text-ink">
              {signal}
            </p>
            {subtext && (
              <p className="mt-1 text-xs leading-relaxed text-ink-muted">
                {subtext}
              </p>
            )}
          </div>
          {hasCitations && (
            <div className="flex w-[30%] min-w-[7.5rem] shrink-0 justify-end">
              <CitationToggle
                open={open}
                count={sources!.length}
                onToggle={() => setOpen((v) => !v)}
              />
            </div>
          )}
        </div>
        {open && hasCitations && <CitationPanel sources={sources!} />}
      </div>
    );
  }

  if (!hasCitations) return null;

  return (
    <div className="mt-2">
      <CitationToggle
        open={open}
        count={sources!.length}
        onToggle={() => setOpen((v) => !v)}
      />
      {open && <CitationPanel sources={sources!} />}
    </div>
  );
}
