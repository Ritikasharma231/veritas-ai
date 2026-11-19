export interface AnalysisResponse {
  id: string | null;
  input_type: string;
  source_url: string | null;
  title: string | null;
  prediction: string | null;
  confidence: number | null;
  probabilities: Record<string, number> | null;
  explanation: Record<string, unknown> | null;
  linguistic_signals: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  model_name: string | null;
  inference_ms: number | null;
  truncated?: boolean;
  status: string;
  error: string | null;
  created_at: string | null;
}

export interface AnalysisListItem {
  id: string;
  input_type: string;
  title: string | null;
  prediction: string | null;
  confidence: number | null;
  source_url: string | null;
  created_at: string;
  status: string;
}

export interface AnalysisListResponse {
  items: AnalysisListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface DashboardStats {
  total_analyses: number;
  completed_analyses: number;
  classification_distribution: Record<string, number>;
  avg_confidence: number | null;
  daily_trend: { date: string; total: number; Fake: number; Real: number }[];
  confidence_histogram: { range: string; count: number }[];
  recent_activity: {
    id: string;
    title: string;
    prediction: string | null;
    confidence: number | null;
    created_at: string;
  }[];
  avg_inference_ms: number | null;
  data_source: string;
  generated_at: string;
}

export interface ModelInfo {
  available: boolean;
  model_name: string;
  labels: string[];
  device: string;
  error: string | null;
  model_path: string | null;
  hf_id: string | null;
  locally_finetuned: boolean;
  metrics: Record<string, unknown> | null;
  metrics_source: string | null;
}

export interface UrlPreview {
  url: string;
  final_url: string;
  title: string | null;
  author: string | null;
  publish_date: string | null;
  site_name: string | null;
  extractor: string;
  text_preview: string;
  text_length: number;
}

export interface Health {
  status: string;
  version: string;
  model_available: boolean;
  database: string;
  timestamp: string;
}

export interface LinguisticSignal {
  value: number | string;
  label: string;
  detail: string;
  severity: "info" | "warning" | "error";
}
