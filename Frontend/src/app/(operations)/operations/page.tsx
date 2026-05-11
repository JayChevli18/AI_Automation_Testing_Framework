import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function OperationsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Operations</h1>
      <Card>
        <CardHeader>
          <CardTitle>Cancel and cleanup</CardTitle>
          <CardDescription>
            Forms for <code className="rounded bg-muted px-1 text-xs">POST .../cancel</code> and{" "}
            <code className="rounded bg-muted px-1 text-xs">POST .../runs/cleanup</code> will be added in a later step.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
