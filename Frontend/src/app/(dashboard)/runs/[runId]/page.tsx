import { RunDetailView } from "@/features/runs/components/run-detail-view";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunDetailView runId={runId} />;
}
