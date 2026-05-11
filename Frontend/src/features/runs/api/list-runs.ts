import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

import type { RunListData, RunListItem, RunListRequestBody } from "../types";

type ListResponse = {
  success: boolean;
  message?: string;
  data: RunListData;
};

export async function listRuns(body: RunListRequestBody): Promise<RunListData> {
  const { data } = await apiClient.post<ListResponse>(`${API_TESTS}/runs/list`, body);
  if (!data.success || !data.data) {
    throw new Error(data.message ?? "Failed to list runs");
  }
  return data.data;
}

export async function fetchRunListItem(runId: string): Promise<RunListItem | null> {
  const data = await listRuns({
    page: 1,
    limit: 1,
    search: null,
    sortingOptions: { sortBy: "updated_at", sortOrder: "desc" },
    filters: [{ field: "run_id", operator: "equals", value: runId }],
  });
  return data.list[0] ?? null;
}
