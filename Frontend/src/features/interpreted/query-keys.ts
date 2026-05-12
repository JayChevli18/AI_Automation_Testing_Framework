export const interpretedKeys = {
  root: ["interpreted"] as const,
  read: (runId: string) => [...interpretedKeys.root, runId] as const,
};
