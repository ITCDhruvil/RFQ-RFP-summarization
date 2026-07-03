"use client";

import Link from "next/link";

import { DocumentDownloadMenu } from "@/components/documents/DocumentDownloadMenu";
import { SparklesIcon } from "@/components/documents/DocumentMenuIcons";
import { ProposalsMenu } from "@/components/documents/ProposalsMenu";

export function DocumentHeaderActions({
  documentId,
  filename,
  showBriefingDownloads = true,
  currentProposal,
  hideAskAi = false,
}: {
  documentId: string;
  filename: string;
  showBriefingDownloads?: boolean;
  currentProposal?: "technical" | "commercial";
  hideAskAi?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      <DocumentDownloadMenu
        documentId={documentId}
        filename={filename}
        showBriefing={showBriefingDownloads}
      />
      <ProposalsMenu documentId={documentId} current={currentProposal} />
      {!hideAskAi && (
        <Link
          href={`/documents/${documentId}/chat`}
          className="inline-flex items-center gap-1.5 rounded-md bg-accent px-3 py-2 text-sm font-medium text-white hover:bg-accent-hover"
        >
          <SparklesIcon />
          <span>Ask AI</span>
        </Link>
      )}
    </div>
  );
}
