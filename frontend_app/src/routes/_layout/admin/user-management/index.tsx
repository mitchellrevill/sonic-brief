import { createFileRoute } from "@tanstack/react-router";
import { UserManagementTable } from "@/components/user-managment/content";
import { UserManagementHeader } from "@/components/user-managment/header";
import { PermissionGuard } from "@/lib/permission"; 

export const Route = createFileRoute("/_layout/admin/user-management/")({
  component: AdminUserManagementPage,
});

function AdminUserManagementPage() {
  return (
    <PermissionGuard required={["Admin"]}>
      <div className="min-h-screen bg-background">
        <UserManagementHeader />
        <div className="container mx-auto px-4 py-6 space-y-6">
          <UserManagementTable />
        </div>
      </div>
    </PermissionGuard>
  );
}
