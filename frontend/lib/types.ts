// Mirrors ARCHITECTURE.md Section 5.1 (DealState) and Section 9 (API contracts).

export type QueryType = "comps_search" | "valuation" | "compliance_check" | "full_memo";
export type PropertyType = "Apartment" | "Villa" | "Townhouse";
export type TickType = "Sale" | "Off-Plan" | "Mortgage";

export interface Tick {
  building: string;
  community: string;
  beds: number;
  price: number;
  type: TickType;
}

export type DataProvenance = "synthetic" | "dld_kaggle" | "licensed_partner";

export interface Comp {
  transaction_id: string;
  building: string;
  community: string;
  property_type: PropertyType;
  bedrooms: number;
  size_sqft: number;
  price: number;
  price_per_sqft: number;
  date: string;
  data_provenance?: DataProvenance | string;
}

export interface ComplianceClause {
  clause_id: string;
  text: string;
  source_doc: string;
  similarity: number;
  review_status?: "unreviewed" | "pending_review" | "reviewed";
  reviewed_by?: string | null;
  review_date?: string | null;
}

export interface AgentTraceEntry {
  agent: "query" | "comps" | "valuation" | "compliance" | "memo";
  status: "pending" | "running" | "done" | "error";
  detail?: string;
  count?: number;
  timestamp?: string;
}

export interface DealState {
  query_id: string;
  raw_query: string;

  query_type?: QueryType | null;
  community?: string | null;
  property_type?: PropertyType | null;
  bedrooms?: number | null;
  budget_min?: number | null;
  budget_max?: number | null;
  project_id?: string | null;

  retrieved_comps: Comp[];

  valuation_low?: number | null;
  valuation_high?: number | null;
  valuation_method?: string | null;
  valuation_rationale?: string | null;

  retrieved_clauses: ComplianceClause[];
  compliance_flags: string[];
  compliance_summary?: string | null;

  memo_markdown?: string | null;

  agent_trace: AgentTraceEntry[];

  // Merged in by GET /deals/{id} from the persisted DealQuery row (Phase 4) --
  // job metadata, not part of the pipeline's own output.
  job_status?: DealStatus;
  attempt_count?: number;
}

// Mirrors the backend's persisted DealQuery.status column (Phase 4: job
// durability) -- the authoritative record, not derived from agent_trace.
export type DealStatus = "pending" | "running" | "done" | "failed";

export interface DealSummary {
  query_id: number;
  raw_query: string;
  query_type?: QueryType | null;
  status: DealStatus;
  created_at?: string | null;
}

export interface MarketTrendPoint {
  community: string;
  month: string;
  avg_price_per_sqft: number;
}

export interface DeveloperLeaderboardEntry {
  developer_id: string;
  name: string;
  track_record_score: number;
  active_projects_count: number;
  delivery_delay_rate: number;
}

export interface OffPlanFunnelEntry {
  project_id: string;
  name: string;
  community: string;
  percent_sold: number;
}
