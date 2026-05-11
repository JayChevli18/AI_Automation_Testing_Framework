import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

export type RunMetrics = {
  total_runs: number;
  by_status: Record<string, number>;
  runs_last_24h: number;
  runs_last_7d: number;
  active_runs: number;
  queued_runs: number;
  cancelled_runs: number;
};

export type MetricsResponse = {
  success: boolean;
  metrics: RunMetrics;
};

export async function fetchMetrics(): Promise<RunMetrics> {
  const { data } = await apiClient.get<MetricsResponse>(`${API_TESTS}/metrics`);
  if (!data.success || !data.metrics) {
    throw new Error("Invalid metrics response");
  }
  return data.metrics;
}
