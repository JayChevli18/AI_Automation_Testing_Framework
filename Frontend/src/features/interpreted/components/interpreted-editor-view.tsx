"use client";

import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { runsKeys } from "@/features/runs/query-keys";
import { fetchRunResults } from "@/features/runs/api/run-results";
import { cn } from "@/lib/utils";
import { getApiError } from "@/shared/api/client";

import { patchInterpretedSteps } from "../api/patch";
import { fetchInterpretedSteps } from "../api/read";
import { interpretedKeys } from "../query-keys";
import type {
  InterpretedAction,
  InterpretedCaseRecord,
  InterpretedStep,
  InterpretedStepRecord,
} from "../types";

const ACTIONS: InterpretedAction[] = [
  "goto",
  "hover",
  "click",
  "fill",
  "assert_visible",
  "assert_text",
  "wait",
  "unknown",
];

function defaultInterpreted(): InterpretedStep {
  return {
    action: "unknown",
    target: "",
    value: null,
    value_key: null,
    assertion: null,
    confidence: 0.85,
    missing_value: false,
    notes: null,
  };
}

function stepToDraft(step: InterpretedStepRecord) {
  const i = step.interpreted ?? defaultInterpreted();
  return {
    action: i.action,
    target: i.target ?? "",
    value: i.value ?? "",
    valueKey: i.value_key ?? "",
    assertionJson: i.assertion ? JSON.stringify(i.assertion, null, 2) : "",
    confidence: i.confidence,
    missingValue: i.missing_value,
    notes: i.notes ?? "",
  };
}

type EditTarget = { testCaseId: string; stepIndex: number };

export function InterpretedEditorView({ runId }: { runId: string }) {
  const queryClient = useQueryClient();
  const [edit, setEdit] = useState<EditTarget | null>(null);
  const [draft, setDraft] = useState(() =>
    stepToDraft({
      step_index: 0,
      raw_step: "",
      interpreted: null,
      interpretation_error: null,
    }),
  );
  const [conflictMessage, setConflictMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  const resultsQ = useQuery({
    queryKey: runsKeys.results(runId),
    queryFn: () => fetchRunResults(runId),
  });

  const readQ = useQuery({
    queryKey: interpretedKeys.read(runId),
    queryFn: () => fetchInterpretedSteps(runId),
  });

  const cases: InterpretedCaseRecord[] = useMemo(() => {
    const raw = readQ.data?.interpreted_steps;
    if (!Array.isArray(raw)) return [];
    return raw as InterpretedCaseRecord[];
  }, [readQ.data?.interpreted_steps]);

  const revision = readQ.data?.revision ?? null;

  const beginEdit = useCallback((testCaseId: string, step: InterpretedStepRecord) => {
    setSaveError(null);
    setConflictMessage(null);
    setEdit({ testCaseId, stepIndex: step.step_index });
    setDraft(stepToDraft(step));
  }, []);

  const cancelEdit = useCallback(() => {
    setEdit(null);
    setSaveError(null);
  }, []);

  const patchMut = useMutation({
    mutationFn: async (body: Parameters<typeof patchInterpretedSteps>[1]) => {
      return patchInterpretedSteps(runId, body);
    },
    onSuccess: async () => {
      setConflictMessage(null);
      setSaveError(null);
      setEdit(null);
      await queryClient.invalidateQueries({ queryKey: interpretedKeys.read(runId) });
      await queryClient.invalidateQueries({ queryKey: runsKeys.results(runId) });
    },
    onError: (err: unknown) => {
      const api = getApiError(err);
      const status = axios.isAxiosError(err) ? err.response?.status : 0;
      if (status === 409 || api?.code === "HTTP_409") {
        setConflictMessage(api?.message ?? "Conflict: revision mismatch or run is busy.");
        return;
      }
      setSaveError(api?.message ?? (err as Error).message);
    },
  });

  const saveEdit = useCallback(() => {
    if (!edit) {
      return;
    }
    let assertion: Record<string, unknown> | null = null;
    const trimmed = draft.assertionJson.trim();
    if (trimmed) {
      try {
        assertion = JSON.parse(trimmed) as Record<string, unknown>;
        if (assertion !== null && typeof assertion !== "object") {
          setSaveError("Assertion JSON must be an object.");
          return;
        }
      } catch {
        setSaveError("Assertion JSON is invalid.");
        return;
      }
    }

    const interpreted: Record<string, unknown> = {
      action: draft.action,
      target: draft.target,
      value: draft.value.trim() === "" ? null : draft.value,
      value_key: draft.valueKey.trim() === "" ? null : draft.valueKey,
      assertion,
      confidence: Number(draft.confidence),
      missing_value: draft.missingValue,
      notes: draft.notes.trim() === "" ? null : draft.notes,
    };

    patchMut.mutate({
      patches: [
        {
          test_case_id: edit.testCaseId,
          step_patches: [
            {
              step_index: edit.stepIndex,
              interpreted,
            },
          ],
        },
      ],
      expected_revision: revision ?? null,
    });
  }, [edit, draft, revision, patchMut]);

  const reloadAfterConflict = useCallback(async () => {
    setConflictMessage(null);
    setSaveError(null);
    setEdit(null);
    await queryClient.invalidateQueries({ queryKey: interpretedKeys.read(runId) });
  }, [queryClient, runId]);

  const runBlocked = resultsQ.data?.status === "running";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Interpreted steps</h1>
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

      {runBlocked && (
        <Card className="border-amber-500/50 bg-amber-500/5">
          <CardHeader className="py-3">
            <CardTitle className="text-base">Run is executing</CardTitle>
            <CardDescription>
              Editing is blocked while status is <code className="rounded bg-muted px-1 text-xs">running</code>. Wait for
              completion or cancel from run detail.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {conflictMessage && (
        <Card className="border-destructive/50">
          <CardHeader className="py-3">
            <CardTitle className="text-destructive text-base">Conflict</CardTitle>
            <CardDescription className="text-destructive/90 whitespace-pre-wrap">{conflictMessage}</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-2">
            <Button type="button" onClick={() => void reloadAfterConflict()}>
              Reload server version
            </Button>
            <Button type="button" variant="outline" onClick={() => setConflictMessage(null)}>
              Dismiss
            </Button>
          </CardContent>
        </Card>
      )}

      {readQ.isError && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Could not load interpreted steps</CardTitle>
            <CardDescription>
              {getApiError(readQ.error)?.message ?? (readQ.error as Error).message}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" variant="outline" onClick={() => void readQ.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {readQ.isSuccess && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">Revision</CardTitle>
            <CardDescription>
              Patches send <code className="rounded bg-muted px-1 text-xs">expected_revision</code> for optimistic locking.
              Current: <strong>{revision ?? "—"}</strong>
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      {saveError && (
        <p className="text-destructive text-sm" role="alert">
          {saveError}
        </p>
      )}

      {readQ.isLoading && <p className="text-muted-foreground text-sm">Loading…</p>}

      {readQ.isSuccess &&
        cases.map((tc) => (
          <Card key={tc.test_case_id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-base font-mono">{tc.test_case_id}</CardTitle>
              <CardDescription>
                {tc.test_case_name}
                {tc.module ? ` · ${tc.module}` : ""}
              </CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10">#</TableHead>
                    <TableHead>Raw step</TableHead>
                    <TableHead>Interpreted</TableHead>
                    <TableHead className="w-40">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tc.steps.map((step) => {
                    const isEditing =
                      edit?.testCaseId === tc.test_case_id && edit.stepIndex === step.step_index;
                    return (
                      <TableRow key={`${tc.test_case_id}-${step.step_index}`}>
                        <TableCell className="text-muted-foreground">{step.step_index}</TableCell>
                        <TableCell className="max-w-md text-sm whitespace-pre-wrap">{step.raw_step}</TableCell>
                        <TableCell className="min-w-[280px]">
                          {isEditing ? (
                            <div className="grid gap-2 py-1">
                              <div className="grid gap-1">
                                <Label className="text-xs">Action</Label>
                                <select
                                  className="border-input bg-background h-8 rounded-md border px-2 text-sm"
                                  value={draft.action}
                                  onChange={(e) =>
                                    setDraft((d) => ({ ...d, action: e.target.value as InterpretedAction }))
                                  }
                                >
                                  {ACTIONS.map((a) => (
                                    <option key={a} value={a}>
                                      {a}
                                    </option>
                                  ))}
                                </select>
                              </div>
                              <div className="grid gap-1">
                                <Label className="text-xs">Target</Label>
                                <Input
                                  value={draft.target}
                                  onChange={(e) => setDraft((d) => ({ ...d, target: e.target.value }))}
                                />
                              </div>
                              <div className="grid gap-1">
                                <Label className="text-xs">Value</Label>
                                <Input
                                  value={draft.value}
                                  onChange={(e) => setDraft((d) => ({ ...d, value: e.target.value }))}
                                />
                              </div>
                              <div className="grid gap-1">
                                <Label className="text-xs">Value key</Label>
                                <Input
                                  value={draft.valueKey}
                                  onChange={(e) => setDraft((d) => ({ ...d, valueKey: e.target.value }))}
                                />
                              </div>
                              <div className="grid gap-1">
                                <Label className="text-xs">Assertion (JSON object or empty)</Label>
                                <Textarea
                                  rows={3}
                                  className="font-mono text-xs"
                                  value={draft.assertionJson}
                                  onChange={(e) => setDraft((d) => ({ ...d, assertionJson: e.target.value }))}
                                />
                              </div>
                              <div className="grid gap-1">
                                <Label className="text-xs">Confidence</Label>
                                <Input
                                  type="number"
                                  step={0.01}
                                  min={0}
                                  max={1}
                                  value={draft.confidence}
                                  onChange={(e) =>
                                    setDraft((d) => ({ ...d, confidence: Number(e.target.value) || 0 }))
                                  }
                                />
                              </div>
                              <div className="flex items-center gap-2">
                                <Checkbox
                                  checked={draft.missingValue}
                                  onCheckedChange={(v) => setDraft((d) => ({ ...d, missingValue: Boolean(v) }))}
                                />
                                <Label className="text-xs font-normal">Missing value</Label>
                              </div>
                              <div className="grid gap-1">
                                <Label className="text-xs">Notes</Label>
                                <Input
                                  value={draft.notes}
                                  onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
                                />
                              </div>
                            </div>
                          ) : (
                            <pre className="bg-muted max-h-40 overflow-auto rounded-md p-2 text-xs">
                              {JSON.stringify(step.interpreted ?? null, null, 2)}
                            </pre>
                          )}
                        </TableCell>
                        <TableCell className="align-top">
                          {isEditing ? (
                            <div className="flex flex-col gap-1">
                              <Button
                                type="button"
                                size="sm"
                                disabled={runBlocked || patchMut.isPending}
                                onClick={() => saveEdit()}
                              >
                                {patchMut.isPending ? "Saving…" : "Save"}
                              </Button>
                              <Button type="button" size="sm" variant="outline" onClick={cancelEdit}>
                                Cancel
                              </Button>
                            </div>
                          ) : (
                            <Button
                              type="button"
                              size="sm"
                              variant="secondary"
                              disabled={runBlocked || edit !== null}
                              onClick={() => beginEdit(tc.test_case_id, step)}
                            >
                              Edit
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        ))}
    </div>
  );
}
