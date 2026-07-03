import type { ExtractedInsightItem, SummarySectionBlock } from "@/lib/types/intelligence";

export type RiskSeverity = "critical" | "medium" | "low";

export const RISK_SEVERITY_SECTIONS: RiskSeverity[] = [
  "critical",
  "medium",
  "low",
];

const SECTION_LABELS: Record<RiskSeverity, string> = {
  critical: "Critical — financial impact",
  medium: "Medium",
  low: "Low",
};

const CRITICAL_PATTERNS = [
  /liquidated damages?/i,
  /\bld[s]?\b/i,
  /penalt(y|ies)/i,
  /indemnif/i,
  /overpayment/i,
  /forfeit/i,
  /retention/i,
  /performance guarantee/i,
  /payment bond/i,
  /bank guarantee/i,
  /\bbond\b/i,
  /liable for/i,
  /liability/i,
  /appropriated funds/i,
  /federal or state funds/i,
  /reimbursement/i,
  /fixed[- ]price/i,
  /lowest bidder/i,
  /\bbafo\b/i,
  /non[- ]responsive/i,
  /termination/i,
  /\$\s*\d/,
  /%\s*(per|of)/i,
];

const MEDIUM_PATTERNS = [
  /reject/i,
  /cancel/i,
  /withdraw/i,
  /amend/i,
  /clarification/i,
  /correction/i,
  /non[- ]conform/i,
  /disqualif/i,
  /subcontractor/i,
  /accountab/i,
  /under[- ]performance/i,
  /non[- ]performance/i,
  /sole discretion/i,
  /compliance/i,
];

export function normalizeRiskSeverity(raw?: string | null): RiskSeverity {
  const p = (raw ?? "medium").toLowerCase().trim();
  if (p === "critical" || p === "high" || p === "severe") return "critical";
  if (p === "low" || p === "minor") return "low";
  return "medium";
}

export function classifyRiskSeverity(text: string): RiskSeverity {
  const lower = text.toLowerCase();
  if (!lower) return "medium";
  if (CRITICAL_PATTERNS.some((re) => re.test(lower))) return "critical";
  if (MEDIUM_PATTERNS.some((re) => re.test(lower))) return "medium";
  return "low";
}

export function resolveItemSeverity(
  item: ExtractedInsightItem | SummarySectionBlock,
): RiskSeverity {
  const stored = "severity" in item ? item.severity : undefined;
  const text =
    ("requirement" in item && item.requirement) ||
    ("text" in item ? item.text : "") ||
    ("item" in item ? item.item : "") ||
    "";
  const src = "source_text" in item ? item.source_text : "";
  const combined = `${text} ${src}`.trim();

  const llm = stored ? normalizeRiskSeverity(stored) : null;
  const rules = classifyRiskSeverity(combined);
  const order: Record<RiskSeverity, number> = {
    low: 0,
    medium: 1,
    critical: 2,
  };
  const base = llm ?? rules;
  return order[rules] > order[base] ? rules : base;
}

export function riskSeverityLabel(level: RiskSeverity): string {
  return SECTION_LABELS[level];
}

export function groupByRiskSeverity<T extends { severity?: RiskSeverity }>(
  items: T[],
  getSeverity: (item: T) => RiskSeverity,
): Record<RiskSeverity, T[]> {
  const groups: Record<RiskSeverity, T[]> = {
    critical: [],
    medium: [],
    low: [],
  };
  for (const item of items) {
    groups[getSeverity(item)].push(item);
  }
  return groups;
}
