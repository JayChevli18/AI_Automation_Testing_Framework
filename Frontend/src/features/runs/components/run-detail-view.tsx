"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useId, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { dashboardKeys } from "@/features/dashboard/query-keys";
import { executionsKeys } from "@/features/executions/query-keys";
import { interpretedKeys } from "@/features/interpreted/query-keys";
import { cn } from "@/lib/utils";
import { getApiError } from "@/shared/api/client";

import { cancelRun } from "../api/cancel-run";
import { executeVersioned } from "../api/execute-versioned";
import { fetchLatestExecution } from "../api/latest-execution";
import { fetchRunListItem } from "../api/list-runs";
import { fetchRunResults } from "../api/run-results";
import { runsKeys } from "../query-keys";
import type { ExecuteVersionedBody, RunResultResponse } from "../types";

import { StatusBadge } from "./status-badge";
import { formatDateTime } from "../lib/format";

function pollWhileActive(status: string | undefined): number | false {
  if (!status) return false;
  return status === "running" || status === "queued" ? 2500 : false;
}

export function RunDetailView({ runId }: { runId: string }) {
  const queryClient = useQueryClient();
  const id = useId();
  const [actionError, setActionError] = useState<string | null>(null);

  const rowQ = useQuery({
    queryKey: runsKeys.row(runId),
    queryFn: () => fetchRunListItem(runId),
  });

  const resultsQ = useQuery({
    queryKey: runsKeys.results(runId),
    queryFn: () => fetchRunResults(runId),
    refetchInterval: (q) => pollWhileActive(q.state.data?.status),
  });

  const latestQ = useQuery({
    queryKey: runsKeys.latestExecution(runId),
    queryFn: () => fetchLatestExecution(runId),
    refetchInterval: () => {
      const r = queryClient.getQueryData<RunResultResponse>(runsKeys.results(runId));
      return pollWhileActive(r?.status);
    },
  });

  const [execEnv, setExecEnv] = useState<"beta" | "live">("beta");
  const [execHeadless, setExecHeadless] = useState(true);
  const [execCof, setExecCof] = useState(true);
  const [execTimeout, setExecTimeout] = useState(30_000);
  const [execLiveOk, setExecLiveOk] = useState(false);

  const execMut = useMutation({
    mutationFn: () => {
      if (execEnv === "live" && !execLiveOk) {
        throw new Error('Live runs require checking "Allow mutating actions on live".');
      }
      const body: ExecuteVersionedBody = {
        interpret_run_id: runId,
        environment: execEnv,
        headless: execHeadless,
        continue_on_failure: execCof,
        step_timeout_ms: execTimeout,
        allow_live_mutations: execLiveOk,
      };
      return executeVersioned(body);
    },
    onSuccess: async () => {
      setActionError(null);
      await queryClient.invalidateQueries({ queryKey: runsKeys.results(runId) });
      await queryClient.invalidateQueries({ queryKey: runsKeys.latestExecution(runId) });
      await queryClient.invalidateQueries({ queryKey: runsKeys.row(runId) });
      await queryClient.invalidateQueries({ queryKey: runsKeys.root });
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.root });
      await queryClient.invalidateQueries({ queryKey: executionsKeys.list(runId) });
      await queryClient.invalidateQueries({ queryKey: interpretedKeys.read(runId) });
    },
    onError: (e) => {
      setActionError(getApiError(e)?.message ?? (e as Error).message);
    },
  });

  const cancelMut = useMutation({
    mutationFn: () => cancelRun(runId, null),
    onSuccess: async () => {
      setActionError(null);
      await queryClient.invalidateQueries({ queryKey: runsKeys.results(runId) });
      await queryClient.invalidateQueries({ queryKey: runsKeys.row(runId) });
      await queryClient.invalidateQueries({ queryKey: runsKeys.root });
    },
    onError: (e) => {
      setActionError(getApiError(e)?.message ?? (e as Error).message);
    },
  });

  const loading = rowQ.isPending || resultsQ.isPending;
  const notFound = rowQ.isSuccess && rowQ.data === null;
  const loadError =
    rowQ.isError || resultsQ.isError
      ? getApiError(rowQ.error)?.message ??
        getApiError(resultsQ.error)?.message ??
        (rowQ.error as Error)?.message ??
        (resultsQ.error as Error)?.message
      : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-mono text-xl font-semibold tracking-tight">{runId}</h1>
          <p className="text-muted-foreground text-sm">Run folder and API actions for this interpret run.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/runs/${encodeURIComponent(runId)}/interpreted`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Interpreted steps
          </Link>
          <Link
            href={`/runs/${encodeURIComponent(runId)}/executions`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Executions
          </Link>
        </div>
      </div>

      {actionError && (
        <Card className="border-destructive/50">
          <CardHeader className="py-3">
            <CardTitle className="text-destructive text-base">Action failed</CardTitle>
            <CardDescription className="text-destructive/90">{actionError}</CardDescription>
          </CardHeader>
        </Card>
      )}

      {loadError && !loading && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive text-base">Could not load run</CardTitle>
            <CardDescription>{loadError}</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                void rowQ.refetch();
                void resultsQ.refetch();
              }}
            >
              Retry
            </Button>
            <Link href="/runs" className={cn(buttonVariants({ variant: "secondary" }))}>
              All runs
            </Link>
          </CardContent>
        </Card>
      )}

      {loading && (
        <div className="space-y-3">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {!loadError && notFound && (
        <Card>
          <CardHeader>
            <CardTitle>Run not found</CardTitle>
            <CardDescription>No run with this id exists in storage (or list filter could not find it).</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/runs" className={cn(buttonVariants({ variant: "outline" }))}>
              Back to runs
            </Link>
          </CardContent>
        </Card>
      )}

      {!loadError && !loading && !notFound && rowQ.data && resultsQ.data && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <span className="text-muted-foreground">Status</span>
                <div className="mt-1">
                  <StatusBadge status={rowQ.data.status} />
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">API status</span>
                <div className="mt-1">
                  <StatusBadge status={resultsQ.data.status} />
                </div>
              </div>
              <div>
                <span className="text-muted-foreground">File</span>
                <p className="font-mono text-xs">{rowQ.data.file_id}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Environment</span>
                <p className="capitalize">{rowQ.data.environment}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Created</span>
                <p>{formatDateTime(rowQ.data.created_at)}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Updated</span>
                <p>{formatDateTime(rowQ.data.updated_at)}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Execution counts</CardTitle>
              <CardDescription>From <code className="rounded bg-muted px-1 text-xs">GET /results/…</code></CardDescription>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3 md:grid-cols-6">
              {(
                [
                  ["Total", resultsQ.data.counts.total_cases],
                  ["Passed", resultsQ.data.counts.passed_cases],
                  ["Failed", resultsQ.data.counts.failed_cases],
                  ["Skipped", resultsQ.data.counts.skipped_cases],
                  ["Running", resultsQ.data.counts.running_cases],
                  ["Pending", resultsQ.data.counts.pending_cases],
                ] as const
              ).map(([label, n]) => (
                <div key={label}>
                  <p className="text-muted-foreground">{label}</p>
                  <p className="text-lg font-medium tabular-nums">{n}</p>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Latest versioned execution</CardTitle>
              <CardDescription>
                From <code className="rounded bg-muted px-1 text-xs">GET …/executions/latest</code>
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {latestQ.isLoading && <Skeleton className="h-8 w-full max-w-md" />}
              {latestQ.isError && (
                <p className="text-destructive text-sm">
                  {getApiError(latestQ.error)?.message ?? (latestQ.error as Error).message}
                </p>
              )}
              {latestQ.isSuccess && (
                <>
                  <p>
                    <span className="text-muted-foreground">execution_id: </span>
                    <span className="font-mono text-xs">
                      {latestQ.data.execution_id ?? "—"}
                    </span>
                  </p>
                  {latestQ.data.execution && Object.keys(latestQ.data.execution).length > 0 && (
                    <pre className="bg-muted max-h-48 overflow-auto rounded-md p-3 text-xs">
                      {JSON.stringify(latestQ.data.execution, null, 2)}
                    </pre>
                  )}
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Execute stored interpreted steps</CardTitle>
              <CardDescription>
                <code className="rounded bg-muted px-1 text-xs">POST /execute-versioned</code> with{" "}
                <code className="rounded bg-muted px-1 text-xs">interpret_run_id</code> set to this run.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="grid gap-2">
                  <Label htmlFor={`${id}-ex-env`}>Environment</Label>
                  <select
                    id={`${id}-ex-env`}
                    className="border-input bg-background ring-offset-background focus-visible:ring-ring flex h-8 rounded-md border px-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
                    value={execEnv}
                    disabled={execMut.isPending}
                    onChange={(e) => setExecEnv(e.target.value as "beta" | "live")}
                  >
                    <option value="beta">beta</option>
                    <option value="live">live</option>
                  </select>
                </div>
                <div className="grid gap-2">
                  <Label htmlFor={`${id}-ex-to`}>Step timeout (ms)</Label>
                  <Input
                    id={`${id}-ex-to`}
                    type="number"
                    min={1000}
                    value={execTimeout}
                    disabled={execMut.isPending}
                    onChange={(e) => setExecTimeout(Number(e.target.value) || 30_000)}
                  />
                </div>
              </div>
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`${id}-ex-head`}
                    checked={execHeadless}
                    disabled={execMut.isPending}
                    onCheckedChange={(v) => setExecHeadless(Boolean(v))}
                  />
                  <Label htmlFor={`${id}-ex-head`} className="font-normal">
                    Headless
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`${id}-ex-cof`}
                    checked={execCof}
                    disabled={execMut.isPending}
                    onCheckedChange={(v) => setExecCof(Boolean(v))}
                  />
                  <Label htmlFor={`${id}-ex-cof`} className="font-normal">
                    Continue on failure
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`${id}-ex-live`}
                    checked={execLiveOk}
                    disabled={execMut.isPending || execEnv !== "live"}
                    onCheckedChange={(v) => setExecLiveOk(Boolean(v))}
                  />
                  <Label htmlFor={`${id}-ex-live`} className="font-normal">
                    Allow mutating actions on live
                  </Label>
                </div>
              </div>
              <Button type="button" disabled={execMut.isPending} onClick={() => execMut.mutate()}>
                {execMut.isPending ? "Executing…" : "Execute versioned"}
              </Button>
            </CardContent>
          </Card>

          <Separator />

          <div>
            <h2 className="mb-2 text-sm font-medium">Cooperative cancel</h2>
            <p className="text-muted-foreground mb-3 text-sm">
              Requests cancellation when the run is queued, interpreted, or running.
            </p>
            <Button
              type="button"
              variant="destructive"
              disabled={cancelMut.isPending}
              onClick={() => {
                if (window.confirm("Request cancellation for this run?")) {
                  cancelMut.mutate();
                }
              }}
            >
              {cancelMut.isPending ? "Sending…" : "Request cancel"}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
