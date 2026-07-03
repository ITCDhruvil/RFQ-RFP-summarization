"use client";

import { useState } from "react";

import type { CommercialVendorProfile } from "@/lib/types/commercialProposal";
import {
  EMPTY_COMMERCIAL_VENDOR_PROFILE,
  SAMPLE_COMMERCIAL_VENDOR_PROFILE,
} from "@/lib/types/commercialProposal";

export function CommercialVendorProfileForm({
  onChange,
  onApply,
  disabled = false,
  applying = false,
}: {
  onChange?: (profile: CommercialVendorProfile) => void;
  onApply?: (profile: CommercialVendorProfile) => void;
  disabled?: boolean;
  applying?: boolean;
}) {
  const [profile, setProfile] = useState<CommercialVendorProfile>({
    ...EMPTY_COMMERCIAL_VENDOR_PROFILE,
  });

  const apply = (next: CommercialVendorProfile) => {
    setProfile(next);
    onChange?.(next);
    onApply?.(next);
  };

  const update = (next: CommercialVendorProfile) => {
    setProfile(next);
    onChange?.(next);
  };

  return (
    <div className="space-y-4 rounded-lg border border-surface-border bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">Commercial vendor profile</h3>
          <p className="mt-1 text-xs text-ink-muted">
            Reusable commercial defaults — rates, taxes, margins, and terms.
          </p>
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <button
            type="button"
            disabled={disabled || applying}
            onClick={() => apply({ ...SAMPLE_COMMERCIAL_VENDOR_PROFILE })}
            className="rounded-md border border-dashed border-surface-border px-3 py-1.5 text-xs font-medium text-ink-muted hover:border-accent hover:text-accent disabled:opacity-50"
          >
            Fill with sample data
          </button>
          <button
            type="button"
            disabled={disabled || applying}
            onClick={() => onApply?.(profile)}
            className="rounded-md border border-surface-border px-3 py-1.5 text-xs font-medium hover:bg-surface-muted disabled:opacity-50"
          >
            {applying ? "Applying…" : "Apply to pricing"}
          </button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="font-medium">Currency</span>
          <input
            type="text"
            value={profile.currency ?? ""}
            disabled={disabled}
            onChange={(e) => update({ ...profile, currency: e.target.value })}
            className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Default GST %</span>
          <input
            type="number"
            value={profile.default_gst_percent ?? ""}
            disabled={disabled}
            onChange={(e) =>
              update({ ...profile, default_gst_percent: Number(e.target.value) })
            }
            className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Default margin %</span>
          <input
            type="number"
            value={profile.default_margin_percent ?? ""}
            disabled={disabled}
            onChange={(e) =>
              update({ ...profile, default_margin_percent: Number(e.target.value) })
            }
            className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium">Payment terms (days)</span>
          <input
            type="number"
            value={profile.payment_terms_days ?? ""}
            disabled={disabled}
            onChange={(e) =>
              update({ ...profile, payment_terms_days: Number(e.target.value) })
            }
            className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm sm:col-span-2">
          <span className="font-medium">Price validity (days)</span>
          <input
            type="number"
            value={profile.price_validity_days ?? ""}
            disabled={disabled}
            onChange={(e) =>
              update({ ...profile, price_validity_days: Number(e.target.value) })
            }
            className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
          />
        </label>
      </div>
    </div>
  );
}
