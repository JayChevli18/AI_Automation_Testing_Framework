import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

import type { LatestExecutionResponse } from "../types";

export async function fetchLatestExecution(runId: string): Promise<LatestExecutionResponse> {
  const { data } = await apiClient.get<LatestExecutionResponse>(
    `${API_TESTS}/runs/${encodeURIComponent(runId)}/executions/latest`,
  );
  if (!data.success) {
    throw new Error("Failed to load latest execution");
  }
  return data;
}
