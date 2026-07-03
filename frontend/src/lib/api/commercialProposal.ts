import { apiClient } from "@/lib/api/client";
import type {
  CommercialProposalStatusResponse,
  CommercialValidationReport,
  CommercialVendorProfile,
  CommercialWorkbench,
  GeneratedCommercialProposal,
} from "@/lib/types/commercialProposal";

const TIMEOUT_MS = 600000;

export async function prepareCommercialProposal(
  documentId: string,
  vendorProfile?: CommercialVendorProfile
): Promise<GeneratedCommercialProposal> {
  const { data } = await apiClient.post<GeneratedCommercialProposal>(
    `/documents/${documentId}/commercial-proposal/prepare/`,
    { vendor_profile: vendorProfile }
  );
  return data;
}

export async function getCommercialProposal(
  documentId: string
): Promise<GeneratedCommercialProposal> {
  const { data } = await apiClient.get<GeneratedCommercialProposal>(
    `/documents/${documentId}/commercial-proposal/`
  );
  return data;
}

export async function getCommercialProposalStatus(
  documentId: string
): Promise<CommercialProposalStatusResponse> {
  const { data } = await apiClient.get<CommercialProposalStatusResponse>(
    `/documents/${documentId}/commercial-proposal/status/`
  );
  return data;
}

export async function getCommercialQuestionnaire(documentId: string) {
  const { data } = await apiClient.get<{
    questions: CommercialWorkbench["gap_report"];
    missing_commercial_inputs: string[];
    ready_for_pricing: boolean;
  }>(`/documents/${documentId}/commercial-proposal/questionnaire/`);
  return data;
}

export async function updateCommercialPricing(
  documentId: string,
  pricing: CommercialWorkbench["pricing"]
): Promise<GeneratedCommercialProposal> {
  const { data } = await apiClient.put<GeneratedCommercialProposal>(
    `/documents/${documentId}/commercial-proposal/pricing/`,
    { pricing }
  );
  return data;
}

export async function updateCommercialAssumptions(
  documentId: string,
  assumptions: CommercialWorkbench["assumptions"]
): Promise<GeneratedCommercialProposal> {
  const { data } = await apiClient.put<GeneratedCommercialProposal>(
    `/documents/${documentId}/commercial-proposal/assumptions/`,
    { assumptions }
  );
  return data;
}

export async function updateCommercialTerms(
  documentId: string,
  payload: {
    terms?: CommercialWorkbench["terms"];
    questionnaire_answers?: CommercialWorkbench["questionnaire_answers"];
  }
): Promise<GeneratedCommercialProposal> {
  const { data } = await apiClient.put<GeneratedCommercialProposal>(
    `/documents/${documentId}/commercial-proposal/terms/`,
    payload
  );
  return data;
}

export async function validateCommercialProposal(
  documentId: string
): Promise<CommercialValidationReport> {
  const { data } = await apiClient.post<CommercialValidationReport>(
    `/documents/${documentId}/commercial-proposal/validate/`,
    {}
  );
  return data;
}

export async function startNewCommercialProposal(
  documentId: string,
  vendorProfile?: CommercialVendorProfile
): Promise<GeneratedCommercialProposal> {
  const { data } = await apiClient.post<GeneratedCommercialProposal>(
    `/documents/${documentId}/commercial-proposal/new/`,
    { vendor_profile: vendorProfile }
  );
  return data;
}

export async function generateCommercialProposal(
  documentId: string,
  vendorProfile?: CommercialVendorProfile,
  regenerate = false
) {
  const { data } = await apiClient.post(
    `/documents/${documentId}/commercial-proposal/generate/`,
    { vendor_profile: vendorProfile, regenerate },
    { timeout: TIMEOUT_MS }
  );
  return data;
}

export async function cancelCommercialProposal(documentId: string) {
  const { data } = await apiClient.post(
    `/documents/${documentId}/commercial-proposal/cancel/`,
    {}
  );
  return data;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function commercialProposalPdfUrl(documentId: string): string {
  return `${API_BASE}/documents/${documentId}/commercial-proposal/download/`;
}

export async function downloadCommercialProposalPdf(
  documentId: string,
  originalFilename: string
): Promise<void> {
  const response = await fetch(commercialProposalPdfUrl(documentId));
  if (!response.ok) throw new Error("Failed to download commercial proposal PDF");
  const blob = await response.blob();
  const stem = originalFilename.replace(/\.[^.]+$/, "") || "document";
  const anchor = document.createElement("a");
  anchor.href = URL.createObjectURL(blob);
  anchor.download = `${stem}_commercial_proposal.pdf`;
  anchor.click();
  URL.revokeObjectURL(anchor.href);
}
