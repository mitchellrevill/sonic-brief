import { useEffect } from "react";
import { useRouter } from "@tanstack/react-router";
import { useCapabilityGuard } from "@/hooks/usePermissions";
import { Capability, PermissionLevel, hasPermissionLevel } from "@/types/permissions";

interface PermissionGuardProps {
  requiredPermission?: PermissionLevel;
  requiredCapability?: Capability;
  requiredCapabilities?: Capability[];
  requireAllCapabilities?: boolean; // If true, user must have ALL capabilities, otherwise ANY
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function PermissionGuard({ 
  requiredPermission, 
  requiredCapability, 
  requiredCapabilities,
  requireAllCapabilities = false,
  fallback = null, 
  children 
}: PermissionGuardProps) {
  const router = useRouter();
  const guard = useCapabilityGuard();

  // Check access based on different criteria
  const hasAccess = (() => {
    // If specific capability is required
    if (requiredCapability) {
      return guard.hasCapability(requiredCapability);
    }
    
    // If multiple capabilities are required
    if (requiredCapabilities && requiredCapabilities.length > 0) {
      return requireAllCapabilities 
        ? guard.hasAllCapabilities(requiredCapabilities)
        : guard.hasAnyCapability(requiredCapabilities);
    }
    
    // Permission level check using hierarchy
    if (requiredPermission) {
      return hasPermissionLevel(guard.currentPermission, requiredPermission);
    }
    
    // If no requirements specified, default to allowing access
    return true;
  })();

  // Redirect if not authorized
  useEffect(() => {
    if (!guard.isLoading && (!hasAccess || guard.error)) {
      router.navigate({ to: "/unauthorised" });
    }
  }, [guard.isLoading, guard.error, hasAccess, router]);

  if (guard.isLoading) {
    return <div>Loading permissions...</div>;
  }

  if (!hasAccess || guard.error) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}