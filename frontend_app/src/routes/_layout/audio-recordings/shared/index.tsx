import { SharedJobsPage } from "@/components/audio-recordings/shared-jobs-page";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/audio-recordings/shared/")({
  component: SharedRecordingsRoute,
});

function SharedRecordingsRoute() {
  return <SharedJobsPage />;
}
