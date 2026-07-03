"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { DashboardStats } from "@/components/dashboard/DashboardStats";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { listDocuments } from "@/lib/api/documents";
import { ACTIVE_STAGES } from "@/lib/types/document";

export default function DashboardPage() {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["documents"],
    queryFn: () => listDocuments(),
    refetchInterval: (query) => {
      const docs = query.state.data?.results ?? [];
      const hasActive = docs.some(
        (d) => d.status === "queued" || ACTIVE_STAGES.includes(d.status)
      );
      return hasActive ? 5000 : false;
    },
  });

  const documents = data?.results ?? [];

  return (
    <div className="flex w-full flex-col gap-6">
      <div className="flex flex-col gap-4 border-b border-surface-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <h2 className="text-2xl font-semibold tracking-tight text-ink">
            Dashboard
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-ink-muted">
            Upload tender documents and open procurement briefings when they are
            ready.
          </p>
        </div>
        <Link
          href="/upload"
          className="inline-flex shrink-0 items-center justify-center rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover"
        >
          Upload document
        </Link>
      </div>

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {(error as Error).message}
        </div>
      )}

      {isPending ? (
        <div className="grid w-full gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-24 animate-pulse rounded-lg border border-surface-border bg-surface"
            />
          ))}
        </div>
      ) : (
        documents.length > 0 && <DashboardStats documents={documents} />
      )}

      <section className="w-full min-w-0">
        <div className="mb-4 flex items-center justify-between gap-3">
          <h3 className="text-sm font-semibold text-ink">Documents</h3>
          {!isPending && documents.length > 0 && (
            <span className="text-xs text-ink-muted">
              {documents.length} total
            </span>
          )}
        </div>
        <DocumentTable documents={documents} isLoading={isPending} />
      </section>
    </div>
  );
}
