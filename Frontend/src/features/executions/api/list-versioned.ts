import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

export type VersionedExecutionsListResponse = {
  success: boolean;
  run_id: string;
  executions: Record<string, unknown>[];
};

export async function fetchVersionedExecutions(runId: string): Promise<Record<string, unknown>[]> {
  const { data } = await apiClient.get<VersionedExecutionsListResponse>(
    `${API_TESTS}/versioned/${encodeURIComponent(runId)}/executions`,
  );
  if (!data.success) {
    throw new Error("Failed to list executions");
  }
  return data.executions;
}
