import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Run {runId}</h1>
      <Card>
        <CardHeader>
          <CardTitle>Run detail</CardTitle>
          <CardDescription>
            Latest execution, actions, and links to interpreted steps will be added in a following step.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
