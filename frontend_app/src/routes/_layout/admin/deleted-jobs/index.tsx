import { createFileRoute } from "@tanstack/react-router";
import { AdminDeletedJobsPage } from "@/components/admin/deleted-jobs-page";
import { PermissionGuard } from "@/lib/permission";

export const Route = createFileRoute("/_layout/admin/deleted-jobs/")({
  component: AdminDeletedJobsRoute,
});

function AdminDeletedJobsRoute() {
  return (
    <PermissionGuard required={["Admin"]}>
      <AdminDeletedJobsPage />
    </PermissionGuard>
  );
}
