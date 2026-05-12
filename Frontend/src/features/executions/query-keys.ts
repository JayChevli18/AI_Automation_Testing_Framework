export const executionsKeys = {
  root: ["executions"] as const,
  list: (runId: string) => [...executionsKeys.root, "list", runId] as const,
  summary: (runId: string, executionId: string) =>
    [...executionsKeys.root, runId, executionId, "summary"] as const,
  reports: (runId: string, executionId: string) =>
    [...executionsKeys.root, runId, executionId, "reports"] as const,
  artifacts: (runId: string, executionId: string) =>
    [...executionsKeys.root, runId, executionId, "artifacts"] as const,
};
