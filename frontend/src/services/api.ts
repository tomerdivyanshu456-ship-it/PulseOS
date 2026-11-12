import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

export interface AnalyticsOverview {
  data_source: string;
  period: {
    start_date: string;
    end_date: string;
  };
  metrics: {
    daily_active_users: number;
    monthly_active_users: number;
    conversion_rate: number;
    total_revenue: number;
    total_users: number;
    total_events: number;
    repeat_users: number;
    repeat_user_rate: number;
    average_events_per_user: number;
  };
  funnel: Array<{
    stage: string;
    users: number;
  }>;
  daily_activity: Array<{
    date: string;
    active_users: number;
  }>;
  retention_cohorts: Array<{
    cohort: string;
    cohort_size: number;
    weeks: Array<{
      week: number;
      active_users: number;
      retention_rate: number;
    }>;
  }>;
  event_adoption: Array<{
    event_name: string;
    active_users: number;
    event_count: number;
    user_adoption_rate: number;
  }>;
  adoption_note: string;
  feature_intelligence: {
    mapped_feature_count: number;
    mapping_note: string;
    features: Array<{
      feature: string;
      active_users: number;
      event_count: number;
      adoption_rate: number;
      events_per_active_user: number;
      repeat_users: number;
      repeat_usage_rate: number;
      reach_label: string;
      interpretation: string;
    }>;
  };
}

export interface ProductOpportunitiesResponse {
  status: "ready" | "partial" | "no_data";
  opportunities: Array<{
    id: string;
    title: string;
    feature: string;
    priority: "Investigate" | "Validate" | "Monitor";
    priority_score: number;
    review_count: number;
    average_rating: number;
    severity_score: number;
    evidence_strength: number;
    customer_signal: {
      topic: string;
      review_count: number;
      average_rating: number;
      evidence: Array<{ rating: number; review_text: string }>;
    };
    behavior_signal: null | {
      label: string;
      value: number;
      unit: string;
      detail: string;
      method: string;
    };
    recommendation: string;
    confidence_note: string;
  }>;
  data_gaps: string[];
  sources?: { events: boolean; reviews: boolean };
  methodology: string;
}

export async function getProductOpportunities(): Promise<ProductOpportunitiesResponse> {
  const response = await api.get("/api/opportunities");
  return response.data;
}

export async function getHealth() {
  const response = await api.get("/api/health");
  return response.data;
}

export async function getAnalytics(): Promise<AnalyticsOverview> {
  const response = await api.get("/api/analytics/overview");
  return response.data;
}

export async function uploadDataset(
  datasetType: "events" | "reviews",
  file: File
) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(
    `/api/datasets/upload/${datasetType}`,
    formData
  );

  return response.data;
}

export async function getDatasets() {
  const response = await api.get("/api/datasets");
  return response.data.datasets;
}

export async function getDatasetPreview(datasetId: string) {
  const response = await api.get(
    `/api/datasets/${datasetId}/preview`
  );

  return response.data;
}


export interface VoiceOfCustomerOverview {
  data_source: string;
  filename: string;
  total_reviews: number;
  average_rating: number;
  sentiment_distribution: Array<{
    sentiment: string;
    count: number;
  }>;
  rating_distribution: Array<{
    rating: number;
    count: number;
  }>;
  topics: Array<{
    key: string;
    label: string;
    keywords: string[];
    review_count: number;
    average_rating: number;
    priority_score: number;
    priority: string;
    evidence_level: string;
    recommendation: string;
    evidence: Array<{
      rating: number;
      review_text: string;
    }>;
  }>;
  negative_evidence: Array<{
    rating: number;
    review_text: string;
    sentiment: string;
  }>;
  methodology: {
    sentiment: string;
    topics: string;
    prioritisation: string;
  };
}

export async function getVoiceOfCustomer(): Promise<VoiceOfCustomerOverview> {
  const response = await api.get("/api/analytics/voice-of-customer");
  return response.data;
}


export interface AnalystFinding {
  title: string;
  detail: string;
  type: "metric" | "customer_feedback";
}

export interface AnalystEvidence {
  type: string;
  rating: number;
  text: string;
  sentiment: string;
}

export interface AnalystRecommendation {
  title: string;
  action: string;
  rationale: string;
  validation: string;
}

export interface AnalystPriorityItem {
  label: string;
  review_count: number;
  average_rating: number;
  priority_score: number;
  severity_score: number;
  evidence_strength: number;
  evidence_label: string;
  quadrant: string;
}

export interface AnalystConversationTurn {
  role: "user" | "assistant";
  content: string;
}

export interface AnalystResponse {
  question: string;
  answer: string;
  findings: AnalystFinding[];
  evidence: AnalystEvidence[];
  sources: Array<{ name: string; detail: string }>;
  limitations: string[];
  recommendations: AnalystRecommendation[];
  priority_matrix: AnalystPriorityItem[];
  funnel_analysis: null | {
    unit: string;
    method: string;
    reliability_note: string;
    stages: Array<{ stage: string; count: number }>;
    conversion_rates: {
      view_to_cart: number;
      cart_to_purchase: number;
      view_to_purchase: number;
    };
    drop_offs: {
      view_to_cart: number;
      cart_to_purchase: number;
    };
  };
  context_used: boolean;
}

export async function askAnalyst(
  question: string,
  history: AnalystConversationTurn[] = []
): Promise<AnalystResponse> {
  const response = await api.post("/api/analyst/ask", { question, history });
  return response.data;
}


export interface Experiment {
  id: string;
  name: string;
  opportunity_id: string | null;
  opportunity_title: string | null;
  hypothesis: string;
  rationale: string;
  primary_metric: string;
  secondary_metrics: Array<{ name: string; definition?: string }>;
  guardrails: Array<{ name: string; direction?: string }>;
  baseline_rate: number;
  minimum_detectable_effect: number;
  confidence_level: number;
  power: number;
  sample_size_per_arm: number;
  duration_days: number;
  status: "draft" | "running" | "completed" | "archived";
  created_at: string;
  updated_at: string;
}

export interface ExperimentDraft {
  name: string;
  opportunity_id: string;
  opportunity_title: string;
  hypothesis: string;
  rationale: string;
  primary_metric: string;
  secondary_metrics: Array<{ name: string; definition?: string }>;
  guardrails: Array<{ name: string; direction?: string }>;
  baseline_rate: number;
  minimum_detectable_effect: number;
  confidence_level: number;
  power: number;
  daily_eligible_users: number;
}

export interface ExperimentPlan {
  name: string;
  hypothesis: string;
  rationale: string;
  primary_metric: { name: string; definition: string; type: string };
  secondary_metrics: Array<{ name: string; definition: string }>;
  guardrails: Array<{ name: string; direction: string }>;
  evidence_note: string;
}

export interface ExperimentAnalysis {
  control: { users: number; conversions: number; conversion_rate: number; confidence_interval: [number, number] };
  variant: { users: number; conversions: number; conversion_rate: number; confidence_interval: [number, number] };
  absolute_lift: number;
  relative_lift_percent: number | null;
  difference_confidence_interval: [number, number];
  sample_size_reached: boolean | null;
  guardrails: Array<{ name: string; control_rate: number; variant_rate: number; absolute_change: number; status: string; threshold: number }>;
  interpretation: string;
  methodology: string;
}

export async function generateExperimentPlan(opportunity: ProductOpportunitiesResponse["opportunities"][number]): Promise<ExperimentPlan> {
  const response = await api.post("/api/experiments/plan", { opportunity });
  return response.data;
}

export async function getExperiments(): Promise<Experiment[]> {
  const response = await api.get("/api/experiments");
  return response.data.experiments;
}

export async function createExperiment(payload: ExperimentDraft): Promise<Experiment> {
  const response = await api.post("/api/experiments", payload);
  return response.data;
}

export async function updateExperimentStatus(id: string, status: Experiment["status"]): Promise<Experiment> {
  const response = await api.patch(`/api/experiments/${id}/status`, { status });
  return response.data;
}

export async function analyzeExperiment(payload: {
  control_users: number;
  control_conversions: number;
  variant_users: number;
  variant_conversions: number;
  planned_sample_size_per_arm?: number;
  confidence_level?: number;
  guardrails?: Array<{ name: string; control_rate: number; variant_rate: number; max_increase?: number }>;
}): Promise<ExperimentAnalysis> {
  const response = await api.post("/api/experiments/analyze", payload);
  return response.data;
}



export interface ExperimentDecision {
  experiment_id: string;
  experiment_name: string;
  recommendation: "Ship" | "Iterate" | "Stop";
  reasons: string[];
  analysis: ExperimentAnalysis;
  events: {
    exposure_event: string;
    conversion_event: string;
    source_rows: number;
    tagged_exposure_rows: number;
    exposed_users: number;
    conflicting_assignment_users_excluded: number;
  };
  guardrail_note: string;
  limitations: string[];
}

export async function getExperimentDecision(
  id: string,
  payload: {
    exposure_event: string;
    conversion_event: string;
    guardrails?: Array<{ name: string; event_name: string; max_increase: number }>;
  }
): Promise<ExperimentDecision> {
  const response = await api.post(`/api/experiments/${id}/decision`, payload);
  return response.data;
}


export interface StrategyRecommendation {
  id: string;
  rank: number;
  title: string;
  feature: string;
  priority: string;
  priority_score: number;
  impact_score: number;
  confidence_score: number;
  effort_estimate: number;
  effort_label: string;
  customer_evidence: {
    review_count: number;
    average_rating: number | null;
    examples: Array<{ rating: number; review_text: string }>;
  };
  behavioral_evidence: null | {
    label: string;
    value: number;
    unit: string;
    detail: string;
    method?: string;
  };
  action: string;
  expected_metric: string;
  success_measurement: string;
  linked_experiment_count: number;
  experiment_names: string[];
  evidence_note: string;
  score_explanation: string;
}

export interface ProductStrategyResponse {
  status: "ready" | "partial" | "no_data";
  summary: {
    opportunities_reviewed: number;
    high_priority_count: number;
    experiments_linked: number;
    top_recommendation: string | null;
  };
  recommendations: StrategyRecommendation[];
  data_gaps: string[];
  sources: { events: boolean; reviews: boolean };
  methodology: string;
}

export async function getProductStrategy(): Promise<ProductStrategyResponse> {
  const response = await api.get("/api/strategy");
  return response.data;
}

export async function prioritiseProductStrategy(
  effortEstimates: Record<string, number>
): Promise<ProductStrategyResponse> {
  const response = await api.post("/api/strategy/prioritise", {
    effort_estimates: effortEstimates,
  });
  return response.data;
}


export interface ProductHealthPillar {
  id: string;
  title: string;
  score: number;
  status: "healthy" | "needs_attention" | "at_risk";
  summary: string;
  metrics: Array<{ label: string; value: number; unit: string }>;
  source: string;
  benchmark: string;
  caveat: string;
}

export interface ProductHealthScorecardResponse {
  status: "ready" | "partial" | "no_data";
  overall_score: number | null;
  overall_label: string;
  score_coverage: { available_pillars: number; total_pillars: number };
  period: { start_date: string; end_date: string } | null;
  pillars: ProductHealthPillar[];
  strongest_areas: Array<{ title: string; score: number }>;
  areas_to_investigate: Array<{ title: string; score: number }>;
  data_gaps: string[];
  sources: { events: boolean; reviews: boolean; experiments: boolean };
  methodology: string;
}

export async function getProductHealthScorecard(): Promise<ProductHealthScorecardResponse> {
  const response = await api.get("/api/health-scorecard");
  return response.data;
}


export interface SegmentIntelligenceRow {
  segment: string;
  users: number;
  user_share: number;
  events: number;
  events_per_user: number;
  repeat_users: number;
  repeat_user_rate: number;
  purchasing_users: number;
  purchase_user_rate: number;
  purchase_revenue?: number;
  revenue_per_user?: number;
}

export interface SegmentIntelligenceResponse {
  status: "ready" | "no_dimensions";
  dimensions: Array<{ key: string; label: string; values: number }>;
  selected_dimension: string | null;
  total_users: number;
  period?: { start_date: string; end_date: string };
  segments: SegmentIntelligenceRow[];
  methodology: string;
}

export async function getSegmentIntelligence(dimension?: string): Promise<SegmentIntelligenceResponse> {
  const response = await api.get("/api/analytics/segments", {
    params: dimension ? { dimension } : undefined,
  });
  return response.data;
}
