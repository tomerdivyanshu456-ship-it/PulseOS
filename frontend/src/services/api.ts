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
