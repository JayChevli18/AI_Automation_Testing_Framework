import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

export type ArtifactIndexResponse = {
  success: boolean;
  run_id: string;
  execution_id: string | null;
  artifacts: Record<string, unknown>;
};

export async function fetchArtifacts(
  runId: string,
  executionId?: string | null,
): Promise<Record<string, unknown>> {
  const params =
    executionId !== undefined && executionId !== null && executionId !== ""
      ? { execution_id: executionId }
      : undefined;
  const { data } = await apiClient.get<ArtifactIndexResponse>(
    `${API_TESTS}/runs/${encodeURIComponent(runId)}/artifacts`,
    params ? { params } : {},
  );
  if (!data.success) {
    throw new Error("Failed to load artifacts");
  }
  return data.artifacts;
}
