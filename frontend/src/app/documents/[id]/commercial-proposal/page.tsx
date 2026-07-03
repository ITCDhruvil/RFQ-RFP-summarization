"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import { DocumentHeaderActions } from "@/components/documents/DocumentHeaderActions";
import { CommercialProposalViewer } from "@/components/commercial-proposal/CommercialProposalViewer";
import { CommercialQuestionnaire } from "@/components/commercial-proposal/CommercialQuestionnaire";
import { CommercialTermsForm } from "@/components/commercial-proposal/CommercialTermsForm";
import { CommercialVendorProfileForm } from "@/components/commercial-proposal/CommercialVendorProfileForm";
import { PricingTableEditor } from "@/components/commercial-proposal/PricingTableEditor";
import { DocumentPreview } from "@/components/documents/DocumentPreview";
import { StopProcessingButton } from "@/components/documents/SimpleProcessingCard";
import { SplitPanelLayout } from "@/components/layout/SplitPanelLayout";
import { computePricing } from "@/lib/commercialPricing";
import {
  cancelCommercialProposal,
  generateCommercialProposal,
  getCommercialProposal,
  getCommercialProposalStatus,
  prepareCommercialProposal,
  startNewCommercialProposal,
  updateCommercialPricing,
  updateCommercialTerms,
  validateCommercialProposal,
} from "@/lib/api/commercialProposal";
import { getDocument } from "@/lib/api/documents";
import { getSummaryStatus } from "@/lib/api/intelligence";
import { useCachedDocumentMeta } from "@/lib/documentMetaCache";
import { PdfNavigationProvider } from "@/lib/pdfNavigationContext";
import type {
  CommercialVendorProfile,
  ResourcePricingLine,
} from "@/lib/types/commercialProposal";
import { EMPTY_COMMERCIAL_VENDOR_PROFILE } from "@/lib/types/commercialProposal";

export default function CommercialProposalPage() {
  const params = useParams();
  const documentId = String(params.id);
  const queryClient = useQueryClient();
  const [vendorProfile, setVendorProfile] = useState<CommercialVendorProfile>(
    EMPTY_COMMERCIAL_VENDOR_PROFILE
  );
  const [answers, setAnswers] = useState<Record<string, string | number>>({});
  const [pricingLines, setPricingLines] = useState<ResourcePricingLine[]>([]);
  const [generationStarted, setGenerationStarted] = useState(false);
  const profileRef = useRef(vendorProfile);
  const prepareStarted = useRef(false);

  useEffect(() => {
    profileRef.current = vendorProfile;
  }, [vendorProfile]);

  const documentQuery = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => getDocument(documentId),
  });

  const summaryStatusQuery = useQuery({
    queryKey: ["summary-status", documentId],
    queryFn: () => getSummaryStatus(documentId),
  });

  const statusQuery = useQuery({
    queryKey: ["commercial-proposal-status", documentId],
    queryFn: () => getCommercialProposalStatus(documentId),
    refetchInterval: (q) =>
      q.state.data?.commercial_proposal_status === "processing" ? 2000 : false,
  });

  const briefingReady = summaryStatusQuery.data?.summary_status === "completed";
  const commercialStatus = statusQuery.data?.commercial_proposal_status;
  const isCompleted = commercialStatus === "completed";
  const isProcessing = commercialStatus === "processing";
  const showWorkbench = briefingReady && !isCompleted && !isProcessing;

  const syncProfileMutation = useMutation({
    mutationFn: (profile: CommercialVendorProfile) =>
      prepareCommercialProposal(documentId, profile),
    onSuccess: (data) => {
      queryClient.setQueryData(["commercial-proposal-draft", documentId], data);
      const wb = data.workbench;
      const vp = data.vendor_profile;
      setAnswers({
        ...(wb?.questionnaire_answers ?? {}),
        currency: vp?.currency ?? wb?.questionnaire_answers?.currency ?? "",
        default_gst_percent: vp?.default_gst_percent ?? 0,
        desired_margin_percent: vp?.default_margin_percent ?? 0,
        payment_terms_days: vp?.payment_terms_days ?? 0,
        price_validity_days: vp?.price_validity_days ?? 0,
      });
      setPricingLines(wb?.pricing?.resource_lines ?? []);
      if (vp) {
        setVendorProfile(vp);
      }
    },
  });

  const prepareMutation = useMutation({
    mutationFn: () => prepareCommercialProposal(documentId, profileRef.current),
    onSuccess: (data) => {
      queryClient.setQueryData(["commercial-proposal-draft", documentId], data);
      const wb = data.workbench;
      const vp = data.vendor_profile;
      setAnswers({
        ...(wb?.questionnaire_answers ?? {}),
        currency: vp?.currency ?? "",
        default_gst_percent: vp?.default_gst_percent ?? 0,
        desired_margin_percent: vp?.default_margin_percent ?? 0,
        payment_terms_days: vp?.payment_terms_days ?? 0,
        price_validity_days: vp?.price_validity_days ?? 0,
      });
      setPricingLines(wb?.pricing?.resource_lines ?? []);
      if (vp) {
        setVendorProfile(vp);
      }
    },
  });

  useEffect(() => {
    if (summaryStatusQuery.data?.summary_status !== "completed") return;
    if (prepareStarted.current) return;
    prepareStarted.current = true;
    prepareMutation.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summaryStatusQuery.data?.summary_status]);

  const saveTermsMutation = useMutation({
    mutationFn: () =>
      updateCommercialTerms(documentId, {
        questionnaire_answers: answers,
        terms: {
          currency: vendorProfile.currency,
          payment_terms_days: vendorProfile.payment_terms_days,
          price_validity_days: vendorProfile.price_validity_days,
        },
      }),
    onSuccess: (data) => {
      setPricingLines(data.workbench?.pricing?.resource_lines ?? []);
      queryClient.setQueryData(["commercial-proposal-draft", documentId], data);
    },
  });

  const savePricingMutation = useMutation({
    mutationFn: (lines: ResourcePricingLine[]) =>
      updateCommercialPricing(documentId, {
        resource_lines: lines.map((l) => ({
          role_key: l.role_key,
          role_label: l.role_label,
          line_type: l.line_type,
          billing_basis: l.billing_basis,
          quantity: l.quantity,
          unit_cost_monthly: l.unit_cost_monthly,
          margin_percent: l.margin_percent,
          gst_percent: l.gst_percent,
        })),
      }),
    onSuccess: (data) => {
      setPricingLines(data.workbench?.pricing?.resource_lines ?? []);
    },
  });

  const lastPricingSent = useRef<string>("");
  useEffect(() => {
    if (!briefingReady) return;
    if (!showWorkbench) return;
    if (isProcessing) return;

    const canonical = JSON.stringify(
      pricingLines.map((l) => ({
        role_key: l.role_key,
        role_label: l.role_label,
        line_type: l.line_type,
        billing_basis: l.billing_basis,
        quantity: l.quantity,
        unit_cost_monthly: l.unit_cost_monthly,
        margin_percent: l.margin_percent,
        gst_percent: l.gst_percent,
      }))
    );
    if (canonical === lastPricingSent.current) return;

    const t = window.setTimeout(() => {
      lastPricingSent.current = canonical;
      savePricingMutation.mutate(pricingLines);
    }, 450);
    return () => window.clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pricingLines, briefingReady, showWorkbench, isProcessing]);

  const validateMutation = useMutation({
    mutationFn: async () => {
      await prepareCommercialProposal(documentId, profileRef.current);
      return validateCommercialProposal(documentId);
    },
    onSuccess: async () => {
      const draft = await prepareCommercialProposal(documentId, profileRef.current);
      setPricingLines(draft.workbench?.pricing?.resource_lines ?? []);
    },
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      await prepareCommercialProposal(documentId, profileRef.current);
      return generateCommercialProposal(documentId, profileRef.current, false);
    },
    onMutate: () => setGenerationStarted(true),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["commercial-proposal-status", documentId],
      });
    },
  });

  const startNewMutation = useMutation({
    mutationFn: () =>
      startNewCommercialProposal(documentId, profileRef.current),
    onMutate: () => {
      queryClient.setQueryData(
        ["commercial-proposal-status", documentId],
        (prev: Awaited<ReturnType<typeof getCommercialProposalStatus>> | undefined) =>
          prev
            ? {
                ...prev,
                commercial_proposal_status: "pending",
                error_message: null,
              }
            : prev
      );
    },
    onSuccess: (data) => {
      setGenerationStarted(false);
      prepareStarted.current = true;
      queryClient.setQueryData(["commercial-proposal-draft", documentId], data);
      queryClient.removeQueries({ queryKey: ["commercial-proposal", documentId] });
      queryClient.invalidateQueries({
        queryKey: ["commercial-proposal-status", documentId],
      });
      const wb = data.workbench;
      setAnswers(wb?.questionnaire_answers ?? {});
      setPricingLines(wb?.pricing?.resource_lines ?? []);
      if (data.vendor_profile) {
        setVendorProfile(data.vendor_profile);
      }
      validateMutation.reset();
      generateMutation.reset();
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelCommercialProposal(documentId),
    onSettled: () => {
      setGenerationStarted(false);
      queryClient.invalidateQueries({
        queryKey: ["commercial-proposal-status", documentId],
      });
    },
  });

  const proposalQuery = useQuery({
    queryKey: ["commercial-proposal", documentId],
    queryFn: () => getCommercialProposal(documentId),
    enabled: statusQuery.data?.commercial_proposal_status === "completed",
  });
  const draft = prepareMutation.data ?? startNewMutation.data;
  const questions = draft?.workbench?.gap_report?.questions ?? [];
  const pricingSummary = draft?.workbench?.pricing?.summary;

  const { cachedMeta } = useCachedDocumentMeta(documentId);
  const filename =
    documentQuery.data?.original_filename ??
    cachedMeta?.original_filename ??
    "Your document";

  const panel = (
    <div className="space-y-6">
      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        Commercial pricing is calculated deterministically by the pricing engine. The
        LLM writes narrative sections only — it cannot change your numbers.
      </div>

      {!briefingReady && (
        <p className="text-sm text-ink-muted">
          Complete the procurement briefing before building a commercial proposal.
        </p>
      )}

      {showWorkbench && (
        <>
          <CommercialVendorProfileForm
            onChange={setVendorProfile}
            onApply={(profile) => syncProfileMutation.mutate(profile)}
            applying={syncProfileMutation.isPending}
            disabled={isProcessing}
          />

          <div className="rounded-lg border border-surface-border p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">Commercial terms</h3>
              <button
                type="button"
                onClick={() => saveTermsMutation.mutate()}
                disabled={saveTermsMutation.isPending}
                className="text-xs font-medium text-accent hover:underline disabled:opacity-50"
              >
                Save terms
              </button>
            </div>
            <p className="mt-1 text-xs text-ink-muted">
              Currency, tax, margin, and payment settings used in pricing and narrative
              sections.
            </p>
            <div className="mt-4">
              <CommercialTermsForm
                profile={vendorProfile}
                disabled={isProcessing}
                onChange={(profile, answersPatch) => {
                  setVendorProfile(profile);
                  setAnswers((prev) => ({ ...prev, ...answersPatch }));
                }}
              />
            </div>
          </div>

          <div className="rounded-lg border border-surface-border p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">RFP commercial questions</h3>
              <button
                type="button"
                onClick={() => saveTermsMutation.mutate()}
                disabled={saveTermsMutation.isPending}
                className="text-xs font-medium text-accent hover:underline disabled:opacity-50"
              >
                Save answers
              </button>
            </div>
            <p className="mt-1 text-xs text-ink-muted">
              Optional fields detected from the RFP (mobilization, equipment, etc.).
            </p>
            <div className="mt-4">
              <CommercialQuestionnaire
                questions={questions}
                answers={answers}
                onChange={setAnswers}
                disabled={isProcessing}
              />
            </div>
          </div>

          <div className="rounded-lg border border-surface-border p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="text-sm font-semibold">Pricing schedule</h3>
            </div>
            <p className="mt-1 text-xs text-ink-muted">
              Add personnel, equipment, one-time fees, or annual charges. Click{" "}
              <strong>any field</strong> to see totals update immediately — pricing is
              auto-saved in the background.
            </p>
            <div className="mt-4">
              <PricingTableEditor
                lines={pricingLines}
                onChange={setPricingLines}
                summary={computePricing(pricingLines).summary ?? pricingSummary}
                disabled={isProcessing}
                defaultMargin={vendorProfile.default_margin_percent}
                defaultGst={vendorProfile.default_gst_percent}
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => validateMutation.mutate()}
              disabled={validateMutation.isPending}
              className="rounded-md border border-surface-border px-4 py-2 text-sm font-medium hover:bg-surface-muted"
            >
              Validate
            </button>
            <button
              type="button"
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending || isProcessing}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent-hover disabled:opacity-50"
            >
              Generate commercial proposal
            </button>
          </div>

          {validateMutation.data && (
            <div
              className={`rounded-md border px-4 py-3 text-sm ${
                validateMutation.data.status === "FAILED"
                  ? "border-red-200 bg-red-50 text-red-800"
                  : "border-green-200 bg-green-50 text-green-800"
              }`}
            >
              <p className="font-medium">{validateMutation.data.status}</p>
              {(validateMutation.data.errors ?? []).map((e) => (
                <p key={e}>{e}</p>
              ))}
            </div>
          )}
        </>
      )}

      {startNewMutation.isError && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          {(startNewMutation.error as Error).message}
        </div>
      )}

      {generationStarted && isProcessing && (
        <div className="rounded-lg border border-surface-border bg-surface p-6">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-medium">Generating commercial proposal…</p>
            <StopProcessingButton onStop={() => cancelMutation.mutate()} />
          </div>
        </div>
      )}

      {isCompleted && proposalQuery.data && (
        <CommercialProposalViewer data={proposalQuery.data.commercial_json} />
      )}
    </div>
  );

  return (
    <PdfNavigationProvider>
      <SplitPanelLayout
        header={
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <Link
                href={`/documents/${documentId}/summary`}
                className="text-xs text-ink-muted hover:text-ink"
              >
                ← Back to briefing
              </Link>
              <h2 className="mt-2 text-2xl font-semibold">Commercial proposal</h2>
              <p className="mt-1 text-sm text-ink-muted">{filename}</p>
            </div>
            {briefingReady && (
              <div className="flex flex-wrap items-center gap-2">
                <DocumentHeaderActions
                  documentId={documentId}
                  filename={filename}
                  showBriefingDownloads={false}
                  currentProposal="commercial"
                />
                {isCompleted && (
                  <button
                    type="button"
                    onClick={() => startNewMutation.mutate()}
                    disabled={startNewMutation.isPending || isProcessing}
                    className="rounded-md border border-surface-border px-3 py-2 text-sm font-medium hover:bg-surface-muted disabled:opacity-50"
                  >
                    {startNewMutation.isPending ? "Starting…" : "New proposal"}
                  </button>
                )}
              </div>
            )}
          </div>
        }
        left={panel}
        right={
          <DocumentPreview
            documentId={documentId}
            filename={filename !== "Your document" ? filename : undefined}
          />
        }
      />
    </PdfNavigationProvider>
  );
}
