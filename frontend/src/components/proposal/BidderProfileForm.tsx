"use client";

import { useState } from "react";

import type { BidderProfile } from "@/lib/types/proposal";
import { EMPTY_BIDDER_PROFILE, SAMPLE_BIDDER_PROFILE } from "@/lib/types/proposal";

function parseLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export function BidderProfileForm({
  initial,
  onChange,
  disabled = false,
}: {
  initial?: BidderProfile;
  onChange?: (profile: BidderProfile) => void;
  disabled?: boolean;
}) {
  const [profile, setProfile] = useState<BidderProfile>({
    ...EMPTY_BIDDER_PROFILE,
    ...initial,
    capabilities: initial?.capabilities?.length
      ? initial.capabilities
      : [""],
  });

  const update = (next: BidderProfile) => {
    setProfile(next);
    onChange?.(next);
  };

  const capabilitiesText = (profile.capabilities ?? []).join("\n");
  const certificationsText = (profile.certifications ?? []).join("\n");

  return (
    <div className="space-y-4 rounded-lg border border-surface-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">Bidder profile (optional)</h3>
          <p className="mt-1 text-xs text-ink-muted">
            Company facts you provide here are used in the proposal. Click{" "}
            <strong>Fill with sample data</strong> for a demo-ready profile (team,
            case studies, SOPs, and service catalog).
          </p>
        </div>
        <button
          type="button"
          disabled={disabled}
          onClick={() => update({ ...SAMPLE_BIDDER_PROFILE })}
          className="shrink-0 rounded-md border border-dashed border-surface-border px-3 py-1.5 text-xs font-medium text-ink-muted hover:border-accent hover:text-accent disabled:opacity-50"
        >
          Fill with sample data
        </button>
      </div>

      <label className="block text-sm">
        <span className="font-medium">Company name</span>
        <input
          type="text"
          value={profile.company_name ?? ""}
          disabled={disabled}
          onChange={(e) =>
            update({ ...profile, company_name: e.target.value })
          }
          placeholder="Your organization"
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm disabled:opacity-50"
        />
      </label>

      <label className="block text-sm">
        <span className="font-medium">Core capabilities</span>
        <span className="ml-1 text-xs text-ink-muted">(one per line)</span>
        <textarea
          value={capabilitiesText}
          disabled={disabled}
          rows={4}
          onChange={(e) =>
            update({
              ...profile,
              capabilities: parseLines(e.target.value),
            })
          }
          placeholder={"Security services\n24/7 operations center\n..."}
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm disabled:opacity-50"
        />
      </label>

      <label className="block text-sm">
        <span className="font-medium">Certifications & registrations</span>
        <span className="ml-1 text-xs text-ink-muted">(one per line)</span>
        <textarea
          value={certificationsText}
          disabled={disabled}
          rows={3}
          onChange={(e) =>
            update({
              ...profile,
              certifications: parseLines(e.target.value),
            })
          }
          placeholder={"ISO 9001\nRegistered with ..."}
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm disabled:opacity-50"
        />
      </label>

      <label className="block text-sm">
        <span className="font-medium">Additional notes</span>
        <textarea
          value={profile.additional_notes ?? ""}
          disabled={disabled}
          rows={3}
          onChange={(e) =>
            update({ ...profile, additional_notes: e.target.value })
          }
          placeholder="Past experience, differentiators, team highlights..."
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm disabled:opacity-50"
        />
      </label>
    </div>
  );
}

export function sanitizeBidderProfile(profile: BidderProfile): BidderProfile {
  const knowledge = profile.knowledge_assets;
  return {
    company_name: profile.company_name?.trim() || "",
    capabilities: (profile.capabilities ?? []).map((c) => c.trim()).filter(Boolean),
    certifications: (profile.certifications ?? [])
      .map((c) => c.trim())
      .filter(Boolean),
    key_personnel: (profile.key_personnel ?? []).filter(
      (p) => p && (p.name?.trim() || p.role?.trim() || p.experience?.trim())
    ),
    reference_projects: (profile.reference_projects ?? []).filter(
      (p) => p && (p.name?.trim() || p.client?.trim() || p.description?.trim())
    ),
    additional_notes: profile.additional_notes?.trim() || "",
    knowledge_assets: knowledge
      ? {
          policies: (knowledge.policies ?? []).map((x) => x.trim()).filter(Boolean),
          sops: (knowledge.sops ?? []).map((x) => x.trim()).filter(Boolean),
          service_catalog: (knowledge.service_catalog ?? [])
            .map((x) => x.trim())
            .filter(Boolean),
          training_programs: (knowledge.training_programs ?? [])
            .map((x) => x.trim())
            .filter(Boolean),
          resumes: (knowledge.resumes ?? []).map((x) => x.trim()).filter(Boolean),
          certifications: (knowledge.certifications ?? [])
            .map((x) => x.trim())
            .filter(Boolean),
          org_structure: knowledge.org_structure?.trim() || "",
        }
      : undefined,
  };
}

export function hasBidderProfileContent(profile: BidderProfile): boolean {
  const sanitized = sanitizeBidderProfile(profile);
  const kb = sanitized.knowledge_assets;
  const kbCount =
    (kb?.policies?.length ?? 0) +
    (kb?.sops?.length ?? 0) +
    (kb?.service_catalog?.length ?? 0) +
    (kb?.training_programs?.length ?? 0);
  return Boolean(
    sanitized.company_name ||
      (sanitized.capabilities?.length ?? 0) ||
      (sanitized.certifications?.length ?? 0) ||
      (sanitized.key_personnel?.length ?? 0) ||
      (sanitized.reference_projects?.length ?? 0) ||
      sanitized.additional_notes ||
      kbCount
  );
}
