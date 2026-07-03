import type { ProcurementSignal } from "@/lib/types/intelligence";

export type SignalPriority = "high" | "medium" | "low";

export const PRIORITY_SECTIONS: SignalPriority[] = ["high", "medium", "low"];

const SECTION_LABELS: Record<SignalPriority, string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

export function normalizePriority(raw?: string | null): SignalPriority {
  const p = (raw ?? "medium").toLowerCase().trim();
  if (p === "high" || p === "medium" || p === "low") return p;
  return "medium";
}

export function prioritySectionLabel(level: SignalPriority): string {
  return SECTION_LABELS[level];
}

export function groupSignalsByPriority(
  signals: ProcurementSignal[]
): Record<SignalPriority, ProcurementSignal[]> {
  const groups: Record<SignalPriority, ProcurementSignal[]> = {
    high: [],
    medium: [],
    low: [],
  };
  for (const signal of signals) {
    groups[normalizePriority(signal.priority)].push(signal);
  }
  return groups;
}
