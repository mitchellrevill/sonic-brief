import { createFileRoute } from "@tanstack/react-router";
import { UserManagementTable } from "@/components/user-managment/content";

export const Route = createFileRoute("/_layout/user-management/")({
  component: UserManagementPage,
});

function UserManagementPage() {
  return (
    <div className="space-y-4 p-4 pt-6 md:p-8">
      <div className="text-2xl font-bold">User Management</div>
      <div className="text-muted-foreground">
        Manage users and their permissions.
      </div>
      <UserManagementTable />
    </div>
  );
}