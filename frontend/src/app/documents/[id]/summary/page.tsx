"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { SimpleProcessingCard } from "@/components/documents/SimpleProcessingCard";
import { DocumentPreview } from "@/components/documents/DocumentPreview";
import { DocumentHeaderActions } from "@/components/documents/DocumentHeaderActions";
import { SplitPanelLayout } from "@/components/layout/SplitPanelLayout";
import { PdfNavigationProvider } from "@/lib/pdfNavigationContext";
import { InsightsViewer } from "@/components/summary/InsightsViewer";
import { SummaryViewer } from "@/components/summary/SummaryViewer";
import { getDocument, kickDocumentProcessing } from "@/lib/api/documents";
import {
  useCachedDocumentMeta,
} from "@/lib/documentMetaCache";
import {
  cancelSummary,
  generateSummary,
  getSummary,
  getSummaryStatus,
  listInsights,
  regenerateSummary,
} from "@/lib/api/intelligence";
import { resolveUserProcessingPhase } from "@/lib/userFacingStatus";

const PROCESSING_STAGES = [
  "chunking_processing",
  "embedding_processing",
  "extraction_processing",
  "summary_processing",
];

export default function SummaryPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = String(params.id);
  const queryClient = useQueryClient();
  const autoGenerateStarted = useRef(false);
  const kickStarted = useRef(false);
  const queuedSince = useRef<number | null>(null);
  const { cachedMeta, persistMeta } = useCachedDocumentMeta(documentId);

  const documentQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
  });

  useEffect(() => {
    const doc = documentQuery.data;
    if (!doc?.original_filename || !doc.mime_type) return;
    persistMeta({
      original_filename: doc.original_filename,
      mime_type: doc.mime_type,
    });
  }, [documentId, documentQuery.data, persistMeta]);

  const statusQuery = useQuery({
    queryKey: ["summary-status", documentId],
    queryFn: () => getSummaryStatus(documentId),
    refetchInterval: (q) => {
      const data = q.state.data;
      const st = data?.summary_status;
      const docSt = data?.document_status;
      if (st === "completed" || st === "failed") {
        return docSt === "completed" ? false : 3000;
      }
      if (
        st === "processing" ||
        PROCESSING_STAGES.includes(data?.progress_stage ?? "") ||
        docSt !== "completed"
      ) {
        return 3000;
      }
      return false;
    },
  });

  const summaryQuery = useQuery({
    queryKey: ["summary", documentId],
    queryFn: () => getSummary(documentId),
    enabled: statusQuery.data?.summary_status === "completed",
    retry: false,
  });

  const insightsQuery = useQuery({
    queryKey: ["insights", documentId],
    queryFn: () => listInsights(documentId),
    enabled: statusQuery.data?.summary_status === "completed",
  });

  const generateMutation = useMutation({
    mutationFn: () => generateSummary(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["summary-status", documentId] });
    },
  });

  const regenerateMutation = useMutation({
    mutationFn: () => regenerateSummary(documentId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["summary-status", documentId] });
      queryClient.invalidateQueries({ queryKey: ["summary", documentId] });
      queryClient.invalidateQueries({ queryKey: ["insights", documentId] });
      if (data && "sync" in data && (data as { sync?: boolean }).sync) {
        queryClient.refetchQueries({ queryKey: ["summary-status", documentId] });
      }
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelSummary(documentId),
    onSettled: () => {
      // Bust the document list cache so the dashboard badge shows "Failed"
      // immediately without waiting for the next 5 s poll.
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["summary-status", documentId] });
      router.push("/");
    },
  });

  useEffect(() => {
    if (statusQuery.data?.summary_status === "completed") {
      queryClient.invalidateQueries({ queryKey: ["summary", documentId] });
      queryClient.invalidateQueries({ queryKey: ["insights", documentId] });
    }
  }, [statusQuery.data?.summary_status, documentId, queryClient]);

  const docStatus = statusQuery.data?.document_status;
  const summaryStatus = statusQuery.data?.summary_status;
  const isWorking =
    regenerateMutation.isPending ||
    generateMutation.isPending ||
    summaryStatus === "processing" ||
    PROCESSING_STAGES.includes(statusQuery.data?.progress_stage ?? "") ||
    (docStatus === "completed" &&
      summaryStatus !== "completed" &&
      summaryStatus !== "failed");

  const hasSummary = summaryStatus === "completed";
  const phase = resolveUserProcessingPhase(docStatus, summaryStatus, {
    summaryStarting: generateMutation.isPending || regenerateMutation.isPending,
  });

  useEffect(() => {
    if (autoGenerateStarted.current) return;
    if (!statusQuery.data) return;
    if (docStatus !== "completed") return;
    if (summaryStatus === "completed" || summaryStatus === "processing") return;

    autoGenerateStarted.current = true;
    generateMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- run once when parse completes
  }, [docStatus, summaryStatus, statusQuery.data]);

  useEffect(() => {
    if (docStatus !== "queued" && docStatus !== "uploaded") {
      queuedSince.current = null;
      return;
    }
    if (queuedSince.current === null) {
      queuedSince.current = Date.now();
    }
    if (kickStarted.current) return;

    const elapsed = Date.now() - (queuedSince.current ?? Date.now());
    if (elapsed < 12000) return;

    kickStarted.current = true;
    kickDocumentProcessing(documentId)
      .then(() => {
        queryClient.invalidateQueries({ queryKey: ["summary-status", documentId] });
        queryClient.invalidateQueries({ queryKey: ["document-status", documentId] });
      })
      .catch(() => {
        kickStarted.current = false;
      });
  }, [docStatus, documentId, queryClient]);

  const resolvedFilename =
    documentQuery.data?.original_filename ??
    cachedMeta?.original_filename ??
    "Your document";
  const resolvedMimeType =
    documentQuery.data?.mime_type ?? cachedMeta?.mime_type;

  const pageHeader = (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <Link href="/" className="text-xs text-ink-muted hover:text-ink">
          ← Dashboard
        </Link>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">
          Procurement briefing
        </h2>
        <p className="mt-1 text-sm text-ink-muted">{resolvedFilename}</p>
      </div>
      {hasSummary && (
        <DocumentHeaderActions
          documentId={documentId}
          filename={resolvedFilename}
        />
      )}
    </div>
  );

  const briefingPanel = (
    <div className="space-y-6">
      {(generateMutation.isError || regenerateMutation.isError) && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {(generateMutation.error ?? regenerateMutation.error)?.message}
        </div>
      )}

      {statusQuery.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {(statusQuery.error as Error).message}
        </div>
      )}

      {statusQuery.isPending && !statusQuery.isError && (
        <div className="rounded-lg border border-surface-border bg-surface p-6">
          <div className="flex items-center gap-3">
            <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-surface-muted" />
            <div className="h-4 w-48 animate-pulse rounded bg-surface-muted" />
          </div>
          <div className="mt-5 h-1.5 w-full animate-pulse rounded-full bg-surface-muted" />
        </div>
      )}

      {!hasSummary && !statusQuery.isPending && (
        <SimpleProcessingCard
          documentStatus={docStatus}
          summaryStatus={summaryStatus}
          summaryStarting={
            generateMutation.isPending || regenerateMutation.isPending
          }
          waitingToStart={
            (docStatus === "queued" || docStatus === "uploaded") &&
            kickStarted.current
          }
          progressStage={statusQuery.data?.progress_stage}
          errorMessage={statusQuery.data?.error_message}
          onStop={() => cancelMutation.mutate()}
        />
      )}

      {summaryStatus === "failed" && (() => {
        const wasCancelled = statusQuery.data?.error_message
          ?.toLowerCase()
          .includes("cancel");
        return (
          <div
            className={`flex flex-wrap items-center gap-3 rounded-md border px-4 py-3 text-sm ${
              wasCancelled
                ? "border-surface-border bg-surface text-ink-muted"
                : "border-red-200 bg-red-50 text-red-800"
            }`}
          >
            <p className="flex-1">
              {wasCancelled
                ? "Processing was stopped. You can restart from the beginning."
                : (statusQuery.data?.error_message ??
                  "We could not build the briefing for this document.")}
            </p>
            <button
              type="button"
              onClick={() => {
                autoGenerateStarted.current = false;
                kickStarted.current = false;
                queryClient.invalidateQueries({ queryKey: ["summary-status", documentId] });
                kickDocumentProcessing(documentId)
                  .then(() => {
                    queryClient.invalidateQueries({ queryKey: ["summary-status", documentId] });
                    queryClient.invalidateQueries({ queryKey: ["document", documentId] });
                  })
                  .catch(() => {
                    autoGenerateStarted.current = false;
                    generateMutation.mutate();
                  });
              }}
              disabled={generateMutation.isPending}
              className={`rounded-md px-3 py-1.5 text-sm font-medium ring-1 disabled:opacity-50 ${
                wasCancelled
                  ? "bg-surface-muted text-ink ring-surface-border hover:bg-surface"
                  : "bg-white text-red-900 ring-red-200 hover:bg-red-50"
              }`}
            >
              {generateMutation.isPending
                ? "Starting…"
                : wasCancelled
                  ? "Restart processing"
                  : "Try again"}
            </button>
          </div>
        );
      })()}

      {hasSummary && summaryQuery.isPending && (
        <p className="text-sm text-ink-muted">Loading your briefing…</p>
      )}

      {hasSummary && summaryQuery.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {(summaryQuery.error as Error).message}
        </div>
      )}

      {summaryQuery.data && (
        <>
          <SummaryViewer data={summaryQuery.data.summary_json} />
          <section>
            <h3 className="mb-3 text-lg font-semibold tracking-tight">
              Key requirements & deadlines
            </h3>
            <InsightsViewer insights={insightsQuery.data ?? []} />
          </section>
        </>
      )}

      {hasSummary && (
        <details className="rounded-lg border border-surface-border bg-surface">
          <summary className="cursor-pointer px-4 py-3 text-sm font-medium text-ink-muted hover:text-ink">
            Advanced options
          </summary>
          <div className="border-t border-surface-border px-4 py-3">
            <button
              type="button"
              onClick={() => regenerateMutation.mutate()}
              disabled={isWorking}
              className="rounded-md border border-surface-border px-3 py-1.5 text-sm font-medium hover:bg-surface-muted disabled:opacity-50"
            >
              {regenerateMutation.isPending
                ? "Regenerating briefing…"
                : "Regenerate briefing"}
            </button>
            <p className="mt-2 text-xs text-ink-muted">
              Re-runs AI analysis. This can take several minutes.
            </p>
          </div>
        </details>
      )}

      {statusQuery.isPending && phase !== "ready" && (
        <p className="sr-only">Loading status…</p>
      )}
    </div>
  );

  const previewPanel = (
    <div className="h-full min-h-0">
      <DocumentPreview
        documentId={documentId}
        filename={resolvedFilename !== "Your document" ? resolvedFilename : undefined}
        mimeType={resolvedMimeType}
      />
    </div>
  );

  return (
    <PdfNavigationProvider>
      <SplitPanelLayout
        header={pageHeader}
        left={briefingPanel}
        right={previewPanel}
      />
    </PdfNavigationProvider>
  );
}
