import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

import type { InterpretedStepsReadPayload } from "../types";

export async function fetchInterpretedSteps(runId: string): Promise<InterpretedStepsReadPayload> {
  const { data } = await apiClient.get<InterpretedStepsReadPayload>(
    `${API_TESTS}/runs/${encodeURIComponent(runId)}/interpreted-steps`,
  );
  if (!data.success) {
    throw new Error("Failed to load interpreted steps");
  }
  return data;
}
