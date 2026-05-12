import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

import type { InterpretedStepsPatchResponse } from "../types";

export type StepPatchPayload = {
  step_index: number;
  raw_step?: string;
  interpreted?: Record<string, unknown> | null;
  interpretation_error?: Record<string, string> | null;
};

export type CasePatchPayload = {
  test_case_id: string;
  step_patches: StepPatchPayload[];
};

export type PatchInterpretedBody = {
  patches: CasePatchPayload[];
  expected_revision: number | null;
};

export async function patchInterpretedSteps(
  runId: string,
  body: PatchInterpretedBody,
): Promise<InterpretedStepsPatchResponse> {
  const { data } = await apiClient.patch<InterpretedStepsPatchResponse>(
    `${API_TESTS}/runs/${encodeURIComponent(runId)}/interpreted-steps`,
    body,
  );
  if (!data.success) {
    throw new Error(data.message || "Patch failed");
  }
  return data;
}
