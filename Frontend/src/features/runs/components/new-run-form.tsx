"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useId, useRef, useState } from "react";

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
import { getApiError } from "@/shared/api/client";

import { dashboardKeys } from "@/features/dashboard/query-keys";

import { startFullRun } from "../api/start-full-run";
import { startInterpret } from "../api/start-interpret";
import { uploadTestFile } from "../api/upload";
import { runsKeys } from "../query-keys";
import type { RunPipelineBody } from "../types";

function parseMaxCases(raw: string): number | null {
  const t = raw.trim();
  if (!t) return null;
  const n = parseInt(t, 10);
  if (!Number.isFinite(n) || n < 1) return null;
  return n;
}

function toBody(
  fileId: string,
  opts: {
    environment: "beta" | "live";
    headless: boolean;
    continue_on_failure: boolean;
    step_timeout_ms: number;
    max_cases: number | null;
    allow_live_mutations: boolean;
  },
): RunPipelineBody {
  return {
    file_id: fileId,
    environment: opts.environment,
    headless: opts.headless,
    continue_on_failure: opts.continue_on_failure,
    step_timeout_ms: opts.step_timeout_ms,
    max_cases: opts.max_cases,
    allow_live_mutations: opts.allow_live_mutations,
  };
}

export function NewRunForm() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const id = useId();

  const [file, setFile] = useState<File | null>(null);
  const [fileId, setFileId] = useState<string | null>(null);
  const [environment, setEnvironment] = useState<"beta" | "live">("beta");
  const [headless, setHeadless] = useState(true);
  const [continueOnFailure, setContinueOnFailure] = useState(true);
  const [stepTimeoutMs, setStepTimeoutMs] = useState(30_000);
  const [maxCasesRaw, setMaxCasesRaw] = useState("");
  const [allowLiveMutations, setAllowLiveMutations] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const uploadMut = useMutation({
    mutationFn: (f: File) => uploadTestFile(f),
    onSuccess: (res) => {
      setFileId(res.file_id);
      setFormError(null);
    },
    onError: (e) => {
      setFormError(getApiError(e)?.message ?? (e as Error).message);
    },
  });

  const interpretMut = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose an Excel file first.");
      const fid = fileId ?? (await uploadTestFile(file)).file_id;
      setFileId(fid);
      if (environment === "live" && !allowLiveMutations) {
        throw new Error('Live environment requires "Allow mutating actions on live".');
      }
      return startInterpret(
        toBody(fid, {
          environment,
          headless,
          continue_on_failure: continueOnFailure,
          step_timeout_ms: stepTimeoutMs,
          max_cases: parseMaxCases(maxCasesRaw),
          allow_live_mutations: allowLiveMutations,
        }),
      );
    },
    onSuccess: async (res) => {
      await queryClient.invalidateQueries({ queryKey: runsKeys.root });
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.root });
      router.push(`/runs/${encodeURIComponent(res.run_id)}`);
    },
    onError: (e) => {
      setFormError(getApiError(e)?.message ?? (e as Error).message);
    },
  });

  const fullRunMut = useMutation({
    mutationFn: async () => {
      if (!file) throw new Error("Choose an Excel file first.");
      const fid = fileId ?? (await uploadTestFile(file)).file_id;
      setFileId(fid);
      if (environment === "live" && !allowLiveMutations) {
        throw new Error('Live environment requires "Allow mutating actions on live".');
      }
      return startFullRun(
        toBody(fid, {
          environment,
          headless,
          continue_on_failure: continueOnFailure,
          step_timeout_ms: stepTimeoutMs,
          max_cases: parseMaxCases(maxCasesRaw),
          allow_live_mutations: allowLiveMutations,
        }),
      );
    },
    onSuccess: async (res) => {
      await queryClient.invalidateQueries({ queryKey: runsKeys.root });
      await queryClient.invalidateQueries({ queryKey: dashboardKeys.root });
      router.push(`/runs/${encodeURIComponent(res.run_id)}`);
    },
    onError: (e) => {
      setFormError(getApiError(e)?.message ?? (e as Error).message);
    },
  });

  const busy = uploadMut.isPending || interpretMut.isPending || fullRunMut.isPending;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New run</h1>
        <p className="text-muted-foreground text-sm">
          Upload an <code className="rounded bg-muted px-1 text-xs">.xlsx</code> or{" "}
          <code className="rounded bg-muted px-1 text-xs">.xls</code> file, then interpret only or run the full pipeline.
        </p>
      </div>

      {formError && (
        <Card className="border-destructive/50">
          <CardHeader className="py-3">
            <CardTitle className="text-destructive text-base">Error</CardTitle>
            <CardDescription className="text-destructive/90">{formError}</CardDescription>
          </CardHeader>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>1. File</CardTitle>
          <CardDescription>Upload is required before interpret or full run.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            disabled={busy}
            onChange={(e) => {
              const f = e.target.files?.[0];
              setFile(f ?? null);
              setFileId(null);
              setFormError(null);
            }}
          />
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="secondary"
              disabled={!file || busy}
              onClick={() => file && uploadMut.mutate(file)}
            >
              {uploadMut.isPending ? "Uploading…" : "Upload only"}
            </Button>
            {fileId && (
              <p className="text-muted-foreground self-center text-sm font-mono">file_id: {fileId}</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2. Options</CardTitle>
          <CardDescription>Same payload shape as the FastAPI <code className="rounded bg-muted px-1 text-xs">RunRequest</code>.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor={`${id}-env`}>Environment</Label>
            <select
              id={`${id}-env`}
              className="border-input bg-background ring-offset-background focus-visible:ring-ring flex h-8 rounded-md border px-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
              value={environment}
              disabled={busy}
              onChange={(e) => setEnvironment(e.target.value as "beta" | "live")}
            >
              <option value="beta">beta</option>
              <option value="live">live</option>
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${id}-timeout`}>Step timeout (ms)</Label>
            <Input
              id={`${id}-timeout`}
              type="number"
              min={1000}
              disabled={busy}
              value={stepTimeoutMs}
              onChange={(e) => setStepTimeoutMs(Number(e.target.value) || 30_000)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor={`${id}-max`}>Max cases (optional)</Label>
            <Input
              id={`${id}-max`}
              type="number"
              min={1}
              placeholder="All cases"
              disabled={busy}
              value={maxCasesRaw}
              onChange={(e) => setMaxCasesRaw(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-3 sm:col-span-2">
            <div className="flex items-center gap-2">
              <Checkbox
                id={`${id}-headless`}
                checked={headless}
                disabled={busy}
                onCheckedChange={(v) => setHeadless(Boolean(v))}
              />
              <Label htmlFor={`${id}-headless`} className="font-normal">
                Headless browser
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id={`${id}-cof`}
                checked={continueOnFailure}
                disabled={busy}
                onCheckedChange={(v) => setContinueOnFailure(Boolean(v))}
              />
              <Label htmlFor={`${id}-cof`} className="font-normal">
                Continue on failure
              </Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                id={`${id}-live`}
                checked={allowLiveMutations}
                disabled={busy || environment !== "live"}
                onCheckedChange={(v) => setAllowLiveMutations(Boolean(v))}
              />
              <Label htmlFor={`${id}-live`} className="font-normal">
                Allow mutating actions on live (required for <code className="text-xs">environment=live</code>)
              </Label>
            </div>
          </div>
          {environment === "live" && !allowLiveMutations && (
            <p className="text-destructive text-sm sm:col-span-2">
              The API returns 403 for live runs unless mutating actions are explicitly allowed.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>3. Start</CardTitle>
          <CardDescription>
            Interpret calls <code className="rounded bg-muted px-1 text-xs">POST /interpret</code>. Full run calls{" "}
            <code className="rounded bg-muted px-1 text-xs">POST /run</code> and can take a long time.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={!file || busy}
            onClick={() => interpretMut.mutate()}
          >
            {interpretMut.isPending ? "Interpreting…" : "Interpret only"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={!file || busy}
            onClick={() => fullRunMut.mutate()}
          >
            {fullRunMut.isPending ? "Running…" : "Full pipeline (interpret + execute)"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
