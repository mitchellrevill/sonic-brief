import { createFileRoute } from "@tanstack/react-router";
import { UserManagementTable } from "@/components/user-managment/content";
import { PermissionGuard } from "@/lib/permission"; 

export const Route = createFileRoute("/_layout/user-management/")({
  component: UserManagementPage,
});

function UserManagementPage() {
  return (
    <PermissionGuard required={["Admin"]}>
    <div className="space-y-4 p-4 pt-6 md:p-8">
      <div className="text-2xl font-bold">User Management</div>
      <div className="text-muted-foreground">
        Manage users and their permissions.
      </div>
      <UserManagementTable />
    </div>
    </PermissionGuard>
  );
}