import type { AudioRecording, PaginatedResponse } from "@/api/audio-recordings";
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

export function getAudioRecordingsQuery(filters?: AudioListValues & { page?: number; per_page?: number }) {
  const page = filters?.page ?? 1;
  const perPage = filters?.per_page ?? 12;

  // Build a stable key including pagination to allow separate caching per page
  return queryOptions({
    queryKey: ["sonic-brief", "audio-recordings", page, perPage, filters || {}],
    queryFn: async () => {
      const response = await getAudioRecordings({ ...filters, page, per_page: perPage });
      
      // Handle the paginated response structure
      if (response && typeof response === 'object' && 'jobs' in response) {
        const paginatedResponse = response as PaginatedResponse<AudioRecording>;
        return {
          jobs: sortAudioRecordings(paginatedResponse.jobs || []),
          count: paginatedResponse.count || 0,
          status: paginatedResponse.status || 200
        };
      }
      
      // Fallback for backward compatibility
      return {
        jobs: sortAudioRecordings(Array.isArray(response) ? (response as AudioRecording[]) : []),
        count: Array.isArray(response) ? (response as AudioRecording[]).length : 0,
        status: 200
      };
    },
  });
}

export function getAudioTranscriptionQuery(id: string) {
  return queryOptions({
    queryKey: ["sonic-brief", "audio-recordings", "transcription", id],
    queryFn: () => getAudioTranscription(id),
    enabled: !!id,
    retry: (failureCount, error: any) => {
      // Only retry for 404 errors (transcription not ready yet)
      if (error?.status === 404 || error?.response?.status === 404) {
        // Retry up to 20 times for 404s (about 10 minutes with exponential backoff)
        return failureCount < 20;
      }
      // For other errors, use default retry logic (3 times)
      return failureCount < 3;
    },
    retryDelay: (attemptIndex) => {
      // For 404 errors, use a more aggressive retry pattern
      // Start with 3 seconds, then exponential backoff with max 30 seconds
      return Math.min(3000 * Math.pow(1.5, attemptIndex), 30000);
    },
    // Prevent showing error states for 404s during retries
    throwOnError: (error: any) => {
      // Don't throw 404 errors to prevent toast notifications
      if (error?.status === 404 || error?.response?.status === 404) {
        return false;
      }
      return true;
    },
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
