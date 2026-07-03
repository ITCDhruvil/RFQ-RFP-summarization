"use client";

import type { GeneratedCommercialProposal } from "@/lib/types/commercialProposal";

export function CommercialProposalViewer({
  data,
}: {
  data: GeneratedCommercialProposal["commercial_json"];
}) {
  if (!data) return null;

  const sections = [
    ["Commercial Cover Letter", (data.cover_letter as { body?: string })?.body],
    ["Executive Summary", (data.executive_summary as { body?: string })?.body],
    ["Taxes & Duties", (data.taxes_and_duties as { body?: string })?.body],
    ["Payment Terms", (data.payment_terms as { body?: string })?.body],
    ["Price Validity", (data.price_validity as { body?: string })?.body],
    ["Commercial Terms", (data.commercial_terms as { body?: string })?.body],
  ];

  const pricingLines = (data.resource_pricing_table ?? []) as Array<{
    role_label?: string;
    quantity?: number;
    monthly_cost?: number;
    annual_cost?: number;
    total_with_margin?: number;
  }>;
  const pricingSummary = (data.pricing_summary ?? {}) as Record<string, number | string>;

  return (
    <div className="space-y-6">
      {sections.map(([title, body]) =>
        body ? (
          <section key={String(title)} className="rounded-lg border border-surface-border p-4">
            <h3 className="text-sm font-semibold">{title}</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm text-ink">{body}</p>
          </section>
        ) : null
      )}

      {pricingLines.length > 0 && (
        <section className="rounded-lg border border-surface-border p-4">
          <h3 className="text-sm font-semibold">Pricing Schedule</h3>
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead>
                <tr className="border-b bg-surface-muted">
                  <th className="px-2 py-2">Role</th>
                  <th className="px-2 py-2">Qty</th>
                  <th className="px-2 py-2">Monthly</th>
                  <th className="px-2 py-2">Annual</th>
                </tr>
              </thead>
              <tbody>
                {pricingLines.map((row, i) => (
                  <tr key={i} className="border-b border-surface-border">
                    <td className="px-2 py-2">{row.role_label}</td>
                    <td className="px-2 py-2">{row.quantity}</td>
                    <td className="px-2 py-2">
                      {row.monthly_cost != null
                        ? Number(row.monthly_cost).toLocaleString()
                        : "—"}
                    </td>
                    <td className="px-2 py-2">
                      {row.annual_cost != null
                        ? Number(row.annual_cost).toLocaleString()
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {Object.keys(pricingSummary).length > 0 && (
            <dl className="mt-3 grid gap-1 text-xs sm:grid-cols-2">
              {Object.entries(pricingSummary).map(([key, val]) => (
                <div key={key} className="flex justify-between gap-2 border-b border-dashed py-1">
                  <dt className="text-ink-muted">{key.replace(/_/g, " ")}</dt>
                  <dd className="font-medium">
                    {typeof val === "number" ? val.toLocaleString() : String(val)}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}

      {Array.isArray(data.assumptions) && data.assumptions.length > 0 && (
        <section className="rounded-lg border border-surface-border p-4">
          <h3 className="text-sm font-semibold">Assumptions</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
            {(data.assumptions as Array<{ text: string }>).map((a, i) => (
              <li key={i}>{a.text}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
