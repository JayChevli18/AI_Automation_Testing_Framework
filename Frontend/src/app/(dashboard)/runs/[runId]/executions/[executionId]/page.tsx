import { ExecutionDetailView } from "@/features/executions/components/execution-detail-view";

export default async function ExecutionDetailPage({
  params,
}: {
  params: Promise<{ runId: string; executionId: string }>;
}) {
  const { runId, executionId } = await params;
  return <ExecutionDetailView runId={runId} executionId={executionId} />;
}
