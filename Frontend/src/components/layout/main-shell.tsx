import Link from "next/link";

import { Separator } from "@/components/ui/separator";

const nav = [
  { href: "/", label: "Dashboard" },
  { href: "/runs", label: "Runs" },
  { href: "/runs/new", label: "New run" },
  { href: "/operations", label: "Operations" },
  { href: "/settings", label: "Settings" },
] as const;

export function MainShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-2 px-4 py-3">
          <Link href="/" className="font-semibold tracking-tight text-foreground">
            Test automation
          </Link>
          <Separator orientation="vertical" className="mx-1 h-6 shrink-0" />
          <nav className="flex flex-wrap items-center gap-1">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className="rounded-md px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">{children}</main>
    </div>
  );
}
