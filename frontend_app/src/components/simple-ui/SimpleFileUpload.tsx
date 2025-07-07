import { useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
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

  // Lazy load FFmpeg only when needed
  const ffmpegRef = useRef<any>(null);

  const loadFFmpeg = async () => {
    if (!ffmpegRef.current) {
      const { FFmpeg } = await import("@ffmpeg/ffmpeg");
      const ffmpeg = new FFmpeg();
      ffmpeg.on("progress", ({ progress }: any) => {
        setConversionProgress(Math.round(progress * 100));
      });
      await ffmpeg.load();
      ffmpegRef.current = ffmpeg;
    }
    return ffmpegRef.current;
  };

  const convertToWav = async (file: File): Promise<File> => {
    if (!file.type.startsWith("audio/") && !file.type.startsWith("video/")) return file;
    setIsConverting(true);
    setConversionStep("Loading FFmpeg...");
    setConversionProgress(10);
    try {
      const ffmpeg = await loadFFmpeg();
      setConversionStep("Preparing file...");
      setConversionProgress(25);
      const inputName = file.name;
      const outputName = inputName.replace(/\.[^/.]+$/, "") + ".wav";
      const fileData = await file.arrayBuffer();
      await ffmpeg.writeFile(inputName, new Uint8Array(fileData));
      setConversionStep("Converting to WAV...");
      setConversionProgress(50);
      await ffmpeg.exec([
        "-i", inputName,
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        "-y",
        outputName,
      ]);
      setConversionStep("Finalizing...");
      setConversionProgress(85);
      const outputData = await ffmpeg.readFile(outputName);
      const wavFile = new File([outputData], outputName, { type: "audio/wav" });
      setConversionProgress(100);
      setIsConverting(false);
      await ffmpeg.deleteFile(inputName);
      await ffmpeg.deleteFile(outputName);
      return wavFile;
    } catch (e) {
      setIsConverting(false);
      setConversionStep("");
      setConversionProgress(0);
      toast.error("Conversion failed. Uploading original file.");
      return file;
    }
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
      toast.success("File uploaded successfully!");
      setSelectedFile(null);
      onUploadComplete();
    } catch (e) {
      toast.error("Upload failed");
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
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
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
          <Button onClick={handleUpload} disabled={isUploading || isConverting} className="w-full">
            {isUploading ? "Uploading..." : "Upload"}
          </Button>
        </div>
      )}
    </div>
  );
}
