import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

import type { RunResultResponse } from "../types";

export async function fetchRunResults(runId: string): Promise<RunResultResponse> {
  const { data } = await apiClient.get<RunResultResponse>(`${API_TESTS}/results/${runId}`);
  if (!data.success) {
    throw new Error("Failed to load run status");
  }
  return data;
}
