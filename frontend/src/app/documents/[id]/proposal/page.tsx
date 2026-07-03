"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { DocumentHeaderActions } from "@/components/documents/DocumentHeaderActions";
import { DocumentPreview } from "@/components/documents/DocumentPreview";
import { StopProcessingButton } from "@/components/documents/SimpleProcessingCard";
import { SplitPanelLayout } from "@/components/layout/SplitPanelLayout";
import {
  BidderProfileForm,
  hasBidderProfileContent,
  sanitizeBidderProfile,
} from "@/components/proposal/BidderProfileForm";
import { ProposalViewer } from "@/components/proposal/ProposalViewer";
import { getDocument } from "@/lib/api/documents";
import {
  cancelProposal,
  generateProposal,
  getProposal,
  getProposalStatus,
  startNewProposal,
} from "@/lib/api/proposal";
import { getSummaryStatus } from "@/lib/api/intelligence";
import { useCachedDocumentMeta } from "@/lib/documentMetaCache";
import { PdfNavigationProvider } from "@/lib/pdfNavigationContext";
import type { BidderProfile } from "@/lib/types/proposal";
import { EMPTY_BIDDER_PROFILE } from "@/lib/types/proposal";

function generationSessionKey(documentId: string) {
  return `proposal-generation-active:${documentId}`;
}

export default function ProposalPage() {
  const params = useParams();
  const documentId = String(params.id);
  const queryClient = useQueryClient();
  const [bidderProfile, setBidderProfile] = useState<BidderProfile>(EMPTY_BIDDER_PROFILE);
  const [stopRequested, setStopRequested] = useState(false);
  const [generationStarted, setGenerationStarted] = useState(false);
  const profileRef = useRef(bidderProfile);

  useEffect(() => {
    profileRef.current = bidderProfile;
  }, [bidderProfile]);

  useEffect(() => {
    setGenerationStarted(
      sessionStorage.getItem(generationSessionKey(documentId)) === "1"
    );
  }, [documentId]);

  const documentQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
  });

  const summaryStatusQuery = useQuery({
    queryKey: ["summary-status", documentId],
    queryFn: () => getSummaryStatus(documentId),
  });

  const statusQuery = useQuery({
    queryKey: ["proposal-status", documentId],
    queryFn: () => getProposalStatus(documentId),
    refetchInterval: (q) => {
      const st = q.state.data?.proposal_status;
      if (st === "processing" || stopRequested) return 1000;
      return false;
    },
  });

  const proposalQuery = useQuery({
    queryKey: ["proposal", documentId],
    queryFn: () => getProposal(documentId),
    enabled: statusQuery.data?.proposal_status === "completed",
    retry: false,
  });

  const { cachedMeta } = useCachedDocumentMeta(documentId);

  const markGenerationStarted = () => {
    sessionStorage.setItem(generationSessionKey(documentId), "1");
    setGenerationStarted(true);
    setStopRequested(false);
  };

  const clearGenerationSession = () => {
    sessionStorage.removeItem(generationSessionKey(documentId));
    setGenerationStarted(false);
  };

  const generateMutation = useMutation({
    mutationFn: () =>
      generateProposal(
        documentId,
        sanitizeBidderProfile(profileRef.current),
        false
      ),
    onMutate: () => {
      markGenerationStarted();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["proposal-status", documentId] });
    },
  });

  const startNewMutation = useMutation({
    mutationFn: () =>
      startNewProposal(documentId, sanitizeBidderProfile(profileRef.current)),
    onMutate: () => {
      queryClient.setQueryData(
        ["proposal-status", documentId],
        (prev: Awaited<ReturnType<typeof getProposalStatus>> | undefined) =>
          prev
            ? {
                ...prev,
                proposal_status: "pending",
                error_message: null,
              }
            : prev
      );
    },
    onSuccess: () => {
      clearGenerationSession();
      setStopRequested(false);
      queryClient.removeQueries({ queryKey: ["proposal", documentId] });
      queryClient.invalidateQueries({ queryKey: ["proposal-status", documentId] });
      generateMutation.reset();
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelProposal(documentId),
    onMutate: () => {
      setStopRequested(true);
      queryClient.setQueryData(
        ["proposal-status", documentId],
        (prev: Awaited<ReturnType<typeof getProposalStatus>> | undefined) =>
          prev
            ? {
                ...prev,
                proposal_status: "failed",
                error_message: "Cancelled by user.",
              }
            : prev
      );
    },
    onSettled: async () => {
      await queryClient.refetchQueries({ queryKey: ["proposal-status", documentId] });
      queryClient.invalidateQueries({ queryKey: ["proposal", documentId] });
      generateMutation.reset();
      clearGenerationSession();
    },
    onError: () => {
      setStopRequested(false);
      queryClient.invalidateQueries({ queryKey: ["proposal-status", documentId] });
    },
  });

  useEffect(() => {
    if (statusQuery.data?.proposal_status === "completed") {
      queryClient.invalidateQueries({ queryKey: ["proposal", documentId] });
      setStopRequested(false);
      clearGenerationSession();
    }
  }, [statusQuery.data?.proposal_status, documentId, queryClient]);

  const resolvedFilename =
    documentQuery.data?.original_filename ??
    cachedMeta?.original_filename ??
    "Your document";
  const resolvedMimeType =
    documentQuery.data?.mime_type ?? cachedMeta?.mime_type;

  const briefingReady = summaryStatusQuery.data?.summary_status === "completed";
  const proposalStatus = statusQuery.data?.proposal_status;
  const isCompleted = proposalStatus === "completed";
  const isProcessing = proposalStatus === "processing";
  const showUserProgress =
    generationStarted &&
    !stopRequested &&
    (generateMutation.isPending || isProcessing);
  const hasOrphanedProcessing =
    isProcessing && !generationStarted && !generateMutation.isPending;
  const wasCancelled =
    proposalStatus === "failed" &&
    statusQuery.data?.error_message === "Cancelled by user.";
  const profileReady = hasBidderProfileContent(bidderProfile);
  const showSetupForm = briefingReady && !isCompleted;

  const pageHeader = (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <Link
          href={`/documents/${documentId}/summary`}
          className="text-xs text-ink-muted hover:text-ink"
        >
          ← Back to briefing
        </Link>
        <h2 className="mt-2 text-2xl font-semibold tracking-tight">
          Technical proposal draft
        </h2>
        <p className="mt-1 text-sm text-ink-muted">{resolvedFilename}</p>
      </div>
      {briefingReady && (
        <div className="flex flex-wrap items-center gap-2">
          <DocumentHeaderActions
            documentId={documentId}
            filename={resolvedFilename}
            showBriefingDownloads={false}
            currentProposal="technical"
          />
          {isCompleted && (
            <button
              type="button"
              onClick={() => startNewMutation.mutate()}
              disabled={
                showUserProgress ||
                hasOrphanedProcessing ||
                startNewMutation.isPending
              }
              className="rounded-md border border-surface-border px-3 py-2 text-sm font-medium hover:bg-surface-muted disabled:opacity-50"
            >
              {startNewMutation.isPending ? "Starting…" : "New proposal"}
            </button>
          )}
        </div>
      )}
    </div>
  );

  const proposalPanel = (
    <div className="space-y-6">
      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        AI-generated draft for internal review only. Verify all facts, pricing, and
        legal commitments before submission.
      </div>

      {!briefingReady && (
        <div className="rounded-md border border-surface-border bg-surface px-4 py-3 text-sm text-ink-muted">
          A completed procurement briefing is required before generating a proposal.{" "}
          <Link
            href={`/documents/${documentId}/summary`}
            className="font-medium text-accent hover:underline"
          >
            View briefing status
          </Link>
        </div>
      )}

      {hasOrphanedProcessing && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p>
              A proposal draft is already generating from an earlier attempt. Stop
              it to fill in your bidder profile and start fresh.
            </p>
            <StopProcessingButton
              onStop={() => {
                if (!cancelMutation.isPending) {
                  cancelMutation.mutate();
                }
              }}
            />
          </div>
        </div>
      )}

      {showSetupForm && (
        <>
          {wasCancelled && (
            <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              Proposal generation was stopped. Update your bidder profile and try
              again when ready.
            </div>
          )}

          <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <strong>Ready-to-use demo:</strong> click{" "}
            <strong>Fill with sample data</strong>, then{" "}
            <strong>Generate technical proposal</strong>. For a complete bid pack,
            also open <strong>Commercial proposal</strong>, fill sample data, apply
            to pricing, and generate.
          </div>

          {proposalStatus === "failed" && !wasCancelled && (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
              {statusQuery.data?.error_message ??
                "Proposal generation failed. Update your profile and try again."}
            </div>
          )}

          <BidderProfileForm
            onChange={setBidderProfile}
            disabled={showUserProgress || hasOrphanedProcessing}
          />

          {!profileReady && (
            <p className="text-xs text-ink-muted">
              Add your company details above before generating. You can also use
              &ldquo;Fill with sample data&rdquo; to test quickly.
            </p>
          )}

          <button
            type="button"
            onClick={() => generateMutation.mutate()}
            disabled={
              showUserProgress ||
              hasOrphanedProcessing ||
              generateMutation.isPending ||
              !profileReady
            }
            className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
          >
            {generateMutation.isPending
              ? "Starting generation…"
              : "Generate technical proposal"}
          </button>
        </>
      )}

      {showUserProgress && (
        <div className="rounded-lg border border-surface-border bg-surface p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="h-2.5 w-2.5 animate-pulse rounded-full bg-accent" />
              <p className="text-sm font-medium">Generating proposal draft…</p>
            </div>
            {isProcessing && (
              <StopProcessingButton
                onStop={() => {
                  if (!cancelMutation.isPending) {
                    cancelMutation.mutate();
                  }
                }}
              />
            )}
          </div>
          <p className="mt-2 text-xs text-ink-muted">
            This typically takes 30–90 seconds. The page will update automatically.
          </p>
        </div>
      )}

      {stopRequested && cancelMutation.isPending && (
        <p className="text-xs text-ink-muted">Stopping generation…</p>
      )}

      {startNewMutation.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {(startNewMutation.error as Error).message}
        </div>
      )}

      {generateMutation.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {(generateMutation.error as Error).message}
        </div>
      )}

      {isCompleted && proposalQuery.data && (
        <ProposalViewer data={proposalQuery.data.proposal_json} />
      )}

      {isCompleted && proposalQuery.isPending && (
        <p className="text-sm text-ink-muted">Loading proposal…</p>
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
        left={proposalPanel}
        right={previewPanel}
      />
    </PdfNavigationProvider>
  );
}
