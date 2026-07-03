import type { ResourcePricingLine } from "@/lib/types/commercialProposal";

export type PricingBillingBasis = "monthly" | "one_time" | "annual";
export type PricingLineType = "personnel" | "equipment" | "service" | "other";

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

function applyMargin(amountAnnual: number, marginPercent: number): number {
  return round2(amountAnnual * (1 + (marginPercent || 0) / 100));
}

export function computePricing(lines: ResourcePricingLine[]): {
  resource_lines: ResourcePricingLine[];
  summary: Record<string, number | string>;
} {
  const computed: ResourcePricingLine[] = [];
  let subtotal_monthly = 0;
  let subtotal_annual = 0;
  let total_before_tax = 0;
  let total_with_tax = 0;

  for (const row of lines) {
    const qty = Number(row.quantity ?? 0) || 0;
    const unit = Number(row.unit_cost_monthly ?? 0) || 0;
    const margin = Number(row.margin_percent ?? 0) || 0;
    const gst = Number(row.gst_percent ?? 0) || 0;
    const billing = String(row.billing_basis ?? "monthly").toLowerCase();

    let monthly = 0;
    let annual = 0;
    if (billing === "one_time") {
      monthly = 0;
      annual = round2(qty * unit);
    } else if (billing === "annual") {
      annual = round2(qty * unit);
      monthly = round2(annual / 12);
    } else {
      monthly = round2(qty * unit);
      annual = round2(monthly * 12);
    }

    const with_margin = applyMargin(annual, margin);
    const with_tax = round2(with_margin * (1 + gst / 100));

    if (billing !== "one_time") subtotal_monthly += monthly;
    subtotal_annual += annual;
    total_before_tax += with_margin;
    total_with_tax += with_tax;

    computed.push({
      ...row,
      billing_basis: billing as PricingBillingBasis,
      monthly_cost: monthly,
      annual_cost: annual,
      total_with_margin: with_margin,
    });
  }

  return {
    resource_lines: computed,
    summary: {
      subtotal_monthly: round2(subtotal_monthly),
      subtotal_annual: round2(subtotal_annual),
      total_before_tax: round2(total_before_tax),
      total_with_tax: round2(total_with_tax),
      currency_note:
        "Live preview in UI; server pricing engine remains authoritative.",
    },
  };
}

export function createPricingLine(
  type: PricingLineType,
  billing: PricingBillingBasis,
  defaults: { margin?: number; gst?: number }
): ResourcePricingLine {
  const labels: Record<PricingLineType, string> = {
    personnel: "Personnel role",
    equipment: "Equipment / asset",
    service: "Recurring service",
    other: "Line item",
  };
  const suffix = `${type}_${Date.now().toString(36)}`;
  return {
    role_key: suffix,
    role_label: labels[type],
    line_type: type,
    billing_basis: billing,
    quantity: 1,
    unit_cost_monthly: 0,
    margin_percent: defaults.margin ?? 15,
    gst_percent: defaults.gst ?? 18,
  };
}

export function unitPriceLabel(billing?: string): string {
  switch (billing) {
    case "one_time":
      return "Unit (one-time)";
    case "annual":
      return "Unit / year";
    default:
      return "Unit / month";
  }
}
