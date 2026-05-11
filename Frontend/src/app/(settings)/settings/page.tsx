import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
      <Card>
        <CardHeader>
          <CardTitle>API and preferences</CardTitle>
          <CardDescription>
            The dev server proxies <code className="rounded bg-muted px-1 text-xs">/api/*</code> to{" "}
            <code className="rounded bg-muted px-1 text-xs">API_BACKEND_ORIGIN</code> (see{" "}
            <code className="rounded bg-muted px-1 text-xs">.env.example</code>). Optional UI overrides can live here.
          </CardDescription>
        </CardHeader>
      </Card>
    </div>
  );
}
