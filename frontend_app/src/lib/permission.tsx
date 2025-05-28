import { useRouter } from "@tanstack/react-router";

interface PermissionGuardProps {
  required: Array<"Admin" | "User" | "Viewer">;
  children: React.ReactNode;
}

export function PermissionGuard({ required, children }: PermissionGuardProps) {
  const router = useRouter();
  const permission = localStorage.getItem("permission");

  if (!permission || !required.includes(permission as any)) {
    router.navigate({ to: "/unauthorised" });
    return null;
  }

  return <>{children}</>;
}