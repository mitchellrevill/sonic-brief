import { Button } from "@/components/ui/button";
import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { Link } from "@tanstack/react-router";
import { FileAudio } from "lucide-react";

export function AudioRecordingsHeader() {
  return (
    <div className="flex items-center justify-between px-2 py-2 md:px-4 md:py-3">
      <div className="space-y-0.5">
        <h2 className="text-lg md:text-xl font-semibold tracking-tight">
          Audio Recordings
        </h2>        <SmartBreadcrumb
          items={[{ label: "Audio Recordings", isCurrentPage: true }]}
        />
        <p className="text-muted-foreground text-xs md:text-sm">
          Manage and monitor all uploaded audio files and their processing status.
        </p>
      </div>
      <Link to="/audio-upload">        <Button size="sm" className="px-2 py-1">
          <FileAudio className="mr-2 h-4 w-4" />
          <span className="hidden sm:inline">Add New Media File</span>
        </Button>
      </Link>
    </div>
  );
}
