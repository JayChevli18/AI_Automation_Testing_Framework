import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

type CancelResponse = {
  success: boolean;
  run_id: string;
  status: string;
  message: string;
};

export async function cancelRun(runId: string, reason?: string | null): Promise<CancelResponse> {
  const { data } = await apiClient.post<CancelResponse>(
    `${API_TESTS}/runs/${encodeURIComponent(runId)}/cancel`,
    { reason: reason ?? null },
  );
  if (!data.success) {
    throw new Error("Cancel failed");
  }
  return data;
}
