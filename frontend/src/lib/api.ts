const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface PullRequestInfo {
  url: string;
  title: string | null;
  number: number | null;
  merged: boolean;
  merged_at: string | null;
}

export interface OrchestratedSession {
  session_id: string;
  devin_url: string;
  github_issue_number: number;
  github_issue_title: string;
  github_issue_url: string;
  github_issue_labels: string[];
  status: "pending" | "running" | "completed" | "failed" | "suspended" | "merged";
  status_detail: string | null;
  acus_consumed: number;
  estimated_acus: number | null;
  num_user_messages: number | null;
  num_devin_messages: number | null;
  session_size: string | null;
  created_at: number;
  completed_at: number | null;
  duration_seconds: number | null;
  pull_requests: PullRequestInfo[];
  error: string | null;
  merge_strategy: string | null;
  merge_strategy_reason: string | null;
  issue_closed: boolean;
  issue_closed_at: number | null;
}

export interface Metrics {
  total_sessions: number;
  active_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  success_rate: number;
  total_acus: number;
  avg_acus_per_session: number;
  total_estimated_acus: number;
  avg_estimated_acus: number;
  avg_resolution_seconds: number | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  active_sessions: number;
  total_sessions: number;
}

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function getSessions(): Promise<OrchestratedSession[]> {
  return fetchJSON<OrchestratedSession[]>("/api/sessions");
}

export function getMetrics(): Promise<Metrics> {
  return fetchJSON<Metrics>("/api/metrics");
}

export function getHealth(): Promise<HealthResponse> {
  return fetchJSON<HealthResponse>("/api/health");
}
