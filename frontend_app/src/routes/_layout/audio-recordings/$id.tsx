import { RecordingDetailsPage } from "@/components/audio-recordings/recording-details-page";
import { RecordingDetailsSkeleton } from "@/components/audio-recordings/recording-details-page-skeleton";
import { getAudioRecordingsQuery } from "@/queries/audio-recordings.query";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/audio-recordings/$id")({
  component: RecordingDetailsComponent,
});

function RecordingDetailsComponent() {
  const { id } = Route.useParams();

  const {
    data: allRecordings,
    isLoading,
    isError,
  } = useQuery(getAudioRecordingsQuery());

  const recording = allRecordings?.find((recording) => recording.id === id);

  if (isLoading) {
    return <RecordingDetailsSkeleton />;
  }

  if (!recording || isError) {
    return (
      <div className="container mx-auto px-4 py-6">
        <div className="rounded border border-red-400 bg-red-100 px-4 py-3 text-red-700">
          <p className="mt-2">
            <Link to="/audio-recordings" className="text-blue-500 underline">
              Return to recordings list
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return <RecordingDetailsPage recording={recording} />;
}
