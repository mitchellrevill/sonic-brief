import { createFileRoute } from "@tanstack/react-router";
import { PermissionGuard } from "@/lib/permission";
// Need to explicitly import from the file path since the module hasn't been imported before
import { AdminAllJobsPage } from "../../../../components/admin/all-jobs-page"; 

export const Route = createFileRoute("/_layout/admin/all-jobs/")({
  component: AdminAllJobsRoute,
});

function AdminAllJobsRoute() {
  return (
    <PermissionGuard required={["Admin"]}>
      <AdminAllJobsPage />
    </PermissionGuard>
  );
}
