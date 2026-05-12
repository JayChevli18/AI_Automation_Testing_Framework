"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
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
import { Textarea } from "@/components/ui/textarea";
import { dashboardKeys } from "@/features/dashboard/query-keys";
import { executionsKeys } from "@/features/executions/query-keys";
import { interpretedKeys } from "@/features/interpreted/query-keys";
import { cancelRun } from "@/features/runs/api/cancel-run";
import { runsKeys } from "@/features/runs/query-keys";
import { cn } from "@/lib/utils";
import { getApiError } from "@/shared/api/client";

import { cleanupRuns } from "../api/cleanup";

export function OperationsView() {
  const queryClient = useQueryClient();

  const [cancelRunId, setCancelRunId] = useState("");
  const [cancelReason, setCancelReason] = useState("");
  const [cancelError, setCancelError] = useState<string | null>(null);
  const [cancelOk, setCancelOk] = useState<string | null>(null);

  const cancelMut = useMutation({
    mutationFn: () => cancelRun(cancelRunId.trim(), cancelReason.trim() || null),
    onSuccess: async (data) => {
      setCancelError(null);
      setCancelOk(`Cancellation requested. Status: ${data.status}`);
      await queryClient.invalidateQueries({ queryKey: runsKeys.root });
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.root });
      await queryClient.invalidateQueries({ queryKey: executionsKeys.root });
      await queryClient.invalidateQueries({ queryKey: interpretedKeys.root });
    },
    onError: (e) => {
      setCancelOk(null);
      setCancelError(getApiError(e)?.message ?? (e as Error).message);
    },
  });

  const [retainDays, setRetainDays] = useState(14);
  const [dryRun, setDryRun] = useState(true);
  const [maxDelete, setMaxDelete] = useState(200);
  const [cleanupError, setCleanupError] = useState<string | null>(null);
  const [cleanupResult, setCleanupResult] = useState<{
    message: string;
    deleted_run_ids: string[];
    scanned: number;
  } | null>(null);

  const cleanupMut = useMutation({
    mutationFn: () =>
      cleanupRuns({
        retain_days: retainDays,
        dry_run: dryRun,
        max_delete: maxDelete,
      }),
    onSuccess: async (data) => {
      setCleanupError(null);
      setCleanupResult({
        message: data.message,
        deleted_run_ids: data.deleted_run_ids,
        scanned: data.scanned,
      });
      await queryClient.invalidateQueries({ queryKey: runsKeys.root });
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.root });
      await queryClient.invalidateQueries({ queryKey: executionsKeys.root });
      await queryClient.invalidateQueries({ queryKey: interpretedKeys.root });
    },
    onError: (e) => {
      setCleanupResult(null);
      setCleanupError(getApiError(e)?.message ?? (e as Error).message);
    },
  });

  const submitCancel = () => {
    setCancelOk(null);
    setCancelError(null);
    const id = cancelRunId.trim();
    if (!id) {
      setCancelError("Enter a run id.");
      return;
    }
    if (!window.confirm(`Request cooperative cancellation for run ${id}?`)) return;
    cancelMut.mutate();
  };

  const submitCleanup = () => {
    setCleanupError(null);
    setCleanupResult(null);
    if (!dryRun) {
      if (
        !window.confirm(
          "Dry run is OFF. This will permanently delete old run folders from disk. Continue?",
        )
      ) {
        return;
      }
      if (
        !window.confirm(
          "Second confirmation: deleted runs cannot be recovered. Proceed with destructive cleanup?",
        )
      ) {
        return;
      }
    }
    cleanupMut.mutate();
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Operations</h1>
        <p className="text-muted-foreground text-sm">
          Cooperative cancel and retention cleanup. Run ids are listed on{" "}
          <Link href="/runs" className="text-primary underline-offset-4 hover:underline">
            Runs
          </Link>
          .
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Cancel run</CardTitle>
          <CardDescription>
            <code className="rounded bg-muted px-1 text-xs">{`POST /api/tests/runs/{run_id}/cancel`}</code> — best effort
            while the run is queued, interpreted, or running.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 max-w-xl">
          <div className="grid gap-2">
            <Label htmlFor="op-cancel-run">Run id</Label>
            <Input
              id="op-cancel-run"
              className="font-mono text-sm"
              value={cancelRunId}
              onChange={(e) => setCancelRunId(e.target.value)}
              placeholder="run_20260512_114749_0107"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="op-cancel-reason">Reason (optional)</Label>
            <Textarea
              id="op-cancel-reason"
              rows={2}
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Operator note…"
            />
          </div>
          {cancelError && <p className="text-destructive text-sm">{cancelError}</p>}
          {cancelOk && <p className="text-sm text-emerald-700 dark:text-emerald-400">{cancelOk}</p>}
          <Button type="button" disabled={cancelMut.isPending} onClick={submitCancel}>
            {cancelMut.isPending ? "Sending…" : "Request cancel"}
          </Button>
        </CardContent>
      </Card>

      <Card className={cn(!dryRun && "border-destructive/60")}>
        <CardHeader>
          <CardTitle>Retention cleanup</CardTitle>
          <CardDescription>
            <code className="rounded bg-muted px-1 text-xs">POST /api/tests/runs/cleanup</code> — deletes run folders
            older than <strong>retain_days</strong> that are not running or queued. Default is <strong>dry run</strong>{" "}
            (preview only).
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 max-w-xl">
          <div className="grid gap-2">
            <Label htmlFor="op-retain">Retain days</Label>
            <Input
              id="op-retain"
              type="number"
              min={1}
              max={3650}
              value={retainDays}
              onChange={(e) => setRetainDays(Math.max(1, Number(e.target.value) || 14))}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="op-max-del">Max delete (per request)</Label>
            <Input
              id="op-max-del"
              type="number"
              min={1}
              max={5000}
              value={maxDelete}
              onChange={(e) => setMaxDelete(Math.max(1, Number(e.target.value) || 200))}
            />
          </div>
          <div className="flex items-start gap-2 rounded-md border border-amber-500/40 bg-amber-500/5 p-3">
            <Checkbox
              id="op-dry"
              checked={dryRun}
              onCheckedChange={(v) => setDryRun(Boolean(v))}
            />
            <div>
              <Label htmlFor="op-dry" className="font-medium">
                Dry run (recommended)
              </Label>
              <p className="text-muted-foreground mt-1 text-sm">
                When checked, the API only reports which runs would be deleted. Uncheck only after reviewing the
                candidate list.
              </p>
            </div>
          </div>
          {!dryRun && (
            <p className="text-destructive text-sm font-medium">
              Destructive mode: folders will be removed from storage. You will be asked to confirm twice.
            </p>
          )}
          {cleanupError && <p className="text-destructive text-sm">{cleanupError}</p>}
          {cleanupResult && (
            <div className="bg-muted rounded-md p-3 text-sm">
              <p className="font-medium">{cleanupResult.message}</p>
              <p className="text-muted-foreground mt-2">Scanned: {cleanupResult.scanned} runs</p>
              <p className="text-muted-foreground mt-1">
                {cleanupResult.deleted_run_ids.length === 0
                  ? "No run ids in this response."
                  : `${cleanupResult.deleted_run_ids.length} run id(s):`}
              </p>
              {cleanupResult.deleted_run_ids.length > 0 && (
                <ul className="mt-2 max-h-40 list-inside list-disc overflow-auto font-mono text-xs">
                  {cleanupResult.deleted_run_ids.map((id) => (
                    <li key={id}>{id}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          <Button
            type="button"
            variant={dryRun ? "secondary" : "destructive"}
            disabled={cleanupMut.isPending}
            onClick={submitCleanup}
          >
            {cleanupMut.isPending ? "Running cleanup…" : dryRun ? "Preview cleanup (dry run)" : "Run destructive cleanup"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
