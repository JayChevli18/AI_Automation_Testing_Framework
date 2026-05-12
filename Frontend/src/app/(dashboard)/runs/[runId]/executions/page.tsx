import { ExecutionsListView } from "@/features/executions/components/executions-list-view";

export default async function ExecutionsListPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <ExecutionsListView runId={runId} />;
}
