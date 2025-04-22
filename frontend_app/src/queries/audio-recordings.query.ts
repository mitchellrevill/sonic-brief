import type { AudioRecording } from "@/api/audio-recordings";
import type { AudioListValues } from "@/schema/audio-list.schema";
import {
  getAudioRecordings,
  getAudioTranscription,
} from "@/api/audio-recordings";
import { queryOptions } from "@tanstack/react-query";

function sortAudioRecordings(data: Array<AudioRecording>) {
  return data.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

export function getAudioRecordingsQuery(filters?: AudioListValues) {
  return queryOptions({
    queryKey: ["sonic-brief", "audio-recordings", filters],
    queryFn: () => getAudioRecordings(filters),
    select: (data) => sortAudioRecordings(data),
  });
}

export function getAudioTranscriptionQuery(id: string) {
  return queryOptions({
    queryKey: ["sonic-brief", "audio-recordings", "transcription", id],
    queryFn: () => getAudioTranscription(id),
    enabled: !!id,
  });
}
