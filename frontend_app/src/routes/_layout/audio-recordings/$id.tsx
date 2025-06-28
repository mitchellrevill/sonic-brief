import { RecordingDetailsPageWrapper } from "@/components/audio-recordings/recording-details-page-wrapper";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/audio-recordings/$id")({
  component: RecordingDetailsComponent,
});

function RecordingDetailsComponent() {
  const { id } = Route.useParams();

  return (
    <PermissionGuard requiredCapability={Capability.VIEW_TRANSCRIPTIONS}>
      <RecordingDetailsPageWrapper id={id} />
    </PermissionGuard>
  );
}
