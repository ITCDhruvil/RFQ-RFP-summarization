export type CommercialProposalStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed";

export interface CommercialVendorProfile {
  currency?: string;
  default_gst_percent?: number;
  default_margin_percent?: number;
  payment_terms_days?: number;
  price_validity_days?: number;
  company_legal_name?: string;
  authorized_signatory?: string;
  signatory_designation?: string;
  rate_cards?: Record<string, unknown>[];
  resource_rates?: ResourceRateInput[];
  commercial_assumptions?: string[];
  commercial_exclusions?: string[];
}

export interface ResourceRateInput {
  role_key: string;
  role_label?: string;
  line_type?: "personnel" | "equipment" | "service" | "other";
  billing_basis?: "monthly" | "one_time" | "annual";
  quantity?: number;
  unit_cost_monthly?: number;
  margin_percent?: number;
  gst_percent?: number;
}

export interface ResourcePricingLine {
  role_key?: string;
  role_label?: string;
  line_type?: "personnel" | "equipment" | "service" | "other";
  billing_basis?: "monthly" | "one_time" | "annual";
  quantity?: number;
  unit_cost_monthly?: number;
  margin_percent?: number;
  gst_percent?: number;
  monthly_cost?: number;
  annual_cost?: number;
  total_with_margin?: number;
}

export interface CommercialQuestion {
  field_key: string;
  label: string;
  section: string;
  required: boolean;
  input_type: string;
  placeholder?: string;
  options?: string[];
}

export interface CommercialWorkbench {
  requirements?: Record<string, unknown>;
  questionnaire_answers?: Record<string, string | number>;
  pricing?: {
    resource_lines?: ResourcePricingLine[];
    summary?: Record<string, number | string>;
  };
  assumptions?: Array<{ text: string; source?: string; editable?: string }>;
  exclusions?: Array<{ text: string; source?: string; editable?: string }>;
  terms?: Record<string, unknown>;
  gap_report?: {
    missing_commercial_inputs?: string[];
    questions?: CommercialQuestion[];
    ready_for_pricing?: boolean;
  };
  validation_report?: CommercialValidationReport;
}

export interface CommercialValidationReport {
  status: "PASSED" | "FAILED";
  blocked?: boolean;
  errors?: string[];
  warnings?: string[];
  blocking_reason?: string;
}

export interface GeneratedCommercialProposal {
  id: string;
  document_id: string;
  status: CommercialProposalStatus;
  version: number;
  commercial_json?: Record<string, unknown>;
  vendor_profile?: CommercialVendorProfile;
  workbench?: CommercialWorkbench;
  error_message?: string;
}

export interface CommercialProposalStatusResponse {
  document_id: string;
  commercial_proposal_status: CommercialProposalStatus | null;
  commercial_proposal_id?: string;
  error_message?: string;
}

export const EMPTY_COMMERCIAL_VENDOR_PROFILE: CommercialVendorProfile = {
  currency: "INR",
  default_gst_percent: 18,
  default_margin_percent: 15,
  payment_terms_days: 45,
  price_validity_days: 90,
  resource_rates: [],
  commercial_assumptions: [],
  commercial_exclusions: [],
};

export const SAMPLE_COMMERCIAL_VENDOR_PROFILE: CommercialVendorProfile = {
  currency: "INR",
  default_gst_percent: 18,
  default_margin_percent: 15,
  payment_terms_days: 45,
  price_validity_days: 90,
  resource_rates: [
    {
      role_key: "security_guard",
      role_label: "Security Guard",
      quantity: 275,
      unit_cost_monthly: 25000,
      margin_percent: 15,
      gst_percent: 18,
    },
    {
      role_key: "supervisor",
      role_label: "Supervisor",
      quantity: 28,
      unit_cost_monthly: 35000,
      margin_percent: 15,
      gst_percent: 18,
    },
    {
      role_key: "control_room_operator",
      role_label: "Control Room Operator",
      quantity: 12,
      unit_cost_monthly: 32000,
      margin_percent: 15,
      gst_percent: 18,
    },
  ],
  commercial_assumptions: [
    "Client will provide workspace, utilities, and induction facilities at each site.",
    "Statutory minimum wages and applicable labour laws are incorporated in unit rates.",
    "Shift patterns and headcount are as per RFP scope; surges require change order.",
    "GST is applied at prevailing rates on taxable components.",
  ],
  commercial_exclusions: [
    "Emergency staffing surges beyond 10% of deployed headcount unless separately agreed.",
    "Client-provided equipment maintenance and capital expenditure.",
    "Third-party statutory fee increases after price validity date.",
  ],
  authorized_signatory: "Rajesh Verma",
  signatory_designation: "Director — Commercial & Contracts",
  company_legal_name: "Meridian Secure Solutions Pvt. Ltd.",
};
