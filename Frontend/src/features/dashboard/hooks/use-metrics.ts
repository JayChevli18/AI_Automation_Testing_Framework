"use client";

import { useQuery } from "@tanstack/react-query";

import { fetchMetrics } from "../api/metrics";
import { dashboardKeys } from "../query-keys";

export function useMetrics() {
  return useQuery({
    queryKey: dashboardKeys.metrics(),
    queryFn: fetchMetrics,
  });
}
