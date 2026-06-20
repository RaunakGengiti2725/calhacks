// Mirrors dryrun_core.models.Report (the payload the Reporting stage emits).

export interface ReportSummary {
  designs_selected: number;
  designs_total: number;
  spend: number;
  budget: number;
  expected_distinct_successes: number;
  naive_expected_distinct_successes: number;
  expected_constructs: number;
  naive_expected_constructs: number;
  cost_per_success: number;
  uplift_ratio: number;
}

export interface FunnelCounts {
  generated: number;
  viability_passed: number;
  fold_passed: number;
  selected: number;
}

export interface Portfolio {
  method: string;
  selected_ids: string[];
  budget: number;
  total_cost: number;
  expected_successes: number;
  expected_distinct_successes: number;
  cost_per_success: number;
  count: number;
}

export interface PortfolioComparison {
  optimized: Portfolio;
  naive: Portfolio;
  expected_successes_uplift: number;
  dollars_naive_needs_to_match: number | null;
}

export interface SequenceSpacePoint {
  design_id: string;
  x: number;
  y: number;
  selected_optimized: boolean;
  selected_naive: boolean;
  success_probability: number;
}

export interface CandidateRow {
  design_id: string;
  sequence_preview: string;
  viability: number;
  fold_confidence: number | null;
  cost: number;
  success_probability: number;
  selected: boolean;
  selected_naive: boolean;
  mutations: string[];
}

export interface StructurePayload {
  design_id: string;
  is_wild_type: boolean;
  pdb: string;
  plddt: number[];
  mean_plddt: number;
  low_confidence_regions: [number, number][];
  mutation_positions: number[];
  misfold_flag: boolean;
}

export interface ReportMeta {
  mode: string;
  goal: string | null;
  seed_sequence: string;
  seed_length: number;
  candidate_count: number;
  budget: number;
  generated_at: string;
}

export interface Report {
  summary: ReportSummary;
  funnel: FunnelCounts;
  comparison: PortfolioComparison;
  candidates: CandidateRow[];
  sequence_space: SequenceSpacePoint[];
  structures: StructurePayload[];
  wild_type_structure: StructurePayload | null;
  plain_summary: string;
  meta: ReportMeta;
}

export interface AnalyzeRequest {
  natural?: string;
  seed?: string;
  goal?: string;
  budget?: number;
  candidates?: number;
}
