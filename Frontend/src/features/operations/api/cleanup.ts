import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

export type CleanupRunsBody = {
  retain_days: number;
  dry_run: boolean;
  max_delete: number;
};

export type CleanupRunsResponse = {
  success: boolean;
  message: string;
  deleted_run_ids: string[];
  scanned: number;
};

export async function cleanupRuns(body: CleanupRunsBody): Promise<CleanupRunsResponse> {
  const { data } = await apiClient.post<CleanupRunsResponse>(`${API_TESTS}/runs/cleanup`, body);
  if (!data.success) {
    throw new Error(data.message || "Cleanup failed");
  }
  return data;
}
