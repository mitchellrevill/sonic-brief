import type { AudioRecording } from "@/api/audio-recordings";
import type { AudioListValues } from "@/schema/audio-list.schema";
import {
  getAudioRecordings,
  getAudioTranscription,
  refineAnalysis,
  getRefinementHistory,
  getRefinementSuggestions,
  type AnalysisRefinementRequest,
} from "@/api/audio-recordings";
import { queryOptions, useMutation, useQueryClient } from "@tanstack/react-query";

function sortAudioRecordings(data: Array<AudioRecording>) {
  if (!data || !Array.isArray(data)) return [];
  return data.sort(
    (a, b) =>
      new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );
}

export function getAudioRecordingsQuery(filters?: AudioListValues) {
  return queryOptions({
    queryKey: ["sonic-brief", "audio-recordings", filters || {}],
    queryFn: async () => {
      const data = await getAudioRecordings(filters);
      return data || []; // Ensure we always return an array
    },
    select: (data) => sortAudioRecordings(data || []),
  });
}

export function getAudioTranscriptionQuery(id: string) {
  return queryOptions({
    queryKey: ["sonic-brief", "audio-recordings", "transcription", id],
    queryFn: () => getAudioTranscription(id),
    enabled: !!id,
  });
}

// Analysis refinement queries
export function getRefinementHistoryQuery(jobId: string) {
  return queryOptions({
    queryKey: ["sonic-brief", "analysis-refinement", "history", jobId],
    queryFn: () => getRefinementHistory(jobId),
    enabled: !!jobId,
  });
}

export function getRefinementSuggestionsQuery(jobId: string) {
  return queryOptions({
    queryKey: ["sonic-brief", "analysis-refinement", "suggestions", jobId],
    queryFn: () => getRefinementSuggestions(jobId),
    enabled: !!jobId,
  });
}

// Analysis refinement mutation
export function useAnalysisRefinementMutation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({
      jobId,
      request,
    }: {
      jobId: string;
      request: AnalysisRefinementRequest;
    }) => refineAnalysis(jobId, request),    onSuccess: (_, variables) => {
      // Invalidate and refetch refinement history
      queryClient.invalidateQueries({
        queryKey: ["sonic-brief", "analysis-refinement", "history", variables.jobId],
      });
      
      // Optionally refetch the job data to update analysis
      queryClient.invalidateQueries({
        queryKey: ["sonic-brief", "audio-recordings"],
      });
    },
  });
}
