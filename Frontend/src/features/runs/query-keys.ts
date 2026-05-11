import type { RunListRequestBody } from "./types";

export const runsKeys = {
  root: ["runs"] as const,
  list: (body: RunListRequestBody) => [...runsKeys.root, "list", body] as const,
  row: (runId: string) => [...runsKeys.root, "row", runId] as const,
  results: (runId: string) => [...runsKeys.root, "results", runId] as const,
  latestExecution: (runId: string) => [...runsKeys.root, "latestExecution", runId] as const,
};
