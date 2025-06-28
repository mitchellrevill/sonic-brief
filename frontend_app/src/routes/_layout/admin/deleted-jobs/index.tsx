import { createFileRoute } from "@tanstack/react-router";
import { AdminDeletedJobsPage } from "@/components/admin/deleted-jobs-page";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";

export const Route = createFileRoute("/_layout/admin/deleted-jobs/")({
  component: AdminDeletedJobsRoute,
});

function AdminDeletedJobsRoute() {
  return (
    <PermissionGuard requiredCapability={Capability.CAN_VIEW_ALL_JOBS}>
      <AdminDeletedJobsPage />
    </PermissionGuard>
  );
}
