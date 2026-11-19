import type {
  AnalysisListResponse,
  AnalysisResponse,
  DashboardStats,
  Health,
  ModelInfo,
  UrlPreview,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : "Request failed");
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<Health>("/health"),
  analyzeText: (text: string, title?: string, saveHistory = true) =>
    request<AnalysisResponse>("/analyze/text", {
      method: "POST",
      body: JSON.stringify({ text, title, save_history: saveHistory }),
    }),
  analyzeUrl: (url: string, saveHistory = true) =>
    request<AnalysisResponse>("/analyze/url", {
      method: "POST",
      body: JSON.stringify({ url, save_history: saveHistory }),
    }),
  previewUrl: (url: string) =>
    request<UrlPreview>("/analyze/url/preview", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),
  listAnalyses: (params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== "") qs.set(k, String(v));
    });
    return request<AnalysisListResponse>(`/analyses?${qs.toString()}`);
  },
  getAnalysis: (id: string) => request<AnalysisResponse>(`/analyses/${id}`),
  deleteAnalysis: (id: string) =>
    request<void>(`/analyses/${id}`, { method: "DELETE" }),
  dashboardStats: () => request<DashboardStats>("/dashboard/stats"),
  modelInfo: () => request<ModelInfo>("/model/info"),
  modelMetrics: () =>
    request<{ available: boolean; metrics?: Record<string, unknown>; source?: string; detail?: string }>(
      "/model/metrics"
    ),
};
