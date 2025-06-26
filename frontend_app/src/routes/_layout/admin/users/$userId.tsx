import { createFileRoute } from "@tanstack/react-router";
import { UserDetailsPage } from "@/components/user-managment/userdetails/user-details";
import { PermissionGuard } from "@/lib/permission";

export const Route = createFileRoute("/_layout/admin/users/$userId")({
  component: UserDetailsPageRoute,
});

function UserDetailsPageRoute() {
  return (
    <PermissionGuard required={["Admin"]}>
      <div className="min-h-screen bg-background">
        <UserDetailsPage />
      </div>
    </PermissionGuard>
  );
}
