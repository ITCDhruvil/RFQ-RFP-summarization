import { apiClient } from "@/lib/api/client";
import type {
  ExtractedInsight,
  GenerateSummaryResponse,
  GeneratedSummary,
  SummaryStatusResponse,
} from "@/lib/types/intelligence";

/** Sync regeneration can take several minutes */
const INTELLIGENCE_TIMEOUT_MS = 600000;

export async function generateSummary(
  documentId: string
): Promise<GenerateSummaryResponse> {
  const { data } = await apiClient.post<GenerateSummaryResponse>(
    `/documents/${documentId}/summary/generate/`,
    {},
    { timeout: INTELLIGENCE_TIMEOUT_MS }
  );
  return data;
}

export async function regenerateSummary(
  documentId: string
): Promise<GenerateSummaryResponse> {
  const { data } = await apiClient.post<GenerateSummaryResponse>(
    `/documents/${documentId}/summary/regenerate/`,
    {},
    { timeout: INTELLIGENCE_TIMEOUT_MS }
  );
  return data;
}

export async function getSummary(documentId: string): Promise<GeneratedSummary> {
  const { data } = await apiClient.get<GeneratedSummary>(
    `/documents/${documentId}/summary/`
  );
  return data;
}

export async function getSummaryStatus(
  documentId: string
): Promise<SummaryStatusResponse> {
  const { data } = await apiClient.get<SummaryStatusResponse>(
    `/documents/${documentId}/summary/status/`
  );
  return data;
}

export async function cancelSummary(
  documentId: string
): Promise<{ message: string; summary_id?: string }> {
  const { data } = await apiClient.post(
    `/documents/${documentId}/summary/cancel/`,
    {}
  );
  return data;
}

export async function listInsights(
  documentId: string
): Promise<ExtractedInsight[]> {
  const { data } = await apiClient.get<ExtractedInsight[]>(
    `/documents/${documentId}/insights/`
  );
  return data;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function briefingPdfDownloadUrl(
  documentId: string,
  variant: "full" | "executive" = "full"
): string {
  const params = new URLSearchParams({ variant });
  return `${API_BASE}/documents/${documentId}/summary/download/?${params}`;
}

/** Trigger browser download of the structured briefing PDF. */
export async function downloadBriefingPdf(
  documentId: string,
  originalFilename: string,
  variant: "full" | "executive" = "full"
): Promise<void> {
  const url = briefingPdfDownloadUrl(documentId, variant);
  const response = await fetch(url);
  if (!response.ok) {
    let message = "Failed to download briefing PDF";
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
  const suffix =
    variant === "executive" ? "executive_summary" : "briefing";
  const fallbackName = `${stem}_procurement_${suffix}.pdf`;
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
