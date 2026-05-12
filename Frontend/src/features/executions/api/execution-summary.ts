import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

export type VersionedExecutionSummaryResponse = {
  success: boolean;
  run_id: string;
  execution_id: string;
  summary: Record<string, unknown>;
};

export async function fetchVersionedExecutionSummary(
  runId: string,
  executionId: string,
): Promise<Record<string, unknown>> {
  const { data } = await apiClient.get<VersionedExecutionSummaryResponse>(
    `${API_TESTS}/versioned/${encodeURIComponent(runId)}/executions/${encodeURIComponent(executionId)}/summary`,
  );
  if (!data.success) {
    throw new Error("Failed to load execution summary");
  }
  return data.summary;
}
