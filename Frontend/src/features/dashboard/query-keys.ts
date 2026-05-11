export const dashboardKeys = {
  root: ["dashboard"] as const,
  metrics: () => [...dashboardKeys.root, "metrics"] as const,
};
