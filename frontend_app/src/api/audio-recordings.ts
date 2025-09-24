import type { AudioListValues } from "@/schema/audio-list.schema";
import { httpClient } from "@/api/httpClient";
import { JOBS_API, TRANSCRIPTION_API } from "@/lib/apiConstants";

export interface AudioRecording {
  id: string;
  user_id: string;
  file_path: string;
  transcription_file_path: string | null;
  analysis_file_path: string | null;
  prompt_category_id: string;
  prompt_subcategory_id: string;
  status: "uploaded" | "processing" | "completed" | "error";
  transcription_id: string | null;
  created_at: number;
  updated_at: number;
  type: string;
  _rid: string;
  _self: string;
  _etag: string;
  _attachments: string;
  _ts: number;
}

export interface PaginatedResponse<T> {
  jobs: T[];
  count: number;
  status: number;
}

export async function getAudioRecordings(filters?: AudioListValues & { page?: number; per_page?: number }) {
  // Call the jobs listing endpoint. The deployed backend exposes `/api/jobs`.
  // Convert page/per_page to limit/offset for backend compatibility
  const { page, per_page, ...filterParams } = filters || {};
  
  const params: Record<string, any> = {};
  
  // Add filter parameters
  if (filterParams) {
    Object.entries(filterParams).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') {
        params[key] = value;
      }
    });
  }
  
  // Add pagination parameters (backend expects limit/offset)
  if (per_page) {
    params.limit = per_page;
  }
  if (page && per_page) {
    params.offset = (page - 1) * per_page;
  }

  const response = await httpClient.get(JOBS_API, { params });

  // Backend returns { status, count, jobs }
  return response.data as PaginatedResponse<AudioRecording>;
}

export async function getAudioTranscription(id: string) {
  const response = await httpClient.get(TRANSCRIPTION_API(id));
  return response.data;
}

// Analysis refinement API functions
export interface AnalysisRefinementRequest {
  user_request: string;
}

export interface AnalysisRefinementResponse {
  status: string;
  message: string;
  response: string;
  refinement_id: string;
  timestamp: number;
}

export interface RefinementHistoryEntry {
  id: string;
  user_message: string;
  ai_response: string;
  timestamp: number;
  user_id: string;
}

export interface RefinementHistoryResponse {
  status: string;
  job_id: string;
  history: RefinementHistoryEntry[];
  count: number;
}

export async function refineAnalysis(
  jobId: string,
  request: AnalysisRefinementRequest
): Promise<AnalysisRefinementResponse> {
  const response = await httpClient.post(
    `${JOBS_API}/${jobId}/refinements`,
    request
  );
  return response.data;
}

export async function getRefinementHistory(
  jobId: string
): Promise<RefinementHistoryResponse> {
  const response = await httpClient.get(
    `${JOBS_API}/${jobId}/refinements`
  );
  return response.data;
}

export async function getRefinementSuggestions(jobId: string): Promise<{
  status: string;
  job_id: string;
  suggestions: string[];
}> {
  const response = await httpClient.get(
    `${JOBS_API}/${jobId}/refinements/suggestions`
  );
  return response.data;
}
