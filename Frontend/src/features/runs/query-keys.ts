export const runsKeys = {
  root: ["runs"] as const,
  list: (params: unknown) => [...runsKeys.root, "list", params] as const,
  detail: (runId: string) => [...runsKeys.root, "detail", runId] as const,
};
