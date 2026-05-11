import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function NewRunPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">New run</h1>
      <Card>
        <CardHeader>
          <CardTitle>Upload and interpret</CardTitle>
          <CardDescription>
            This page will implement <code className="rounded bg-muted px-1 text-xs">POST /upload</code> then{" "}
            <code className="rounded bg-muted px-1 text-xs">POST /interpret</code>, plus optional{" "}
            <code className="rounded bg-muted px-1 text-xs">POST /run</code>.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>
  );
}
