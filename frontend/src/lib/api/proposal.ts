import { apiClient } from "@/lib/api/client";
import type {
  BidderProfile,
  GenerateProposalResponse,
  GeneratedProposal,
  ProposalStatusResponse,
} from "@/lib/types/proposal";

const INTELLIGENCE_TIMEOUT_MS = 600000;

export async function startNewProposal(
  documentId: string,
  bidderProfile?: BidderProfile
): Promise<{ message: string; proposal_id: string; version: number; status: string }> {
  const { data } = await apiClient.post(
    `/documents/${documentId}/proposal/new/`,
    { bidder_profile: bidderProfile }
  );
  return data;
}

export async function generateProposal(
  documentId: string,
  bidderProfile?: BidderProfile,
  regenerate = false
): Promise<GenerateProposalResponse> {
  const { data } = await apiClient.post<GenerateProposalResponse>(
    `/documents/${documentId}/proposal/generate/`,
    { bidder_profile: bidderProfile, regenerate },
    { timeout: INTELLIGENCE_TIMEOUT_MS }
  );
  return data;
}

export async function cancelProposal(
  documentId: string
): Promise<{ message: string; proposal_id?: string }> {
  const { data } = await apiClient.post(
    `/documents/${documentId}/proposal/cancel/`,
    {}
  );
  return data;
}

export async function getProposal(documentId: string): Promise<GeneratedProposal> {
  const { data } = await apiClient.get<GeneratedProposal>(
    `/documents/${documentId}/proposal/`
  );
  return data;
}

export async function getProposalStatus(
  documentId: string
): Promise<ProposalStatusResponse> {
  const { data } = await apiClient.get<ProposalStatusResponse>(
    `/documents/${documentId}/proposal/status/`
  );
  return data;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function proposalPdfDownloadUrl(documentId: string): string {
  return `${API_BASE}/documents/${documentId}/proposal/download/`;
}

export async function downloadProposalPdf(
  documentId: string,
  originalFilename: string
): Promise<void> {
  const url = proposalPdfDownloadUrl(documentId);
  const response = await fetch(url);
  if (!response.ok) {
    let message = "Failed to download proposal PDF";
    try {
      const body = await response.json();
      message = body?.error?.message ?? message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const stem = originalFilename.replace(/\.[^.]+$/, "") || "document";
  const fallbackName = `${stem}_technical_proposal.pdf`;
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^";\n]+)"?/i.exec(disposition);
  const filename = match?.[1]?.trim() || fallbackName;

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}
