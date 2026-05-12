"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchArtifacts } from "@/features/executions/api/artifacts";
import { fetchVersionedExecutions } from "@/features/executions/api/list-versioned";
import { executionsKeys } from "@/features/executions/query-keys";
import { cn } from "@/lib/utils";
import { getApiError } from "@/shared/api/client";

import { runsKeys } from "../query-keys";

function copyText(text: string) {
  void navigator.clipboard.writeText(text);
}

export function ArtifactsExplorerView({ runId }: { runId: string }) {
  const [executionId, setExecutionId] = useState<string>("");

  const execListQ = useQuery({
    queryKey: executionsKeys.list(runId),
    queryFn: () => fetchVersionedExecutions(runId),
  });

  const executionOptions = useMemo(() => {
    const rows = execListQ.data ?? [];
    return [...rows]
      .filter((r) => r.execution_id != null && String(r.execution_id) !== "")
      .map((r) => ({ id: String(r.execution_id), label: String(r.execution_id) }));
  }, [execListQ.data]);

  const scope = executionId === "" ? "_latest" : executionId;

  const artifactsQ = useQuery({
    queryKey: runsKeys.artifacts(runId, scope),
    queryFn: () =>
      fetchArtifacts(runId, executionId === "" ? undefined : executionId),
  });

  const a = artifactsQ.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Artifacts</h1>
          <p className="text-muted-foreground font-mono text-sm">{runId}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/runs/${encodeURIComponent(runId)}`} className={cn(buttonVariants({ variant: "outline", size: "sm" }))}>
            Run detail
          </Link>
          <Link
            href={`/runs/${encodeURIComponent(runId)}/executions`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Executions
          </Link>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Scope</CardTitle>
          <CardDescription>
            <code className="rounded bg-muted px-1 text-xs">GET /api/tests/runs/…/artifacts</code> with optional{" "}
            <code className="rounded bg-muted px-1 text-xs">execution_id</code>. Empty = server default (latest).
          </CardDescription>
        </CardHeader>
        <CardContent className="max-w-md space-y-2">
          <Label htmlFor="art-exec">Execution</Label>
          <select
            id="art-exec"
            className="border-input bg-background ring-offset-background focus-visible:ring-ring flex h-9 w-full rounded-md border px-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
            value={executionId}
            onChange={(e) => setExecutionId(e.target.value)}
            disabled={execListQ.isLoading}
          >
            <option value="">Latest (default)</option>
            {executionOptions.map((o) => (
              <option key={o.id} value={o.id}>
                {o.label}
              </option>
            ))}
          </select>
          {execListQ.isError && (
            <p className="text-muted-foreground text-xs">Could not load execution list for dropdown.</p>
          )}
        </CardContent>
      </Card>

      {artifactsQ.isLoading && <Skeleton className="h-40 w-full" />}

      {artifactsQ.isError && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive text-base">Failed to load artifacts</CardTitle>
            <CardDescription>
              {getApiError(artifactsQ.error)?.message ?? (artifactsQ.error as Error).message}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" variant="outline" onClick={() => void artifactsQ.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {artifactsQ.isSuccess && a && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Resolved execution</CardTitle>
              <CardDescription className="font-mono text-xs">
                {String(a.execution_id ?? "—")}
              </CardDescription>
            </CardHeader>
          </Card>

          <ArtifactSection
            title="Screenshots"
            paths={Array.isArray(a.screenshots) ? (a.screenshots as string[]) : []}
          />
          <ArtifactSection
            title="HTML dumps"
            paths={Array.isArray(a.html_dumps) ? (a.html_dumps as string[]) : []}
          />
          {a.summary_path ? (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Summary path</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap items-center gap-2">
                <code className="bg-muted max-w-full flex-1 overflow-auto rounded px-2 py-1 text-xs break-all">
                  {String(a.summary_path)}
                </code>
                <Button type="button" size="sm" variant="outline" onClick={() => copyText(String(a.summary_path))}>
                  Copy
                </Button>
              </CardContent>
            </Card>
          ) : null}

          {a.report && typeof a.report === "object" ? (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Report index</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="bg-muted max-h-72 overflow-auto rounded-md p-3 text-xs">
                  {JSON.stringify(a.report, null, 2)}
                </pre>
                <Button
                  type="button"
                  className="mt-2"
                  size="sm"
                  variant="outline"
                  onClick={() => copyText(JSON.stringify(a.report, null, 2))}
                >
                  Copy JSON
                </Button>
              </CardContent>
            </Card>
          ) : null}
        </div>
      )}
    </div>
  );
}

function ArtifactSection({ title, paths }: { title: string; paths: string[] }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{paths.length} file(s)</CardDescription>
      </CardHeader>
      <CardContent>
        {paths.length === 0 ? (
          <p className="text-muted-foreground text-sm">None</p>
        ) : (
          <ul className="max-h-64 space-y-2 overflow-auto text-sm">
            {paths.map((p) => (
              <li key={p} className="flex flex-wrap items-start gap-2 border-b border-border/60 pb-2 last:border-0">
                <code className="text-muted-foreground grow break-all font-mono text-xs">{p}</code>
                <Button type="button" size="sm" variant="ghost" className="shrink-0" onClick={() => copyText(p)}>
                  Copy
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
