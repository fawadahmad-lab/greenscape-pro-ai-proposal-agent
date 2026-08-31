export type ProposalStatus =
  | "DRAFT"
  | "GENERATING"
  | "NEEDS_REVIEW"
  | "APPROVED"
  | "SENT"
  | "FAILED";

export interface ProposalListItem {
  id: number;
  client_name: string;
  status: ProposalStatus;
  estimated_total: number | null;
  created_at: string;
}

export interface ScopeItem {
  requested_work: string;
  catalog_item_name: string | null;
  quantity: number | null;
  confidence: number;
  notes: string;
}

export interface PricedLineItem {
  requested_work: string;
  catalog_item_name: string;
  category: string;
  unit: string;
  unit_price: number;
  quantity: number | null;
  line_total: number;
  confidence: number;
  quantity_uncertain: boolean;
  notes: string;
}

export interface Proposal {
  id: number;
  client_name: string;
  client_email: string;
  project_address: string;
  site_walk_notes: string;
  status: ProposalStatus;
  project_summary: string | null;
  scope_json: ScopeItem[] | null;
  pricing_json: PricedLineItem[] | null;
  estimated_total: number | null;
  assumptions_json: string[] | null;
  clarifying_questions_json: string[] | null;
  risk_flags_json: string[] | null;
  generated_proposal: string | null;
  created_at: string;
  updated_at: string;
  approved_at: string | null;
  sent_at: string | null;
}

export interface ProposalCreate {
  client_name: string;
  client_email: string;
  project_address: string;
  site_walk_notes: string;
}

export const STATUS_LABELS: Record<ProposalStatus, string> = {
  DRAFT: "Draft",
  GENERATING: "Generating",
  NEEDS_REVIEW: "Needs Review",
  APPROVED: "Approved",
  SENT: "Sent",
  FAILED: "Failed",
};
