"use client";

import type { CommercialQuestion } from "@/lib/types/commercialProposal";

const SECTION_ORDER = [
  "Pricing Model",
  "Resource Rates",
  "Taxes",
  "Margins",
  "Commercial Terms",
  "Additional Commercial",
];

export function CommercialQuestionnaire({
  questions,
  answers,
  onChange,
  disabled = false,
}: {
  questions: CommercialQuestion[];
  answers: Record<string, string | number>;
  onChange: (answers: Record<string, string | number>) => void;
  disabled?: boolean;
}) {
  if (!questions.length) {
    return (
      <p className="text-sm text-ink-muted">
        No extra RFP-specific questions detected. Use{" "}
        <strong>Commercial terms</strong> above and add line items in the pricing
        schedule.
      </p>
    );
  }

  const grouped = SECTION_ORDER.map((section) => ({
    section,
    items: questions.filter((q) => q.section === section),
  })).filter((g) => g.items.length > 0);

  const other = questions.filter(
    (q) => !SECTION_ORDER.includes(q.section)
  );
  if (other.length) grouped.push({ section: "Other", items: other });

  return (
    <div className="space-y-6">
      {grouped.map(({ section, items }) => (
        <div key={section} className="space-y-3">
          <h4 className="text-sm font-semibold">{section}</h4>
          {items.map((q) => (
            <label key={q.field_key} className="block text-sm">
              <span className="font-medium">
                {q.label}
                {q.required && <span className="text-red-600"> *</span>}
              </span>
              {q.input_type === "select" ? (
                <select
                  value={String(answers[q.field_key] ?? "")}
                  disabled={disabled}
                  onChange={(e) =>
                    onChange({ ...answers, [q.field_key]: e.target.value })
                  }
                  className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
                >
                  <option value="">Select…</option>
                  {(q.options ?? []).map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={q.input_type === "currency" || q.input_type === "percent" || q.input_type === "number" ? "number" : "text"}
                  value={answers[q.field_key] ?? ""}
                  disabled={disabled}
                  placeholder={q.placeholder}
                  onChange={(e) =>
                    onChange({
                      ...answers,
                      [q.field_key]:
                        q.input_type === "number" ||
                        q.input_type === "currency" ||
                        q.input_type === "percent"
                          ? Number(e.target.value)
                          : e.target.value,
                    })
                  }
                  className="mt-1 w-full rounded-md border border-surface-border px-3 py-2 text-sm"
                />
              )}
            </label>
          ))}
        </div>
      ))}
    </div>
  );
}
