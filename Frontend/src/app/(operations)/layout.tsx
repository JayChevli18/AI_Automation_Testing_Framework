import { MainShell } from "@/components/layout/main-shell";

export default function OperationsGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <MainShell>{children}</MainShell>;
}
