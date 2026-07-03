"use client";

import {
  BriefingIcon,
  CommercialProposalIcon,
  DownloadIcon,
  ExecutiveSummaryIcon,
  SparklesIcon,
  TechnicalProposalIcon,
} from "@/components/documents/DocumentMenuIcons";
import { ActionDropdown } from "@/components/ui/ActionDropdown";
import { downloadBriefingPdf } from "@/lib/api/intelligence";
import { downloadCommercialProposalPdf } from "@/lib/api/commercialProposal";
import { downloadProposalPdf } from "@/lib/api/proposal";
import { useQuery } from "@tanstack/react-query";
import { getCommercialProposalStatus } from "@/lib/api/commercialProposal";
import { getProposalStatus } from "@/lib/api/proposal";
import { useState } from "react";

export function DocumentDownloadMenu({
  documentId,
  filename,
  showBriefing = true,
}: {
  documentId: string;
  filename: string;
  showBriefing?: boolean;
}) {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const proposalStatus = useQuery({
    queryKey: ["proposal-status", documentId],
    queryFn: () => getProposalStatus(documentId),
  });

  const commercialStatus = useQuery({
    queryKey: ["commercial-proposal-status", documentId],
    queryFn: () => getCommercialProposalStatus(documentId),
  });

  const technicalReady = proposalStatus.data?.proposal_status === "completed";
  const commercialReady =
    commercialStatus.data?.commercial_proposal_status === "completed";

  async function run(id: string, fn: () => Promise<void>) {
    setError(null);
    setLoading(id);
    try {
      await fn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setLoading(null);
    }
  }

  const items = [];

  if (showBriefing) {
    items.push(
      {
        kind: "button" as const,
        label: "Full briefing",
        description: "Complete procurement report",
        icon: <BriefingIcon />,
        loading: loading === "briefing-full",
        onClick: () =>
          run("briefing-full", () => downloadBriefingPdf(documentId, filename, "full")),
      },
      {
        kind: "button" as const,
        label: "Executive summary",
        description: "Short executive PDF",
        icon: <ExecutiveSummaryIcon />,
        loading: loading === "briefing-executive",
        onClick: () =>
          run("briefing-executive", () =>
            downloadBriefingPdf(documentId, filename, "executive")
          ),
      }
    );
  }

  items.push(
    {
      kind: "button" as const,
      label: "Technical proposal",
      description: technicalReady ? "Technical volume PDF" : "Generate first",
      icon: <TechnicalProposalIcon />,
      disabled: !technicalReady,
      loading: loading === "technical",
      onClick: () =>
        run("technical", () => downloadProposalPdf(documentId, filename)),
    },
    {
      kind: "button" as const,
      label: "Commercial proposal",
      description: commercialReady ? "Commercial volume PDF" : "Generate first",
      icon: <CommercialProposalIcon />,
      disabled: !commercialReady,
      loading: loading === "commercial",
      onClick: () =>
        run("commercial", () => downloadCommercialProposalPdf(documentId, filename)),
    }
  );

  return (
    <div className="flex flex-col items-end gap-1">
      <ActionDropdown
        label="Download"
        icon={<DownloadIcon />}
        items={items}
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  );
}
