import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

import type { ExecuteVersionedBody } from "../types";

type VersionedExecutionResponse = {
  success: boolean;
  run_id: string;
  execution_id: string;
  status: string;
};

export async function executeVersioned(body: ExecuteVersionedBody): Promise<VersionedExecutionResponse> {
  const { data } = await apiClient.post<VersionedExecutionResponse>(
    `${API_TESTS}/execute-versioned`,
    body,
  );
  if (!data.success || !data.execution_id) {
    throw new Error("Execute versioned failed");
  }
  return data;
}
