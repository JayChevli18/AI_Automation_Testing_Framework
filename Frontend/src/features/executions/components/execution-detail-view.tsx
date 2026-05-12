"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { getApiError } from "@/shared/api/client";

import { fetchArtifacts } from "../api/artifacts";
import { fetchVersionedExecutionReports } from "../api/execution-reports";
import { fetchVersionedExecutionSummary } from "../api/execution-summary";
import { executionsKeys } from "../query-keys";

type TabId = "summary" | "reports" | "artifacts";

export function ExecutionDetailView({
  runId,
  executionId,
}: {
  runId: string;
  executionId: string;
}) {
  const [tab, setTab] = useState<TabId>("summary");

  const summaryQ = useQuery({
    queryKey: executionsKeys.summary(runId, executionId),
    queryFn: () => fetchVersionedExecutionSummary(runId, executionId),
  });

  const reportsQ = useQuery({
    queryKey: executionsKeys.reports(runId, executionId),
    queryFn: () => fetchVersionedExecutionReports(runId, executionId),
  });

  const artifactsQ = useQuery({
    queryKey: executionsKeys.artifacts(runId, executionId),
    queryFn: () => fetchArtifacts(runId, executionId),
  });

  const reportHtmlHref = `/api/tests/versioned/${encodeURIComponent(runId)}/executions/${encodeURIComponent(executionId)}/report.html`;
  const legacyReportsHref = `/api/tests/reports/${encodeURIComponent(runId)}?execution_id=${encodeURIComponent(executionId)}`;

  const tabBtn = (id: TabId, label: string) => (
    <button
      type="button"
      key={id}
      onClick={() => setTab(id)}
      className={cn(
        "border-b-2 px-3 py-2 text-sm font-medium transition-colors",
        tab === id
          ? "border-primary text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Execution</h1>
          <p className="text-muted-foreground font-mono text-sm">
            {runId} / {executionId}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href={`/runs/${encodeURIComponent(runId)}/executions`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            All executions
          </Link>
          <Link
            href={`/runs/${encodeURIComponent(runId)}`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Run detail
          </Link>
          <Link
            href={`/runs/${encodeURIComponent(runId)}/artifacts`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Artifact explorer
          </Link>
        </div>
      </div>

      <div className="flex gap-1 border-b">
        {tabBtn("summary", "Summary")}
        {tabBtn("reports", "Reports")}
        {tabBtn("artifacts", "Artifacts")}
      </div>

      {tab === "summary" && (
        <div className="space-y-4">
          {summaryQ.isLoading && <Skeleton className="h-48 w-full" />}
          {summaryQ.isError && (
            <Card className="border-destructive/50">
              <CardHeader>
                <CardTitle className="text-destructive text-base">Summary failed</CardTitle>
                <CardDescription>
                  {getApiError(summaryQ.error)?.message ?? (summaryQ.error as Error).message}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button type="button" variant="outline" onClick={() => void summaryQ.refetch()}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          )}
          {summaryQ.isSuccess && (
            <>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Overview</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-2 text-sm sm:grid-cols-2 md:grid-cols-4">
                  {(["status", "total_cases", "passed_cases", "failed_cases", "skipped_cases", "running_cases", "pending_cases"] as const).map(
                    (key) => (
                      <div key={key}>
                        <p className="text-muted-foreground capitalize">{key.replace(/_/g, " ")}</p>
                        <p className="font-medium">
                          {summaryQ.data[key] === undefined || summaryQ.data[key] === null
                            ? "—"
                            : String(summaryQ.data[key])}
                        </p>
                      </div>
                    ),
                  )}
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-base">Raw summary JSON</CardTitle>
                  <CardDescription>
                    From <code className="rounded bg-muted px-1 text-xs">…/executions/…/summary</code>
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <pre className="bg-muted max-h-[480px] overflow-auto rounded-md p-3 text-xs">
                    {JSON.stringify(summaryQ.data, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}

      {tab === "reports" && (
        <div className="space-y-4">
          {reportsQ.isLoading && <Skeleton className="h-32 w-full" />}
          {reportsQ.isError && (
            <Card className="border-destructive/50">
              <CardHeader>
                <CardTitle className="text-destructive text-base">Reports index failed</CardTitle>
                <CardDescription>
                  {getApiError(reportsQ.error)?.message ?? (reportsQ.error as Error).message}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button type="button" variant="outline" onClick={() => void reportsQ.refetch()}>
                  Retry
                </Button>
              </CardContent>
            </Card>
          )}
          {reportsQ.isSuccess && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Report artifacts</CardTitle>
                <CardDescription>Versioned Allure results and HTML dashboard paths.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <div>
                  <p className="text-muted-foreground mb-1">HTML report</p>
                  <p className="font-mono text-xs break-all">{reportsQ.data.html_report_path}</p>
                  <a
                    href={reportHtmlHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={cn(buttonVariants({ size: "sm" }), "mt-2 inline-flex")}
                  >
                    Open report.html
                  </a>
                </div>
                <Separator />
                <div>
                  <p className="text-muted-foreground mb-1">Allure results directory</p>
                  <p className="font-mono text-xs break-all">{reportsQ.data.allure_results_dir}</p>
                  <p className="text-muted-foreground mt-2">
                    {reportsQ.data.allure_result_files.length} result file(s)
                  </p>
                </div>
                <Separator />
                <div>
                  <p className="text-muted-foreground mb-1">Legacy run-level report index</p>
                  <a
                    href={legacyReportsHref}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary text-sm underline-offset-4 hover:underline"
                  >
                    GET /api/tests/reports/{runId}?execution_id=…
                  </a>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {tab === "artifacts" && (
        <div className="space-y-4">
          {artifactsQ.isLoading && <Skeleton className="h-32 w-full" />}
          {artifactsQ.isError && (
            <Card className="border-destructive/50">
              <CardHeader>
                <CardTitle className="text-destructive text-base">Artifacts failed</CardTitle>
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
          {artifactsQ.isSuccess && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Artifact index</CardTitle>
                <CardDescription>
                  From <code className="rounded bg-muted px-1 text-xs">GET …/runs/…/artifacts?execution_id=</code>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <ArtifactList label="Screenshots" items={artifactsQ.data.screenshots} />
                <ArtifactList label="HTML dumps" items={artifactsQ.data.html_dumps} />
                {artifactsQ.data.summary_path ? (
                  <div>
                    <p className="text-muted-foreground mb-1">Summary path</p>
                    <p className="font-mono text-xs break-all">{String(artifactsQ.data.summary_path)}</p>
                  </div>
                ) : null}
                {artifactsQ.data.report && typeof artifactsQ.data.report === "object" ? (
                  <div>
                    <p className="text-muted-foreground mb-1">Nested report index</p>
                    <pre className="bg-muted max-h-64 overflow-auto rounded-md p-3 text-xs">
                      {JSON.stringify(artifactsQ.data.report, null, 2)}
                    </pre>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function ArtifactList({ label, items }: { label: string; items: unknown }) {
  const list = Array.isArray(items) ? items : [];
  return (
    <div>
      <p className="text-muted-foreground mb-1">{label}</p>
      {list.length === 0 ? (
        <p className="text-muted-foreground">None</p>
      ) : (
        <ul className="max-h-48 list-inside list-disc overflow-auto font-mono text-xs">
          {list.map((p, i) => (
            <li key={i} className="break-all">
              {String(p)}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
