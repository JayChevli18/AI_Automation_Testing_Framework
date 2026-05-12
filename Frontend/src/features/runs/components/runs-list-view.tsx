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
import { cn } from "@/lib/utils";
import { getApiError } from "@/shared/api/client";

import { listRuns } from "../api/list-runs";
import { useDebounced } from "../hooks/use-debounced";
import { formatDateTime } from "../lib/format";
import { runsKeys } from "../query-keys";
import type { RunListFilter, RunListRequestBody, RunListSortBy, RunListSortOrder } from "../types";

import { StatusBadge } from "./status-badge";

const STATUS_VALUES = ["queued", "interpreted", "running", "completed", "failed", "cancelled"] as const;

const SORT_FIELDS: { value: RunListSortBy; label: string }[] = [
  { value: "created_at", label: "Created" },
  { value: "updated_at", label: "Updated" },
  { value: "run_id", label: "Run ID" },
  { value: "file_id", label: "File ID" },
  { value: "status", label: "Status" },
  { value: "environment", label: "Environment" },
];

const selectCls =
  "border-input bg-background ring-offset-background focus-visible:ring-ring flex h-8 rounded-md border px-2 text-sm focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none";

type AdvRow = {
  id: string;
  field: RunListSortBy;
  operator: RunListFilter["operator"];
  value: string;
};

const FILTER_OPS: RunListFilter["operator"][] = ["equals", "contains", "gte", "lte"];

export function RunsListView() {
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(25);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 350);
  const [sortBy, setSortBy] = useState<RunListSortBy>("created_at");
  const [sortOrder, setSortOrder] = useState<RunListSortOrder>("desc");
  const [status, setStatus] = useState<string>("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [advRows, setAdvRows] = useState<AdvRow[]>([]);

  const listBody: RunListRequestBody = useMemo(() => {
    const statusFilters: RunListFilter[] =
      status === "" ? [] : [{ field: "status", operator: "equals", value: status }];
    const extraFilters: RunListFilter[] = advRows
      .filter((r) => r.value.trim() !== "")
      .map((r) => ({
        field: r.field,
        operator: r.operator,
        value: r.value.trim(),
      }));
    const filters = [...statusFilters, ...extraFilters];
    return {
      page,
      limit,
      search: debouncedSearch.trim() === "" ? null : debouncedSearch.trim(),
      sortingOptions: { sortBy, sortOrder },
      filters,
    };
  }, [page, limit, debouncedSearch, sortBy, sortOrder, status, advRows]);

  const q = useQuery({
    queryKey: runsKeys.list(listBody),
    queryFn: () => listRuns(listBody),
  });

  const apiErr = q.error ? getApiError(q.error) : null;
  const meta = q.data?.meta;
  const rows = q.data?.list ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="text-muted-foreground text-sm">
            Paginated list from <code className="rounded bg-muted px-1 text-xs">POST /api/tests/runs/list</code>.
          </p>
        </div>
        <Link href="/runs/new" className={cn(buttonVariants())}>
          New run
        </Link>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Filters</CardTitle>
          <CardDescription>Search applies to run metadata fields on the server.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-4">
          <div className="grid gap-2 min-w-[200px] flex-1">
            <Label htmlFor="run-search">Search</Label>
            <Input
              id="run-search"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="run id, file id, status…"
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="run-status">Status</Label>
            <select
              id="run-status"
              className={cn(selectCls, "w-44")}
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">Any</option>
              {STATUS_VALUES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="run-sort">Sort by</Label>
            <select
              id="run-sort"
              className={cn(selectCls, "w-40")}
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value as RunListSortBy);
                setPage(1);
              }}
            >
              {SORT_FIELDS.map((f) => (
                <option key={f.value} value={f.value}>
                  {f.label}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="run-order">Order</Label>
            <select
              id="run-order"
              className={cn(selectCls, "w-32")}
              value={sortOrder}
              onChange={(e) => {
                setSortOrder(e.target.value as RunListSortOrder);
                setPage(1);
              }}
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </div>
          <div className="grid gap-2">
            <Label htmlFor="run-limit">Page size</Label>
            <select
              id="run-limit"
              className={cn(selectCls, "w-24")}
              value={String(limit)}
              onChange={(e) => {
                setLimit(Number(e.target.value));
                setPage(1);
              }}
            >
              {[10, 25, 50, 100].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <CardTitle className="text-base">Advanced filters</CardTitle>
              <CardDescription>
                Extra <code className="rounded bg-muted px-1 text-xs">filters[]</code> entries (AND with quick status
                above). Use ISO-like strings for date <code className="rounded bg-muted px-1 text-xs">gte</code> /{" "}
                <code className="rounded bg-muted px-1 text-xs">lte</code>.
              </CardDescription>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setAdvancedOpen((o) => !o)}
            >
              {advancedOpen ? "Hide" : "Show"}
            </Button>
          </div>
        </CardHeader>
        {advancedOpen && (
          <CardContent className="space-y-3">
            {advRows.map((row) => (
              <div
                key={row.id}
                className="flex flex-wrap items-end gap-2 border-b border-border/60 pb-3 last:border-0 last:pb-0"
              >
                <div className="grid gap-1">
                  <Label className="text-xs">Field</Label>
                  <select
                    className={cn(selectCls, "min-w-[140px]")}
                    value={row.field}
                    onChange={(e) => {
                      const field = e.target.value as RunListSortBy;
                      setAdvRows((rows) =>
                        rows.map((r) => (r.id === row.id ? { ...r, field } : r)),
                      );
                      setPage(1);
                    }}
                  >
                    {SORT_FIELDS.map((f) => (
                      <option key={f.value} value={f.value}>
                        {f.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid gap-1">
                  <Label className="text-xs">Operator</Label>
                  <select
                    className={cn(selectCls, "w-32")}
                    value={row.operator}
                    onChange={(e) => {
                      const operator = e.target.value as RunListFilter["operator"];
                      setAdvRows((rows) =>
                        rows.map((r) => (r.id === row.id ? { ...r, operator } : r)),
                      );
                      setPage(1);
                    }}
                  >
                    {FILTER_OPS.map((op) => (
                      <option key={op} value={op}>
                        {op}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="grid min-w-[160px] flex-1 gap-1">
                  <Label className="text-xs">Value</Label>
                  <Input
                    value={row.value}
                    onChange={(e) => {
                      const value = e.target.value;
                      setAdvRows((rows) =>
                        rows.map((r) => (r.id === row.id ? { ...r, value } : r)),
                      );
                      setPage(1);
                    }}
                    placeholder="e.g. beta, run_…, 2026-05-01T00:00:00"
                  />
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="text-destructive"
                  onClick={() => {
                    setAdvRows((rows) => rows.filter((r) => r.id !== row.id));
                    setPage(1);
                  }}
                >
                  Remove
                </Button>
              </div>
            ))}
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={advRows.length >= 10}
                onClick={() => {
                  setAdvRows((rows) => [
                    ...rows,
                    {
                      id: crypto.randomUUID(),
                      field: "run_id",
                      operator: "contains",
                      value: "",
                    },
                  ]);
                  setPage(1);
                }}
              >
                Add filter row
              </Button>
              {advRows.length > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setAdvRows([]);
                    setPage(1);
                  }}
                >
                  Clear all
                </Button>
              )}
            </div>
          </CardContent>
        )}
      </Card>

      {q.isError && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Could not load runs</CardTitle>
            <CardDescription>
              {apiErr?.message ?? (q.error as Error)?.message}
              {apiErr?.requestId ? (
                <span className="mt-2 block font-mono text-xs">request_id: {apiErr.requestId}</span>
              ) : null}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button type="button" variant="outline" onClick={() => q.refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {q.isFetching && !q.isLoading && (
        <p className="text-muted-foreground text-sm">Refreshing…</p>
      )}

      {q.isSuccess && (
        <>
          <div className="overflow-hidden rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run</TableHead>
                  <TableHead>File</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Env</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-muted-foreground h-24 text-center">
                      No runs match these filters.
                    </TableCell>
                  </TableRow>
                ) : (
                  rows.map((r) => (
                    <TableRow key={r.run_id}>
                      <TableCell className="font-mono text-xs">
                        <Link
                          href={`/runs/${encodeURIComponent(r.run_id)}`}
                          className="text-primary hover:underline"
                        >
                          {r.run_id}
                        </Link>
                      </TableCell>
                      <TableCell className="font-mono text-xs">{r.file_id}</TableCell>
                      <TableCell>
                        <StatusBadge status={r.status} />
                      </TableCell>
                      <TableCell className="capitalize">{r.environment}</TableCell>
                      <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                        {formatDateTime(r.created_at)}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm whitespace-nowrap">
                        {formatDateTime(r.updated_at)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {meta && (
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-muted-foreground text-sm">
                Page {meta.currentPage} of {Math.max(meta.totalPages, 1)} · {meta.totalItems} runs
              </p>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!meta.hasPreviousPage}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={!meta.hasNextPage}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
