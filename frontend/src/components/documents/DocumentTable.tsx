"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { DocumentActionsMenu } from "@/components/documents/DocumentActionsMenu";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Pagination, paginateSlice } from "@/components/ui/Pagination";
import type { DocumentListItem } from "@/lib/types/document";
import { ACTIVE_STAGES } from "@/lib/types/document";

const PAGE_SIZE = 10;

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

type StatusFilter = "all" | "ready" | "processing" | "failed";

const FILTERS: { id: StatusFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "ready", label: "Ready" },
  { id: "processing", label: "In progress" },
  { id: "failed", label: "Failed" },
];

function matchesFilter(doc: DocumentListItem, filter: StatusFilter): boolean {
  if (filter === "all") return true;
  if (filter === "ready") return doc.status === "completed";
  if (filter === "failed") return doc.status === "failed";
  return (
    doc.status === "queued" || ACTIVE_STAGES.includes(doc.status)
  );
}

function CellText({
  children,
  title,
  muted = false,
}: {
  children: React.ReactNode;
  title?: string;
  muted?: boolean;
}) {
  return (
    <span
      className={`block truncate ${muted ? "text-ink-muted" : "text-ink"}`}
      title={title}
    >
      {children}
    </span>
  );
}

export function DocumentTable({
  documents,
  isLoading,
}: {
  documents: DocumentListItem[];
  isLoading?: boolean;
}) {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return [...documents]
      .filter((doc) => matchesFilter(doc, filter))
      .filter((doc) => {
        if (!q) return true;
        return (
          doc.original_filename.toLowerCase().includes(q) ||
          (doc.tender_reference ?? "").toLowerCase().includes(q) ||
          (doc.version_label ?? "").toLowerCase().includes(q)
        );
      })
      .sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );
  }, [documents, filter, query]);

  useEffect(() => {
    setPage(1);
  }, [filter, query]);

  const pageItems = useMemo(
    () => paginateSlice(filtered, page, PAGE_SIZE),
    [filtered, page]
  );

  const counts = useMemo(() => {
    const c = { all: documents.length, ready: 0, processing: 0, failed: 0 };
    for (const doc of documents) {
      if (doc.status === "completed") c.ready += 1;
      else if (doc.status === "failed") c.failed += 1;
      else if (
        doc.status === "queued" ||
        ACTIVE_STAGES.includes(doc.status)
      ) {
        c.processing += 1;
      }
    }
    return c;
  }, [documents]);

  if (isLoading) {
    return (
      <div className="h-56 w-full animate-pulse rounded-lg border border-surface-border bg-surface" />
    );
  }

  if (!documents.length) {
    return (
      <div className="w-full rounded-lg border border-dashed border-surface-border bg-surface px-6 py-16 text-center">
        <p className="text-sm font-medium text-ink">No documents yet</p>
        <p className="mt-1 text-sm text-ink-muted">
          Upload an RFQ or RFP PDF to start parsing and procurement analysis.
        </p>
        <Link
          href="/upload"
          className="mt-4 inline-block rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
        >
          Upload document
        </Link>
      </div>
    );
  }

  return (
    <div className="w-full min-w-0 space-y-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-wrap gap-1 rounded-lg border border-surface-border bg-surface p-1">
          {FILTERS.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setFilter(f.id)}
              className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
                filter === f.id
                  ? "bg-surface-muted text-ink"
                  : "text-ink-muted hover:text-ink"
              }`}
            >
              {f.label}
              <span className="ml-1 tabular-nums text-ink-muted">
                ({counts[f.id]})
              </span>
            </button>
          ))}
        </div>
        <input
          type="search"
          placeholder="Search file, tender, or version…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="w-full rounded-md border border-surface-border bg-surface px-3 py-2 text-sm outline-none ring-accent focus:ring-1 lg:max-w-sm"
        />
      </div>

      <Pagination
        page={page}
        pageSize={PAGE_SIZE}
        totalItems={filtered.length}
        onPageChange={setPage}
      />

      <div className="w-full overflow-hidden rounded-lg border border-surface-border bg-surface">
        {filtered.length === 0 ? (
          <p className="px-4 py-10 text-center text-sm text-ink-muted">
            No documents match this filter.
          </p>
        ) : (
          <table className="w-full table-fixed text-sm">
            <colgroup>
              <col className="w-[26%]" />
              <col className="w-[14%]" />
              <col className="w-[10%]" />
              <col className="w-[8%]" />
              <col className="w-[14%]" />
              <col className="w-[18%]" />
              <col className="w-[10%]" />
            </colgroup>
            <thead>
              <tr className="border-b border-surface-border bg-surface-muted/80 text-left text-[11px] font-semibold uppercase tracking-wide text-ink-muted">
                <th className="px-3 py-3 sm:px-4">Document</th>
                <th className="px-3 py-3 sm:px-4">Tender</th>
                <th className="px-3 py-3 sm:px-4">Version</th>
                <th className="px-3 py-3 sm:px-4">Size</th>
                <th className="px-3 py-3 sm:px-4">Status</th>
                <th className="px-3 py-3 sm:px-4">Uploaded</th>
                <th className="px-3 py-3 text-right sm:px-4">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border/80">
              {pageItems.map((doc) => (
                <tr
                  key={doc.id}
                  className="transition-colors hover:bg-surface-muted/40"
                >
                  <td className="px-3 py-3 sm:px-4">
                    <Link
                      href={`/documents/${doc.id}/summary`}
                      className="block truncate font-medium text-ink hover:text-accent"
                      title={doc.original_filename}
                    >
                      {doc.original_filename}
                    </Link>
                  </td>
                  <td className="px-3 py-3 sm:px-4">
                    <CellText
                      title={doc.tender_reference ?? undefined}
                      muted
                    >
                      {doc.tender_reference ?? "—"}
                    </CellText>
                  </td>
                  <td className="px-3 py-3 sm:px-4">
                    <CellText title={doc.version_label ?? undefined} muted>
                      {doc.version_label ?? "—"}
                    </CellText>
                  </td>
                  <td className="px-3 py-3 sm:px-4">
                    <CellText muted>{formatBytes(doc.size_bytes)}</CellText>
                  </td>
                  <td className="px-3 py-3 sm:px-4">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-3 py-3 sm:px-4">
                    <CellText title={formatDate(doc.created_at)} muted>
                      {formatDate(doc.created_at)}
                    </CellText>
                  </td>
                  <td className="px-3 py-3 text-right sm:px-4">
                    <DocumentActionsMenu doc={doc} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {filtered.length > PAGE_SIZE && (
        <Pagination
          page={page}
          pageSize={PAGE_SIZE}
          totalItems={filtered.length}
          onPageChange={setPage}
        />
      )}
    </div>
  );
}
