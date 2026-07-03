"use client";

import {
  CommercialProposalIcon,
  ProposalsIcon,
  TechnicalProposalIcon,
} from "@/components/documents/DocumentMenuIcons";
import { ActionDropdown } from "@/components/ui/ActionDropdown";

export function ProposalsMenu({
  documentId,
  current,
}: {
  documentId: string;
  current?: "technical" | "commercial";
}) {
  return (
    <ActionDropdown
      label="Proposals"
      icon={<ProposalsIcon />}
      items={[
        {
          kind: "link",
          label: "Technical",
          description:
            current === "technical" ? "Current page" : "Technical volume draft",
          href: `/documents/${documentId}/proposal`,
          icon: <TechnicalProposalIcon />,
        },
        {
          kind: "link",
          label: "Commercial",
          description:
            current === "commercial" ? "Current page" : "Pricing & commercial terms",
          href: `/documents/${documentId}/commercial-proposal`,
          icon: <CommercialProposalIcon />,
        },
      ]}
    />
  );
}
