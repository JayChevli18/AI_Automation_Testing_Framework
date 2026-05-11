import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function ExecutionsListPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Executions</h1>
      <Card>
        <CardHeader>
          <CardTitle>Run {runId}</CardTitle>
          <CardDescription>
            Versioned execution list (
            <code className="rounded bg-muted px-1 text-xs">{`GET /api/tests/versioned/{run_id}/executions`}</code>
            ) will be wired here.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
