import type { MediaUploadValues } from "@/schema/audio-upload.schema";
import { useCallback, useState } from "react";
import { fetchPrompts, uploadFile } from "@/api/prompt-management";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { mediaUploadSchema } from "@/schema/audio-upload.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, RefreshCcw, Music } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useEffect } from "react";
import { fetchFile } from "@ffmpeg/util"
import { FFmpeg } from "@ffmpeg/ffmpeg";
import { useRef } from "react";



export function AudioUploadForm({ audioFile }: { audioFile?: File | null }) {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState<string | null>(
    null,
  );
  const [isConverting, setIsConverting] = useState(false);
  const [conversionProgress, setConversionProgress] = useState(0);
  const [conversionStep, setConversionStep] = useState("");


    const form = useForm<MediaUploadValues>({
    resolver: zodResolver(mediaUploadSchema),
  });
 const ffmpegRef = useRef<FFmpeg | null>(null);
   useEffect(() => {
    if (audioFile) {
      form.setValue("mediaFile", audioFile);
    }
  }, [audioFile, form]);

  const {
    data: categories,
    isLoading: isLoadingCategories,
    refetch: refetchCategories,
  } = useQuery({
    queryKey: ["sonic-brief", "prompts"],
    queryFn: fetchPrompts,
    select: (data) => data.data,
  });


const loadFFmpeg = async () => {
    console.log("🎵 Starting FFmpeg initialization (Dashboard)...");
    
    if (!ffmpegRef.current) {
      console.log("📦 Creating new FFmpeg instance...");
      const ffmpeg = new FFmpeg();
      
      // Add logging for FFmpeg events
      ffmpeg.on("log", ({ message }) => {
        console.log("🔧 FFmpeg log:", message);
      });
      
      ffmpeg.on("progress", ({ progress, time }) => {
        console.log(`⏳ FFmpeg progress: ${Math.round(progress * 100)}% (time: ${time}s)`);
      });
      
      console.log("🚀 Loading FFmpeg core and wasm files...");
      await ffmpeg.load();
      console.log("✅ FFmpeg loaded successfully");
      
      ffmpegRef.current = ffmpeg;
    } else {
      console.log("♻️ Reusing existing FFmpeg instance");
    }
    return ffmpegRef.current;
  };

const convertToWebm = async (file: File): Promise<File> => {
    console.log("Starting WebM conversion for file:", file.name, "Size:", file.size, "Type:", file.type);

    try {
      setConversionStep("Loading FFmpeg...");
      setConversionProgress(10);
      console.log("Loading FFmpeg...");
      
      const ffmpeg = await loadFFmpeg();
      console.log("FFmpeg loaded successfully");
      
      setConversionStep("Preparing audio file...");
      setConversionProgress(25);
      
      const inputName = file.name;
      const baseName = inputName.replace(/\.[^/.]+$/, "");
      const outputName = `${baseName}.webm`;
      
      console.log("File names - Input:", inputName, "Output:", outputName);

      console.log("Writing file to FFmpeg filesystem...");
      await ffmpeg.writeFile(inputName, await fetchFile(file));
      console.log("File written successfully");

      setConversionStep("Converting to WebM format...");
      setConversionProgress(50);      const ffmpegArgs = [
        "-i", inputName,
        "-c:a", "libopus",  // Use Opus codec for audio
        "-b:a", "128k",     // Audio bitrate
        "-ac", "1",         // Mono audio
        "-y",               // Overwrite output file
        outputName,
      ];
      
      console.log("Executing FFmpeg with args:", ffmpegArgs);
      await ffmpeg.exec(ffmpegArgs);
      console.log("FFmpeg execution completed");
      
      setConversionStep("Finalizing conversion...");
      setConversionProgress(85);      console.log("Reading converted file...");
      const data = await ffmpeg.readFile(outputName);
      const dataSize = data instanceof Uint8Array ? data.byteLength : data.length;
      console.log("Converted file read successfully, size:", dataSize, "bytes");
      
      if (dataSize === 0) {
        throw new Error("Output file is empty");
      }

      console.log("Cleaning up temporary files...");
      await ffmpeg.deleteFile(inputName);
      await ffmpeg.deleteFile(outputName);
      console.log("Cleanup completed");

      setConversionProgress(100);      const convertedFile = new (File as any)([data], outputName, { type: "audio/webm" });
      console.log("Conversion successful! New file size:", convertedFile.size);
      
      return convertedFile;    } catch (error: unknown) {
      console.error("❌ FFmpeg conversion failed:");
      console.error("Error details:", {
        message: error instanceof Error ? error.message : 'Unknown error',
        name: error instanceof Error ? error.name : 'Error',
        stack: error instanceof Error ? error.stack : undefined,
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type
      });
      
      // Reset conversion UI state
      setConversionStep("");
      setConversionProgress(0);
      
      console.warn("⚠️ Falling back to original file due to conversion failure");
      throw error;
    }
  };




  const { mutateAsync: uploadAudioMutation, isPending: isUploading } =
    useMutation({
      mutationKey: ["sonic-brief/upload-audio"],
      mutationFn: async (values: MediaUploadValues) =>
        await uploadFile(
          values.mediaFile,
          values.promptCategory,
          values.promptSubcategory,
        ),
      onSuccess: (data) =>
        toast.success(`File uploaded successfully! Job ID: ${data.job_id}`),
      onError: () =>
        toast.error(
          "There was an error uploading your file. Please try again.",
        ),
    });  const onSubmit = useCallback(
    async (values: MediaUploadValues) => {
      console.log("🚀 Form submission started (Dashboard)");
      console.log("📋 Submission details:", { 
        hasFile: !!values.mediaFile,
        fileName: values.mediaFile?.name,
        fileSize: values.mediaFile?.size,
        promptCategory: values.promptCategory,
        promptSubcategory: values.promptSubcategory
      });
      
      let processedFile = values.mediaFile;
      if (processedFile && typeof processedFile !== "string") {
        console.log("🎵 Audio file detected, starting conversion process...");
        console.log("🎧 Audio file details:", {
          name: processedFile.name,
          size: `${(processedFile.size / 1024 / 1024).toFixed(2)} MB`,
          type: processedFile.type,
          lastModified: new Date(processedFile.lastModified).toISOString()
        });
        
        try {
          setIsConverting(true);
          setConversionProgress(0);
          setConversionStep("Starting conversion...");
          
          console.log("🔄 Calling convertToWebm function...");
          const conversionStartTime = performance.now();
          processedFile = await convertToWebm(processedFile);
          const conversionEndTime = performance.now();
          const conversionDuration = ((conversionEndTime - conversionStartTime) / 1000).toFixed(2);
          
          console.log("✅ Conversion completed successfully!");
          console.log("⏱️ Conversion took:", conversionDuration, "seconds");
          console.log("📊 Conversion results:", {
            originalSize: `${(values.mediaFile.size / 1024 / 1024).toFixed(2)} MB`,
            convertedSize: `${(processedFile.size / 1024 / 1024).toFixed(2)} MB`,
            compressionRatio: `${((values.mediaFile.size - processedFile.size) / values.mediaFile.size * 100).toFixed(1)}%`,
            originalType: values.mediaFile.type,
            convertedType: processedFile.type
          });
          
          toast.success("Audio converted to WebM format successfully!");
        } catch (error: unknown) {
          console.error("❌ Audio conversion failed:");
          const errorDetails = {
            errorMessage: error instanceof Error ? error.message : 'Unknown error',
            errorStack: error instanceof Error ? error.stack : undefined,
            errorName: error instanceof Error ? error.name : 'Error',
            originalFileName: values.mediaFile?.name,
            originalFileSize: values.mediaFile?.size,
            originalFileType: values.mediaFile?.type,
            timestamp: new Date().toISOString()
          };
          console.error("💥 Conversion error details:", errorDetails);
          
          toast.error("Audio conversion failed. Uploading original file instead.");
          console.warn("⚠️ Falling back to original file due to conversion failure");
          // Use original file when conversion fails
          processedFile = values.mediaFile;
        } finally {
          setIsConverting(false);
          setConversionProgress(0);
          setConversionStep("");
          console.log("🧹 Conversion cleanup completed");
        }
      } else {
        console.log("📄 No file or file is string, skipping conversion");
      }
      
      console.log("📤 Starting file upload...");
      console.log("📋 Upload details:", { 
        fileName: processedFile?.name,
        fileSize: processedFile?.size ? `${(processedFile.size / 1024 / 1024).toFixed(2)} MB` : 'unknown',
        fileType: processedFile?.type
      });
      
      try {
        const uploadStartTime = performance.now();
        const result = await uploadAudioMutation({
          ...values,
          mediaFile: processedFile,
        });
        const uploadEndTime = performance.now();
        const uploadDuration = ((uploadEndTime - uploadStartTime) / 1000).toFixed(2);
        
        console.log("✅ Upload completed successfully!");
        console.log("⏱️ Upload took:", uploadDuration, "seconds");
        console.log("📋 Upload result:", result);
        
      } catch (uploadError: unknown) {
        console.error("❌ Upload failed:");
        console.error("💥 Upload error details:", {
          errorMessage: uploadError instanceof Error ? uploadError.message : 'Unknown upload error',
          errorStack: uploadError instanceof Error ? uploadError.stack : undefined,
          fileName: processedFile?.name,
          fileSize: processedFile?.size,
          timestamp: new Date().toISOString()
        });
        throw uploadError; // Re-throw to let the mutation handle it
      }
      
      console.log("🧹 Resetting form...");
      form.reset({
        mediaFile: undefined,
        promptCategory: "",
        promptSubcategory: "",
      });
      console.log("✨ Form reset completed successfully!");
    },
    [form, uploadAudioMutation],
  );
  const selectedCategoryData = categories?.find(
    (cat) => cat.category_id === selectedCategory,
  );
  return (
    <>
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8"><FormField
              control={form.control}
              name="mediaFile"
              render={({ field }) => (
              <FormItem>
                <FormLabel>Audio File</FormLabel>
                <FormControl>
                <Input
                  type="file"
                  accept="audio/*"
                  onChange={(e) => {
                  const file = e.target.files?.[0];
                  field.onChange(file);
                  }}
                  className="w-full"
                  disabled={!!field.value}
                />
                </FormControl>
                {field.value && typeof field.value !== "string" && (
                <div className="text-xs text-muted-foreground mt-1 flex items-center gap-2">
                  Selected file: {field.value.name}
                  <button
                  type="button"
                  className="ml-2 text-red-500 underline"
                  onClick={() => field.onChange(undefined)}
                  >
                  Clear
                  </button>
                </div>
                )}
                <FormDescription>
                Upload an audio file 
                </FormDescription>
                <FormMessage />
              </FormItem>
              )}
            />            
            <FormField
              control={form.control}
              name="promptCategory"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Prompt Category</FormLabel>
                  <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2 gap-2 sm:gap-0">
                    <Select
                      value={selectedCategory || ""}
                      onValueChange={(value) => {
                        field.onChange(value);
                        setSelectedCategory(value);
                        setSelectedSubcategory(null);
                        form.setValue("promptSubcategory", "");
                      }}
                      disabled={isLoadingCategories}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full sm:w-64">
                          <SelectValue placeholder="Select a category" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {categories?.map((category) => (
                          <SelectItem
                            key={category.category_id}
                            value={category.category_id}
                          >
                            {category.category_name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => refetchCategories()}
                      disabled={isLoadingCategories}
                      className="flex items-center w-full sm:w-auto px-2"
                    >
                      <RefreshCcw className="h-4 w-4" />
                      <span className="ml-2 hidden sm:inline">
                        {isLoadingCategories ? "Refreshing..." : "Refresh"}
                      </span>
                    </Button>
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="promptSubcategory"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Prompt Subcategory</FormLabel>
                  <Select
                    value={selectedSubcategory || ""}
                    onValueChange={(value) => {
                      field.onChange(value);
                      setSelectedSubcategory(value);
                    }}
                    disabled={!selectedCategory}
                  >
                    <FormControl>
                      <SelectTrigger className="w-full sm:w-64">
                        <SelectValue placeholder="Select a subcategory" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {selectedCategoryData?.subcategories.map((subcategory) => (
                        <SelectItem
                          key={subcategory.subcategory_id}
                          value={subcategory.subcategory_id}
                        >
                          {subcategory.subcategory_name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />            <Button
              type="submit"
              disabled={isUploading || !form.formState.isValid || isConverting}
              className="w-full mt-4"
            >
              {isUploading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                "Upload and Process"
              )}            </Button>
          </form>
        </Form>

        {/* Conversion Progress Dialog */}
    <Dialog open={isConverting} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Music className="h-5 w-5 text-primary" />
            Converting Audio to WebM
          </DialogTitle>
          <DialogDescription>
            Please wait while we convert your audio file to an optimized format for processing.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{conversionStep}</span>
              <span className="font-medium">{conversionProgress}%</span>
            </div>
            <Progress value={conversionProgress} className="h-2" />
          </div>
          <div className="text-xs text-muted-foreground text-center">
            This may take a few moments depending on the size of your audio file.
          </div>        </div>
      </DialogContent>
    </Dialog>
    </>
  );
}
