import { createFileRoute } from "@tanstack/react-router";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";
// Need to explicitly import from the file path since the module hasn't been imported before
import { AdminAllJobsPage } from "../../../../components/admin/all-jobs-page"; 

export const Route = createFileRoute("/_layout/admin/all-jobs/")({
  component: AdminAllJobsRoute,
});

function AdminAllJobsRoute() {
  return (
    <PermissionGuard requiredCapability={Capability.CAN_VIEW_ALL_JOBS}>
      <AdminAllJobsPage />
    </PermissionGuard>
  );
}
