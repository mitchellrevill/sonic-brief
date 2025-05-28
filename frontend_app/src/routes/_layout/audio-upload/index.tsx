import { AudioUploadForm } from "@/components/dashboard/audio-upload-form";
import { VoiceRecorder } from "@/components/audio-recorder/VoiceRecorder";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { PermissionGuard } from "@/lib/permission"; 

export const Route = createFileRoute("/_layout/audio-upload/")({
  component: AudioUploadPage,
});

function AudioUploadPage() {
  const [audioFile, setAudioFile] = useState<File | null>(null);

  const handleRecordingComplete = (file: File) => {
    setAudioFile(file);
  };

  return (
    <PermissionGuard required={["Admin", "User"]}>
      <div className="flex-1 space-y-4 p-4 pt-6 md:p-8">
        <h2 className="text-3xl font-bold tracking-tight">Audio Upload</h2>
        <Card>
          <CardHeader>
            <CardTitle>Upload Audio File</CardTitle>
            <VoiceRecorder onRecordingComplete={handleRecordingComplete} />
            <CardDescription>
              Record an audio file 
            </CardDescription>
          </CardHeader>
          <CardContent>
            <AudioUploadForm audioFile={audioFile} />
          </CardContent>
        </Card>
      </div>
    </PermissionGuard>
  );
}