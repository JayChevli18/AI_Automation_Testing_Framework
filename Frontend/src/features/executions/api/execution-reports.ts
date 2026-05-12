import { apiClient } from "@/shared/api/client";
import { API_TESTS } from "@/shared/constants/api-paths";

export type RunReportResponse = {
  success: boolean;
  run_id: string;
  allure_results_dir: string;
  allure_result_files: string[];
  html_report_path: string;
};

export async function fetchVersionedExecutionReports(
  runId: string,
  executionId: string,
): Promise<RunReportResponse> {
  const { data } = await apiClient.get<RunReportResponse>(
    `${API_TESTS}/versioned/${encodeURIComponent(runId)}/executions/${encodeURIComponent(executionId)}/reports`,
  );
  if (!data.success) {
    throw new Error("Failed to load report index");
  }
  return data;
}
