import { MediaUploadHeader } from "@/components/media-upload/header";
import { MediaUploadForm } from "@/components/media-upload/upload-form";
import { AudioRecordingModal } from "@/components/audio-recorder/AudioRecordingModal";
import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PermissionGuard } from "@/lib/permission";

export const Route = createFileRoute("/_layout/audio-upload/")({
  component: MediaUploadPage,
});

function MediaUploadPage() {
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleRecordingComplete = (file: File) => {
    setAudioFile(file);
    setIsModalOpen(false);
  };

  return (
    <PermissionGuard required={["Admin", "User"]}>      <div className="flex-1 space-y-6 p-4 pt-6 md:p-8">
        <MediaUploadHeader onStartRecording={() => setIsModalOpen(true)} />
        <MediaUploadForm mediaFile={audioFile} />
        <AudioRecordingModal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onRecordingComplete={handleRecordingComplete}
        />
      </div>
    </PermissionGuard>
  );
}