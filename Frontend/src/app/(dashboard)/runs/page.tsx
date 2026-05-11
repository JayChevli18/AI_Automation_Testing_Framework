import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function RunsListPage() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="text-muted-foreground text-sm">
            Paginated listing will call <code className="rounded bg-muted px-1 text-xs">POST /api/tests/runs/list</code>{" "}
            in the next step.
          </p>
        </div>
        <Link href="/runs/new" className={cn(buttonVariants())}>
          New run
        </Link>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Coming next</CardTitle>
          <CardDescription>Table, filters, and search wired to the list API.</CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    </div>
  );
}
