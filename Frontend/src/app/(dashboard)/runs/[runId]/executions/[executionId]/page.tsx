import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function ExecutionDetailPage({
  params,
}: {
  params: Promise<{ runId: string; executionId: string }>;
}) {
  const { runId, executionId } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Execution</h1>
      <Card>
        <CardHeader>
          <CardTitle>
            {runId} / {executionId}
          </CardTitle>
          <CardDescription>
            Summary, reports, and artifact index tabs will connect to versioned endpoints.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
