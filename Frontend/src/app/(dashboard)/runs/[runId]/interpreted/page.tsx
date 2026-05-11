import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default async function InterpretedEditorPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Interpreted steps</h1>
      <Card>
        <CardHeader>
          <CardTitle>{runId}</CardTitle>
          <CardDescription>
            Editor with GET bootstrap and PATCH + <code className="rounded bg-muted px-1 text-xs">expected_revision</code>{" "}
            will be implemented next.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
