"use client";

import {
  createPricingLine,
  computePricing,
  unitPriceLabel,
  type PricingBillingBasis,
  type PricingLineType,
} from "@/lib/commercialPricing";
import type { ResourcePricingLine } from "@/lib/types/commercialProposal";

const LINE_TYPES: { value: PricingLineType; label: string }[] = [
  { value: "personnel", label: "Personnel" },
  { value: "equipment", label: "Equipment" },
  { value: "service", label: "Service" },
  { value: "other", label: "Other" },
];

const BILLING_BASES: { value: PricingBillingBasis; label: string }[] = [
  { value: "monthly", label: "Monthly recurring" },
  { value: "annual", label: "Annual charge" },
  { value: "one_time", label: "One-time fee" },
];

export function PricingTableEditor({
  lines,
  onChange,
  summary,
  disabled = false,
  defaultMargin = 15,
  defaultGst = 18,
}: {
  lines: ResourcePricingLine[];
  onChange: (lines: ResourcePricingLine[]) => void;
  summary?: Record<string, number | string>;
  disabled?: boolean;
  defaultMargin?: number;
  defaultGst?: number;
}) {
  const defaults = { margin: defaultMargin, gst: defaultGst };

  const computed = computePricing(lines);
  const displayLines = computed.resource_lines;
  const displaySummary = summary ?? computed.summary;

  const updateLine = (index: number, patch: Partial<ResourcePricingLine>) => {
    const next = lines.map((line, i) => (i === index ? { ...line, ...patch } : line));
    onChange(next);
  };

  const addLine = (type: PricingLineType, billing: PricingBillingBasis) => {
    onChange([...lines, createPricingLine(type, billing, defaults)]);
  };

  const removeLine = (index: number) => {
    onChange(lines.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => addLine("personnel", "monthly")}
          className="rounded-md border border-dashed border-surface-border px-3 py-1.5 text-xs font-medium hover:border-accent hover:text-accent disabled:opacity-50"
        >
          + Personnel
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => addLine("equipment", "monthly")}
          className="rounded-md border border-dashed border-surface-border px-3 py-1.5 text-xs font-medium hover:border-accent hover:text-accent disabled:opacity-50"
        >
          + Equipment / service
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => addLine("service", "one_time")}
          className="rounded-md border border-dashed border-surface-border px-3 py-1.5 text-xs font-medium hover:border-accent hover:text-accent disabled:opacity-50"
        >
          + One-time fee
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => addLine("other", "annual")}
          className="rounded-md border border-dashed border-surface-border px-3 py-1.5 text-xs font-medium hover:border-accent hover:text-accent disabled:opacity-50"
        >
          + Annual charge
        </button>
      </div>

      {displayLines.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No pricing lines yet. Use the buttons above or fill sample data and click{" "}
          <strong>Apply to pricing</strong>.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-surface-border">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-surface-muted text-xs uppercase text-ink-muted">
              <tr>
                <th className="px-3 py-2">Description</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Billing</th>
                <th className="px-3 py-2">Qty</th>
                <th className="px-3 py-2">Unit price</th>
                <th className="px-3 py-2">Margin %</th>
                <th className="px-3 py-2">GST %</th>
                <th className="px-3 py-2">Monthly</th>
                <th className="px-3 py-2">Annual</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {displayLines.map((line, index) => (
                <tr
                  key={`${line.role_key}-${index}`}
                  className="border-t border-surface-border align-top"
                >
                  <td className="px-3 py-2">
                    <input
                      type="text"
                      disabled={disabled}
                      value={line.role_label ?? ""}
                      onChange={(e) =>
                        updateLine(index, { role_label: e.target.value })
                      }
                      className="min-w-[10rem] rounded border border-surface-border px-2 py-1"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <select
                      disabled={disabled}
                      value={(line.line_type as PricingLineType) ?? "personnel"}
                      onChange={(e) =>
                        updateLine(index, {
                          line_type: e.target.value as PricingLineType,
                        })
                      }
                      className="rounded border border-surface-border px-2 py-1 text-xs"
                    >
                      {LINE_TYPES.map((t) => (
                        <option key={t.value} value={t.value}>
                          {t.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      disabled={disabled}
                      value={(line.billing_basis as PricingBillingBasis) ?? "monthly"}
                      onChange={(e) =>
                        updateLine(index, {
                          billing_basis: e.target.value as PricingBillingBasis,
                        })
                      }
                      className="rounded border border-surface-border px-2 py-1 text-xs"
                    >
                      {BILLING_BASES.map((b) => (
                        <option key={b.value} value={b.value}>
                          {b.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min={0}
                      disabled={disabled}
                      value={line.quantity ?? ""}
                      onChange={(e) =>
                        updateLine(index, { quantity: Number(e.target.value) })
                      }
                      className="w-16 rounded border border-surface-border px-2 py-1"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      min={0}
                      disabled={disabled}
                      value={line.unit_cost_monthly ?? ""}
                      onChange={(e) =>
                        updateLine(index, {
                          unit_cost_monthly: Number(e.target.value),
                        })
                      }
                      title={unitPriceLabel(line.billing_basis)}
                      className="w-28 rounded border border-surface-border px-2 py-1"
                    />
                    <p className="mt-0.5 text-[10px] text-ink-muted">
                      {unitPriceLabel(line.billing_basis)}
                    </p>
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      disabled={disabled}
                      value={line.margin_percent ?? ""}
                      onChange={(e) =>
                        updateLine(index, { margin_percent: Number(e.target.value) })
                      }
                      className="w-16 rounded border border-surface-border px-2 py-1"
                    />
                  </td>
                  <td className="px-3 py-2">
                    <input
                      type="number"
                      disabled={disabled}
                      value={line.gst_percent ?? ""}
                      onChange={(e) =>
                        updateLine(index, { gst_percent: Number(e.target.value) })
                      }
                      className="w-16 rounded border border-surface-border px-2 py-1"
                    />
                  </td>
                  <td className="px-3 py-2 text-ink-muted whitespace-nowrap">
                    {line.billing_basis === "one_time"
                      ? "—"
                      : (line.monthly_cost?.toLocaleString() ?? "—")}
                  </td>
                  <td className="px-3 py-2 text-ink-muted whitespace-nowrap">
                    {line.annual_cost?.toLocaleString() ?? "—"}
                  </td>
                  <td className="px-3 py-2">
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => removeLine(index)}
                      className="text-xs text-red-600 hover:underline disabled:opacity-50"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {displaySummary && (
        <div className="grid gap-2 rounded-md bg-surface-muted p-4 text-sm sm:grid-cols-2">
          {Object.entries(displaySummary)
            .filter(([k]) => k !== "currency_note")
            .map(([key, val]) => (
              <div key={key}>
                <span className="text-ink-muted">{key.replace(/_/g, " ")}: </span>
                <span className="font-medium">{String(val)}</span>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

