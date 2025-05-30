import { useRouter } from "@tanstack/react-router";
import { usePermissionGuard } from "@/hooks/usePermissions";

interface PermissionGuardProps {
  required: Array<"Admin" | "User" | "Viewer">;
  children: React.ReactNode;
}

export function PermissionGuard({ required, children }: PermissionGuardProps) {
  const router = useRouter();
  const { currentPermission, isLoading, error } = usePermissionGuard();

  // Show loading state while checking permissions
  if (isLoading) {
    return <div>Loading permissions...</div>;
  }

  // If there's an error or no permission, redirect to unauthorized
  if (error || !currentPermission || !required.includes(currentPermission as any)) {
    router.navigate({ to: "/unauthorised" });
    return null;
  }

  return <>{children}</>;
}