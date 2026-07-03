import type { SummarySectionBlock } from "@/lib/types/intelligence";

export type ChecklistCategory =
  | "core_proposals"
  | "commercial_pricing"
  | "forms_compliance"
  | "guarantees_bonds"
  | "team_references"
  | "other";

export const CHECKLIST_GROUP_ORDER: ChecklistCategory[] = [
  "core_proposals",
  "commercial_pricing",
  "forms_compliance",
  "guarantees_bonds",
  "team_references",
  "other",
];

export const CHECKLIST_GROUP_LABELS: Record<ChecklistCategory, string> = {
  core_proposals: "Proposal volumes",
  commercial_pricing: "Commercial & pricing documents",
  forms_compliance: "Forms, annexures & compliance",
  guarantees_bonds: "Guarantees & bonds",
  team_references: "Team credentials & references",
  other: "Other mandatory items",
};

const CATEGORY_RULES: { category: ChecklistCategory; patterns: RegExp[] }[] = [
  {
    category: "guarantees_bonds",
    patterns: [
      /performance guarantee/i,
      /advance payment bond/i,
      /bank guarantee/i,
      /\bbond\b/i,
    ],
  },
  {
    category: "team_references",
    patterns: [
      /\bcv\b/i,
      /resume/i,
      /reference/i,
      /implementation experience/i,
      /contact details/i,
      /technical team/i,
    ],
  },
  {
    category: "forms_compliance",
    patterns: [
      /appendix/i,
      /annexure/i,
      /compliance matrix/i,
      /sla agreement/i,
      /fill all/i,
      /mandatory document/i,
      /general requirements/i,
    ],
  },
  {
    category: "commercial_pricing",
    patterns: [
      /cost breakup/i,
      /break-?up/i,
      /summary table/i,
      /commercial proposal/i,
      /pricing/i,
      /phase wise/i,
    ],
  },
  {
    category: "core_proposals",
    patterns: [/technical proposal/i],
  },
];

export function inferChecklistCategory(text: string): ChecklistCategory {
  const lower = text.toLowerCase();
  for (const { category, patterns } of CATEGORY_RULES) {
    if (patterns.some((p) => p.test(lower))) return category;
  }
  return "other";
}

export function normalizeChecklistCategory(
  raw?: string | null
): ChecklistCategory {
  const key = (raw ?? "").toLowerCase().replace(/\s+/g, "_");
  if (CHECKLIST_GROUP_ORDER.includes(key as ChecklistCategory)) {
    return key as ChecklistCategory;
  }
  return "other";
}

export interface GroupedChecklistItem extends SummarySectionBlock {
  item?: string;
  text?: string;
  category?: string;
}

export interface ChecklistGroup {
  category: ChecklistCategory;
  label: string;
  items: GroupedChecklistItem[];
}

export function groupSubmissionChecklist(
  items: SummarySectionBlock[]
): ChecklistGroup[] {
  const buckets = new Map<ChecklistCategory, GroupedChecklistItem[]>();

  for (const raw of items) {
    const label = (raw.item || raw.text || "").trim();
    if (!label) continue;

    const category = raw.category
      ? normalizeChecklistCategory(raw.category)
      : inferChecklistCategory(label);

    const entry: GroupedChecklistItem = { ...raw, item: label };
    const list = buckets.get(category) ?? [];
    list.push(entry);
    buckets.set(category, list);
  }

  return CHECKLIST_GROUP_ORDER.filter((cat) => buckets.has(cat)).map(
    (category) => ({
      category,
      label: CHECKLIST_GROUP_LABELS[category],
      items: buckets.get(category)!,
    })
  );
}
