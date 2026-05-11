"use client";

import { useMetrics } from "@/features/dashboard/hooks/use-metrics";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getApiError } from "@/shared/api/client";
import Link from "next/link";

export default function DashboardPage() {
  const q = useMetrics();
  const apiErr = q.error ? getApiError(q.error) : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          Metrics from the API. Start the FastAPI server so requests proxied through{" "}
          <code className="rounded bg-muted px-1 py-0.5 text-xs">/api/*</code> succeed.
        </p>
      </div>

      {q.isLoading && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      )}

      {q.isError && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Could not load metrics</CardTitle>
            <CardDescription>
              {apiErr?.message ?? (q.error as Error)?.message ?? "Unknown error"}
              {apiErr?.requestId ? (
                <span className="mt-2 block font-mono text-xs">
                  request_id: {apiErr.requestId}
                </span>
              ) : null}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button type="button" variant="outline" onClick={() => q.refetch()}>
              Retry
            </Button>
            <Link
              href="/settings"
              className={cn(buttonVariants({ variant: "secondary" }))}
            >
              Check API settings
            </Link>
          </CardContent>
        </Card>
      )}

      {q.isSuccess && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <MetricCard title="Total runs" value={q.data.total_runs} />
          <MetricCard title="Last 24 hours" value={q.data.runs_last_24h} />
          <MetricCard title="Last 7 days" value={q.data.runs_last_7d} />
          <MetricCard title="Active" value={q.data.active_runs} />
          <MetricCard title="Queued" value={q.data.queued_runs} />
          <MetricCard title="Cancelled" value={q.data.cancelled_runs} />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Quick actions</CardTitle>
          <CardDescription>Run management flows (more in the next steps).</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Link href="/runs/new" className={cn(buttonVariants())}>
            New run
          </Link>
          <Link href="/runs" className={cn(buttonVariants({ variant: "outline" }))}>
            All runs
          </Link>
        </CardContent>
      </Card>

      {q.isSuccess && Object.keys(q.data.by_status).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>By status</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-2">
            {Object.entries(q.data.by_status).map(([status, count]) => (
              <Badge key={status} variant="secondary">
                {status}: {count}
              </Badge>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function MetricCard({ title, value }: { title: string; value: number }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-3xl tabular-nums">{value}</CardTitle>
      </CardHeader>
    </Card>
  );
}
