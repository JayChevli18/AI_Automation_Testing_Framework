import { MainShell } from "@/components/layout/main-shell";

export default function SettingsGroupLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <MainShell>{children}</MainShell>;
}
