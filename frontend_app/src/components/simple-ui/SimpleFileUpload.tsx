import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { uploadToasts } from "@/lib/toast-utils";
import { toast } from "sonner";
import { uploadFile } from "@/lib/api";

interface SimpleFileUploadProps {
  categoryId: string;
  subcategoryId: string;
  onUploadComplete: () => void;
}

export function SimpleFileUpload({ categoryId, subcategoryId, onUploadComplete }: SimpleFileUploadProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionProgress, setConversionProgress] = useState(0);
  const [conversionStep, setConversionStep] = useState("");
  const [isUploading, setIsUploading] = useState(false);



  const convertToWav = async (file: File): Promise<File> => {
    // Use shared utility for conversion
    const { convertToWavWithFFmpeg } = await import("@/lib/ffmpegConvert");
    return await convertToWavWithFFmpeg(file, {
      setIsConverting,
      setConversionProgress,
      setConversionStep,
    });
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    let fileToUpload = selectedFile;
    if (fileToUpload.type.startsWith("audio/") || fileToUpload.type.startsWith("video/")) {
      fileToUpload = await convertToWav(fileToUpload);
    }
    try {
      await uploadFile(fileToUpload, categoryId, subcategoryId);
      uploadToasts.success();
      setSelectedFile(null);
      onUploadComplete();
    } catch (e) {
      toast.error("Upload failed", {
        description: "Please check your connection and try again"
      });
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <input
        type="file"
        accept="audio/*,video/*"
        onChange={handleFileChange}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100"
      />
      {selectedFile && (
        <div className="space-y-2">
          <div>Selected: {selectedFile.name}</div>
          {(isConverting || conversionProgress > 0) && (
            <div>
              <div className="mb-1 text-sm">{conversionStep}</div>
              <Progress value={conversionProgress} />
            </div>
          )}
          <Button onClick={handleUpload} disabled={isUploading || isConverting} variant="outline" className="w-full">
            {isUploading ? "Uploading..." : "Upload"}
          </Button>
        </div>
      )}
    </div>
  );
}
