import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

import type { RunPipelineBody } from "../types";

type RunResponse = { success: boolean; run_id: string; status: string };

export async function startFullRun(body: RunPipelineBody): Promise<RunResponse> {
  const { data } = await apiClient.post<RunResponse>(`${API_TESTS}/run`, body);
  if (!data.success || !data.run_id) {
    throw new Error("Run failed");
  }
  return data;
}
