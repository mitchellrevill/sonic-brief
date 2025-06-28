import { SharedJobsPage } from "@/components/audio-recordings/shared-jobs-page";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/audio-recordings/shared/")({
  component: SharedRecordingsRoute,
});

function SharedRecordingsRoute() {
  return (
    <PermissionGuard requiredCapability={Capability.VIEW_TRANSCRIPTIONS}>
      <SharedJobsPage />
    </PermissionGuard>
  );
}
