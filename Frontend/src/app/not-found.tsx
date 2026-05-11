import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export default function NotFound() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-4 px-4">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <Link href="/" className={cn(buttonVariants())}>
        Back to dashboard
      </Link>
    </div>
  );
}
