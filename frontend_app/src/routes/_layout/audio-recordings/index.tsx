import type { AudioListValues } from "@/schema/audio-list.schema";
import { AudioRecordingsCombined } from "@/components/audio-recordings/audio-recordings-combined";
import { AudioRecordingsHeader } from "@/components/audio-recordings/header";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/_layout/audio-recordings/")({
  component: AudioRecordingsIndexComponent,
});

const initialFilters: AudioListValues = {
  job_id: "",
  status: "all",
  created_at: undefined,
};

function AudioRecordingsIndexComponent() {
  return (
    <div className="flex-1 space-y-4 p-4 pt-6 md:p-8">
      <AudioRecordingsHeader />
      <AudioRecordingsCombined initialFilters={initialFilters} />
    </div>
  );
}
