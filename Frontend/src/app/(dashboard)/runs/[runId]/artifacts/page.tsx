import { ArtifactsExplorerView } from "@/features/runs/components/artifacts-explorer-view";

export default async function RunArtifactsPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <ArtifactsExplorerView runId={runId} />;
}
