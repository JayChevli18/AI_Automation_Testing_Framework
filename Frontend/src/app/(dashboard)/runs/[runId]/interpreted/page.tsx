import { InterpretedEditorView } from "@/features/interpreted/components/interpreted-editor-view";

export default async function InterpretedEditorPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <InterpretedEditorView runId={runId} />;
}
