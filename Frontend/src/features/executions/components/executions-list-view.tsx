"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { getApiError } from "@/shared/api/client";

import { fetchVersionedExecutions } from "../api/list-versioned";
import { executionsKeys } from "../query-keys";

import { formatDateTime } from "@/features/runs/lib/format";

function str(v: unknown): string {
  if (v === null || v === undefined) return "—";
  return String(v);
}

export function ExecutionsListView({ runId }: { runId: string }) {
  const q = useQuery({
    queryKey: executionsKeys.list(runId),
    queryFn: () => fetchVersionedExecutions(runId),
  });

  const rows = q.data ?? [];
  const sorted = [...rows].sort((a, b) => {
    const ta = str(a.started_at);
    const tb = str(b.started_at);
    return tb.localeCompare(ta);
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Executions</h1>
          <p className="text-muted-foreground font-mono text-sm">{runId}</p>
        </div>
        <Link href={`/runs/${encodeURIComponent(runId)}`} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
          Run detail
        </Link>
      </div>

      {q.isError && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Could not load executions</CardTitle>
            <CardDescription>
              {getApiError(q.error)?.message ?? (q.error as Error).message}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" variant="outline" onClick={() => void q.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {q.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}

      {q.isSuccess && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Versioned executions</CardTitle>
            <CardDescription>
              From <code className="rounded bg-muted px-1 text-xs">GET /api/tests/versioned/…/executions</code> manifest.
            </CardDescription>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Execution</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Finished</TableHead>
                  <TableHead className="text-right">Passed</TableHead>
                  <TableHead className="text-right">Failed</TableHead>
                  <TableHead className="text-right">Total</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-muted-foreground h-24 text-center">
                      No versioned executions yet. Run execute-versioned from run detail.
                    </TableCell>
                  </TableRow>
                ) : (
                  sorted.map((row, idx) => {
                    const rawId = row.execution_id;
                    const eid =
                      rawId !== null && rawId !== undefined && String(rawId) !== ""
                        ? String(rawId)
                        : null;
                    return (
                      <TableRow key={eid ?? `row-${idx}`}>
                        <TableCell className="font-mono text-xs">
                          {eid ? (
                            <Link
                              href={`/runs/${encodeURIComponent(runId)}/executions/${encodeURIComponent(eid)}`}
                              className="text-primary hover:underline"
                            >
                              {eid}
                            </Link>
                          ) : (
                            "—"
                          )}
                        </TableCell>
                        <TableCell className="capitalize">{str(row.status)}</TableCell>
                        <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                          {row.started_at ? formatDateTime(str(row.started_at)) : "—"}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                          {row.finished_at ? formatDateTime(str(row.finished_at)) : "—"}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{str(row.passed_cases)}</TableCell>
                        <TableCell className="text-right tabular-nums">{str(row.failed_cases)}</TableCell>
                        <TableCell className="text-right tabular-nums">{str(row.total_cases)}</TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
