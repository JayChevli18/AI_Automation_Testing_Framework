export type RunListSortBy =
  | "run_id"
  | "file_id"
  | "status"
  | "environment"
  | "created_at"
  | "updated_at";

export type RunListSortOrder = "asc" | "desc";

export type RunListFilter = {
  field: RunListSortBy;
  operator: "equals" | "contains" | "gte" | "lte";
  value: string | number;
};

export type RunListRequestBody = {
  page: number;
  limit: number;
  search: string | null;
  sortingOptions: {
    sortBy: RunListSortBy;
    sortOrder: RunListSortOrder;
  };
  filters: RunListFilter[];
};

export type RunListItem = {
  run_id: string;
  file_id: string;
  status: string;
  environment: string;
  created_at: string;
  updated_at: string;
};

export type RunListMeta = {
  currentPage: number;
  totalPages: number;
  totalItems: number;
  itemsPerPage: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
};

export type RunListData = {
  list: RunListItem[];
  meta: RunListMeta;
};

export type RunPipelineBody = {
  file_id: string;
  environment: "beta" | "live";
  headless: boolean;
  continue_on_failure: boolean;
  step_timeout_ms: number;
  max_cases: number | null;
  allow_live_mutations: boolean;
};

export type ExecuteVersionedBody = {
  interpret_run_id: string;
  environment: "beta" | "live";
  headless: boolean;
  continue_on_failure: boolean;
  step_timeout_ms: number;
  allow_live_mutations: boolean;
};

export type RunCounts = {
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  skipped_cases: number;
  running_cases: number;
  pending_cases: number;
};

export type RunResultResponse = {
  success: boolean;
  run_id: string;
  status: string;
  counts: RunCounts;
};

export type LatestExecutionResponse = {
  success: boolean;
  run_id: string;
  execution_id: string | null;
  execution: Record<string, unknown> | null;
};
