import { useEffect } from "react";
import { useRouter } from "@tanstack/react-router";
import { usePermissionGuard } from "@/hooks/usePermissions";

interface PermissionGuardProps {
  required: Array<"Admin" | "User" | "Viewer">;
  children: React.ReactNode;
}

export function PermissionGuard({ required, children }: PermissionGuardProps) {
  const router = useRouter();
  const { currentPermission, isLoading, error } = usePermissionGuard();

  // Handle navigation in useEffect to avoid setState during render
  useEffect(() => {
    if (!isLoading && (error || !currentPermission || !required.includes(currentPermission as any))) {
      router.navigate({ to: "/unauthorised" });
    }
  }, [isLoading, error, currentPermission, required, router]);

  // Show loading state while checking permissions
  if (isLoading) {
    return <div>Loading permissions...</div>;
  }

  // If there's an error or no permission, show nothing while navigating
  if (error || !currentPermission || !required.includes(currentPermission as any)) {
    return null;
  }

  return <>{children}</>;
}