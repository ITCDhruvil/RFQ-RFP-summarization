export type ProposalStatus = "pending" | "processing" | "completed" | "failed";

export interface BidderProfile {
  company_name?: string;
  capabilities?: string[];
  certifications?: string[];
  key_personnel?: Array<{
    name?: string;
    role?: string;
    experience?: string;
  }>;
  reference_projects?: Array<{
    name?: string;
    client?: string;
    description?: string;
  }>;
  additional_notes?: string;
  knowledge_assets?: {
    policies?: string[];
    sops?: string[];
    service_catalog?: string[];
    training_programs?: string[];
    resumes?: string[];
    certifications?: string[];
    org_structure?: string;
  };
}

export interface ProposalSourceCitation {
  page?: number;
  section?: string;
  source_text?: string;
}

export interface ProposalTextBlock {
  text?: string;
  sources?: ProposalSourceCitation[];
}

export interface TechnicalApproachSection {
  title?: string;
  content?: string;
  sources?: ProposalSourceCitation[];
}

export interface ComplianceMatrixRow {
  requirement_ref?: string;
  category?: string;
  requirement_text?: string;
  vendor_response?: string;
  response?: string;
  methodology?: string;
  evidence?: Array<{
    evidence_id?: string;
    source_type?: string;
    source_ref?: string;
    excerpt?: string;
  }>;
  compliance_status?: string;
  compliance?: string;
  gap_status?: string;
  confidence_score?: number;
  sources?: ProposalSourceCitation[];
}

export interface ImplementationPhase {
  name?: string;
  duration?: string;
  deliverables?: string[];
}

export interface TeamRole {
  title?: string;
  responsibilities?: string;
  profile_ref?: string;
}

export interface ProposalGap {
  field?: string;
  reason?: string;
}

export interface GeneratedProposalData {
  meta?: {
    volumes?: string[];
    document_name?: string;
  };
  cover_letter?: ProposalTextBlock;
  executive_summary?: ProposalTextBlock & { confidence_score?: number };
  company_overview?: ProposalTextBlock & { confidence_score?: number };
  understanding_of_requirements?: ProposalTextBlock;
  why_choose_us?: {
    differentiators?: Array<{ claim?: string; evidence?: unknown[] }>;
    confidence_score?: number;
  };
  technical_approach?: {
    sections?: TechnicalApproachSection[];
  };
  staffing_approach?: ProposalTextBlock & { confidence_score?: number };
  training_framework?: ProposalTextBlock & { confidence_score?: number };
  compliance_matrix?: ComplianceMatrixRow[];
  transition_plan?: {
    phases?: ImplementationPhase[];
    confidence_score?: number;
  };
  implementation_plan?: {
    phases?: ImplementationPhase[];
    sources?: ProposalSourceCitation[];
  };
  team_and_staffing?: {
    roles?: TeamRole[];
  };
  operational_risks?: Array<{
    risk?: string;
    likelihood?: string;
    impact?: string;
    mitigation?: string;
    owner?: string;
    sources?: ProposalSourceCitation[];
  }>;
  risks_and_mitigations?: Array<{
    risk?: string;
    mitigation?: string;
    sources?: ProposalSourceCitation[];
  }>;
  assumptions_and_exclusions?: {
    assumptions?: string[];
    exclusions?: string[];
  };
  gaps_and_placeholders?: ProposalGap[];
  traceability_matrix?: Array<{
    requirement_id?: string;
    evidence_ids?: string[];
    proposal_section?: string;
    compliance_status?: string;
    gap_status?: string;
    confidence_score?: number;
  }>;
  _pipeline?: Record<string, unknown>;
  _meta?: Record<string, unknown>;
}

export interface GeneratedProposal {
  id: string;
  document_id: string;
  status: ProposalStatus;
  version: number;
  is_current: boolean;
  proposal_json: GeneratedProposalData;
  bidder_profile_snapshot: BidderProfile;
  model_metadata: Record<string, unknown>;
  total_tokens: number;
  error_message: string;
  last_error: Record<string, unknown>;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProposalStatusResponse {
  document_id: string;
  proposal_status: ProposalStatus | null;
  proposal_id: string | null;
  version: number | null;
  total_tokens: number | null;
  error_message?: string | null;
  summary_status: ProposalStatus | null;
}

export interface GenerateProposalResponse {
  message: string;
  document_id: string;
  proposal_id?: string;
  celery_task_id?: string;
  regenerate?: boolean;
  sync?: boolean;
}

export const EMPTY_BIDDER_PROFILE: BidderProfile = {
  company_name: "",
  capabilities: [""],
  certifications: [],
  key_personnel: [],
  reference_projects: [],
  additional_notes: "",
};

/** Sample company profile for testing proposal generation. */
export const SAMPLE_BIDDER_PROFILE: BidderProfile = {
  company_name: "Meridian Secure Solutions Pvt. Ltd.",
  capabilities: [
    "Integrated physical security and facility management",
    "24/7 command center and incident response",
    "Manned guarding, access control, and CCTV monitoring",
    "Workforce deployment across multi-site operations",
    "Training, SOP compliance, and audit-ready documentation",
  ],
  certifications: [
    "ISO 9001:2015 — Quality Management",
    "ISO 45001:2018 — Occupational Health & Safety",
    "PSARA licensed security agency",
    "Registered MSME and GST compliant",
  ],
  key_personnel: [
    {
      name: "Priya Sharma",
      role: "Project Director",
      experience: "18 years leading large-scale security and FM contracts",
    },
    {
      name: "Arun Mehta",
      role: "Operations Manager",
      experience: "12 years in multi-location guarding and SLA management",
    },
    {
      name: "Sneha Kapoor",
      role: "Compliance & Quality Lead",
      experience: "10 years in audit, SOP rollout, and client reporting",
    },
  ],
  reference_projects: [
    {
      name: "Metro Transit Security Program",
      client: "State Transport Authority",
      description:
        "5-year contract covering 42 stations, 1,200+ personnel, and 24/7 control room operations.",
    },
    {
      name: "Campus Facility Management",
      client: "National University Consortium",
      description:
        "Integrated security and housekeeping across 8 campuses with KPI-based monthly reporting.",
    },
  ],
  additional_notes:
    "Meridian has delivered 35+ public-sector security contracts over 15 years. " +
    "We maintain regional offices in Mumbai, Delhi, and Bengaluru with a bench strength " +
    "of 8,000 trained personnel. Our mobilization playbook supports 30-day go-live on " +
    "contracts of similar scale.",
  knowledge_assets: {
    policies: [
      "Corporate HSE policy — zero-harm workplace and incident reporting within 30 minutes",
      "Background verification and PSARA compliance policy for all deployed personnel",
      "Data privacy and confidentiality policy for client premises and personnel records",
    ],
    sops: [
      "Shift handover and roll-call SOP with supervisor sign-off",
      "Incident classification, escalation, and client notification SOP",
      "Cab escort, vehicle inspection, and female employee transport SOP",
      "Absenteeism backup activation SOP (trigger within 2 hours of no-show)",
    ],
    service_catalog: [
      "Manned guarding — static, mobile patrol, and access control",
      "24/7 security operations center with GPS-enabled supervision",
      "Event security and VIP movement coordination",
      "Integrated facility management add-ons (housekeeping, helpdesk)",
    ],
    training_programs: [
      "5-day induction: client SOPs, fire safety, first aid, soft skills",
      "Quarterly refresher: scenario drills, escalation simulation",
      "Supervisor academy: leadership, audit readiness, KPI reporting",
    ],
    org_structure:
      "Project Director → Operations Manager → Regional Supervisors → Site Supervisors → Guards. " +
      "Compliance & Quality function reports dotted-line to Project Director.",
    resumes: [],
    certifications: [],
  },
};
