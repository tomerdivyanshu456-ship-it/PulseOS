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
  };
  funnel: Array<{
    stage: string;
    users: number;
  }>;
  daily_activity: Array<{
    date: string;
    active_users: number;
  }>;
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

export interface AnalystResponse {
  question: string;
  answer: string;
  findings: AnalystFinding[];
  evidence: AnalystEvidence[];
  sources: Array<{
    name: string;
    detail: string;
  }>;
  limitations: string[];
}

export async function askAnalyst(question: string): Promise<AnalystResponse> {
  const response = await api.post("/api/analyst/ask", { question });
  return response.data;
}
