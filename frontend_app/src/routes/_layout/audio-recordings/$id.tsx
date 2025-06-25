import { RecordingDetailsPageWrapper } from "@/components/audio-recordings/recording-details-page-wrapper";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/audio-recordings/$id")({
  component: RecordingDetailsComponent,
});

function RecordingDetailsComponent() {
  const { id } = Route.useParams();

  return <RecordingDetailsPageWrapper id={id} />;
}
