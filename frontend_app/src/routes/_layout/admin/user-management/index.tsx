import { createFileRoute } from "@tanstack/react-router";
import { UserManagementDashboard } from "@/components/user-managment/UserManagementDashboard";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";

export const Route = createFileRoute("/_layout/admin/user-management/")({
  component: AdminUserManagementPage,
});

function AdminUserManagementPage() {
  return (
    <PermissionGuard requiredCapability={Capability.CAN_VIEW_USERS}>
      <UserManagementDashboard />
    </PermissionGuard>
  );
}
