export type SummaryStatus = "pending" | "processing" | "completed" | "failed";

export interface SourceCitation {
  page?: number;
  section?: string;
  section_path?: string;
  source_text?: string;
  /** True when source_text was found verbatim in parsed document pages. */
  citation_verified?: boolean;
  /** True when source_text can be located in the PDF text layer for highlight. */
  highlightable?: boolean;
}

export interface ProcurementStrategyInsight {
  insight?: string;
  implication?: string;
  sources?: SourceCitation[];
}

export interface SummarySectionBlock {
  text?: string;
  item?: string;
  date?: string | null;
  /** critical | medium | low — penalties/risks financial-impact tier */
  severity?: string | null;
  /** Submission checklist grouping (see submissionChecklist.ts). */
  category?: string;
  sources?: SourceCitation[];
}

export interface ProcurementSignal {
  signal?: string;
  priority?: "high" | "medium" | "low" | string;
  sources?: SourceCitation[];
}

export interface GeneratedSummaryData {
  executive_summary?: SummarySectionBlock;
  procurement_critical_signals?: ProcurementSignal[];
  procurement_strategy_insights?: ProcurementStrategyInsight[];
  key_requirements?: SummarySectionBlock[];
  important_deadlines?: SummarySectionBlock[];
  technical_scope?: SummarySectionBlock;
  commercial_terms?: SummarySectionBlock;
  risks_and_concerns?: SummarySectionBlock[];
  submission_checklist?: SummarySectionBlock[];
  _meta?: Record<string, unknown>;
}

export interface GeneratedSummary {
  id: string;
  document_id: string;
  status: SummaryStatus;
  version: number;
  is_current: boolean;
  summary_json: GeneratedSummaryData;
  model_metadata: Record<string, unknown>;
  total_tokens: number;
  error_message: string;
  last_error: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExtractedInsightItem {
  requirement: string;
  page: number;
  section: string;
  section_path?: string;
  source_text: string;
  confidence: number;
  citation_verified?: boolean;
  /** Submission deadlines: calendar date/time or portal URL from the document. */
  date_time?: string | null;
  value?: string | null;
  label?: string | null;
  /** Penalties & risks: critical (financial) | medium | low */
  severity?: string | null;
}

export interface ExtractedInsight {
  id: string;
  extraction_type: string;
  payload: { items: ExtractedInsightItem[] };
  confidence_score: number;
  model_name: string;
  prompt_version: string;
  token_usage: Record<string, number>;
  item_count: number;
  created_at: string;
}

export interface SummaryStatusResponse {
  document_id: string;
  document_status: string;
  summary_status: SummaryStatus | null;
  summary_id: string | null;
  version: number | null;
  progress_stage: string | null;
  total_tokens: number | null;
  error_message?: string | null;
}

export interface GenerateSummaryResponse {
  message: string;
  document_id: string;
  celery_task_id?: string;
  summary_id?: string;
  regenerate?: boolean;
  sync?: boolean;
  status?: string;
}
