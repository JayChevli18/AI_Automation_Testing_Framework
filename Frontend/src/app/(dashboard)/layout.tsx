import { MainShell } from "@/components/layout/main-shell";

export default function DashboardGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <MainShell>{children}</MainShell>;
}
