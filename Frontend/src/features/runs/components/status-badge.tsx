import { cn } from "@/lib/utils";

const tone: Record<string, string> = {
  queued: "bg-secondary text-secondary-foreground",
  interpreted: "bg-blue-600/15 text-blue-700 dark:text-blue-300",
  running: "bg-amber-500/15 text-amber-800 dark:text-amber-200",
  completed: "bg-emerald-600/15 text-emerald-800 dark:text-emerald-200",
  failed: "bg-destructive/15 text-destructive",
  cancelled: "bg-muted text-muted-foreground",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border border-transparent px-2 py-0.5 text-xs font-medium capitalize",
        tone[status] ?? "bg-muted text-muted-foreground",
      )}
    >
      {status}
    </span>
  );
}
