"use client";

import type { CommercialVendorProfile } from "@/lib/types/commercialProposal";

const CURRENCIES = ["INR", "USD", "EUR", "GBP"];

export function CommercialTermsForm({
  profile,
  onChange,
  disabled = false,
}: {
  profile: CommercialVendorProfile;
  onChange: (
    profile: CommercialVendorProfile,
    answers: Record<string, string | number>
  ) => void;
  disabled?: boolean;
}) {
  const patch = (next: CommercialVendorProfile) => {
    onChange(next, {
      currency: next.currency ?? "",
      default_gst_percent: next.default_gst_percent ?? 0,
      desired_margin_percent: next.default_margin_percent ?? 0,
      payment_terms_days: next.payment_terms_days ?? 0,
      price_validity_days: next.price_validity_days ?? 0,
    });
  };

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <label className="block text-sm">
        <span className="font-medium">Currency</span>
        <select
          disabled={disabled}
          value={profile.currency ?? "INR"}
          onChange={(e) => patch({ ...profile, currency: e.target.value })}
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
        >
          {CURRENCIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>

      <label className="block text-sm">
        <span className="font-medium">Default GST %</span>
        <input
          type="number"
          disabled={disabled}
          value={profile.default_gst_percent ?? ""}
          onChange={(e) =>
            patch({ ...profile, default_gst_percent: Number(e.target.value) })
          }
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
        />
      </label>

      <label className="block text-sm">
        <span className="font-medium">Default margin %</span>
        <input
          type="number"
          disabled={disabled}
          value={profile.default_margin_percent ?? ""}
          onChange={(e) =>
            patch({ ...profile, default_margin_percent: Number(e.target.value) })
          }
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
        />
      </label>

      <label className="block text-sm">
        <span className="font-medium">Payment terms (days)</span>
        <input
          type="number"
          disabled={disabled}
          value={profile.payment_terms_days ?? ""}
          onChange={(e) =>
            patch({ ...profile, payment_terms_days: Number(e.target.value) })
          }
          className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
        />
      </label>

      <label className="block text-sm sm:col-span-2">
        <span className="font-medium">Price validity (days)</span>
        <input
          type="number"
          disabled={disabled}
          value={profile.price_validity_days ?? ""}
          onChange={(e) =>
            patch({ ...profile, price_validity_days: Number(e.target.value) })
          }
          className="mt-1 w-full max-w-xs rounded-md border border-surface-border px-3 py-2 text-sm"
        />
      </label>
    </div>
  );
}
