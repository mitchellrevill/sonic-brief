import { toast } from "sonner";

export interface FFmpegConvertOptions {
  setIsConverting?: (v: boolean) => void;
  setConversionProgress?: (v: number) => void;
  setConversionStep?: (v: string) => void;
}

export async function convertToWavWithFFmpeg(
  file: File,
  opts: FFmpegConvertOptions = {}
): Promise<File> {
  const { setIsConverting, setConversionProgress, setConversionStep } = opts;
  if (!file.type.startsWith("audio/") && !file.type.startsWith("video/")) return file;
  setIsConverting?.(true);
  setConversionStep?.("Loading FFmpeg...");
  setConversionProgress?.(10);
  let ffmpeg: any;
  try {
    const { FFmpeg } = await import("@ffmpeg/ffmpeg");
    ffmpeg = new FFmpeg();
    ffmpeg.on("progress", ({ progress }: any) => {
      setConversionProgress?.(Math.round(progress * 100));
    });
    await ffmpeg.load();
    setConversionStep?.("Preparing file...");
    setConversionProgress?.(25);
    const inputName = file.name;
    const outputName = inputName.replace(/\.[^/.]+$/, "") + ".wav";
    const fileData = await file.arrayBuffer();
    await ffmpeg.writeFile(inputName, new Uint8Array(fileData));
    setConversionStep?.("Converting to WAV...");
    setConversionProgress?.(50);
    await ffmpeg.exec([
      "-i", inputName,
      "-acodec", "pcm_s16le",
      "-ar", "16000",
      "-ac", "1",
      "-y",
      outputName,
    ]);
    setConversionStep?.("Finalizing...");
    setConversionProgress?.(85);
    const outputData = await ffmpeg.readFile(outputName);
    const wavFile = new File([outputData], outputName, { type: "audio/wav" });
    setConversionProgress?.(100);
    setIsConverting?.(false);
    await ffmpeg.deleteFile(inputName);
    await ffmpeg.deleteFile(outputName);
    return wavFile;
  } catch (e) {
    setIsConverting?.(false);
    setConversionStep?.("");
    setConversionProgress?.(0);
    toast.error("Conversion failed. Uploading original file.");
    return file;
  }
}
