import type { AudioListValues } from "@/schema/audio-list.schema";
import { AudioRecordingsCombined } from "@/components/audio-recordings/audio-recordings-combined";
import { AudioRecordingsHeader } from "@/components/audio-recordings/header";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";
import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";

const audioRecordingsSearchSchema = z.object({
  page: z.number().min(1).optional().default(1),
  per_page: z.number().min(1).max(100).optional().default(12),
  job_id: z.string().optional(),
  status: z.enum(["all", "uploaded", "processing", "completed", "failed"]).optional().default("all"),
  created_at: z.string().optional(),
});

export const Route = createFileRoute("/_layout/audio-recordings/")({
  component: AudioRecordingsIndexComponent,
  validateSearch: audioRecordingsSearchSchema,
});

function AudioRecordingsIndexComponent() {
  const { page, per_page, job_id, status, created_at } = Route.useSearch();
  
  const initialFilters: AudioListValues & { page: number; per_page: number } = {
    job_id: job_id || "",
    status: status || "all",
    created_at: created_at || undefined,
    page,
    per_page,
  };

  return (
    <PermissionGuard requiredCapability={Capability.VIEW_TRANSCRIPTIONS}>
      <div className="flex-1 space-y-4  md:p-8">
        <AudioRecordingsHeader />
        <AudioRecordingsCombined initialFilters={initialFilters} />
      </div>
    </PermissionGuard>
  );
}
