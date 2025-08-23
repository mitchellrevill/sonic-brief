// Utility to sanitize filenames for safe upload/links
function sanitizeFilename(filename: string): string {
  try {
    // First try to decode any URL-encoded characters
    filename = decodeURIComponent(filename);
  } catch {
    // If decoding fails, use original filename
  }
  
  // Split name and extension
  const lastDot = filename.lastIndexOf('.');
  let name = lastDot !== -1 ? filename.slice(0, lastDot) : filename;
  let ext = lastDot !== -1 ? filename.slice(lastDot) : '';
  
  // More aggressive cleaning: only allow alphanumeric, dash, underscore
  name = name
    .replace(/[^a-zA-Z0-9-_]/g, '_')  // Replace any non-alphanumeric/dash/underscore with underscore
    .replace(/_+/g, '_')              // Collapse multiple underscores
    .replace(/^_+|_+$/g, '')          // Remove leading/trailing underscores
    .toLowerCase();
    
  // Clean extension - only allow alphanumeric and the dot
  ext = ext.replace(/[^a-zA-Z0-9.]/g, '').toLowerCase();
  
  // Ensure we have a valid name
  return name ? `${name}${ext}` : `file${ext}`;
}
import type { MediaUploadValues } from "@/schema/audio-upload.schema";
import { useCallback, useState } from "react";
import { fetchPrompts, uploadFile } from "@/api/prompt-management";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { mediaUploadSchema } from "@/schema/audio-upload.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Loader2,
  RefreshCcw,
  Upload,
  FileText,
  Film,
  Music,
  Image,
  File,
  X,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useEffect, useRef } from "react";
import { RetentionDisclaimer } from "@/components/ui/retention-disclaimer";

interface MediaUploadFormProps {
  mediaFile?: File | null;
}

// File type configurations
const FILE_TYPES = {
  audio: {
    icon: Music,
    color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    accept: "audio/*",
    extensions: [".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"],
    description: "Audio files for transcription and analysis",
  },
  video: {
    icon: Film,
    color: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
    accept: "video/*",
    extensions: [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"],
    description: "Video files (audio will be extracted for analysis)",
  },
  document: {
    icon: FileText,
    color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    accept: ".pdf,.doc,.docx,.txt,.rtf",
    extensions: [".pdf", ".doc", ".docx", ".txt", ".rtf"],
    description: "Documents and text files for analysis",
  },
  transcript: {
    icon: File,
    color: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
    accept: ".txt,.srt,.vtt,.json",
    extensions: [".txt", ".srt", ".vtt", ".json"],
    description: "Transcript files ready for analysis",
  },
  image: {
    icon: Image,
    color: "bg-pink-100 text-pink-800 dark:bg-pink-900 dark:text-pink-200",
    accept: "image/*",
    extensions: [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
    description: "Images with text content (OCR analysis)",
  },
};

// Helper function to get file type from file
const getFileType = (file: File): keyof typeof FILE_TYPES | "other" => {
  const extension = file.name.toLowerCase().substring(file.name.lastIndexOf("."));

  for (const [type, config] of Object.entries(FILE_TYPES)) {
    if (config.extensions.includes(extension)) {
      return type as keyof typeof FILE_TYPES;
    }
  }

  if (file.type.startsWith("audio/")) return "audio";
  if (file.type.startsWith("video/")) return "video";
  if (file.type.startsWith("image/")) return "image";
  if (file.type.includes("text") || file.type.includes("document")) return "document";

  return "other";
};

export function MediaUploadForm({ mediaFile }: MediaUploadFormProps) {
  // use empty string as the controlled Select value so resets are predictable
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>("");
  const [fileType, setFileType] = useState<keyof typeof FILE_TYPES | "other" | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [transcriptText, setTranscriptText] = useState("");
  const [showTranscriptInput, setShowTranscriptInput] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionProgress, setConversionProgress] = useState(0);
  const [conversionStep, setConversionStep] = useState("");
  // Local submitting state to ensure the submit button is reliably reset
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const form = useForm<MediaUploadValues>({
    resolver: zodResolver(mediaUploadSchema),
  });

  useEffect(() => {
    if (mediaFile) {
      form.setValue("mediaFile", mediaFile);
      setFileType(getFileType(mediaFile));
    }
  }, [mediaFile, form]);

  const {
    data: categories,
    isLoading: isLoadingCategories,
    refetch: refetchCategories,
  } = useQuery({
    queryKey: ["sonic-brief", "prompts"],
    queryFn: fetchPrompts,
    select: (data) => data.data,
  });

const convertToWav = async (file: File): Promise<File> => {
    console.log("🎵 Starting audio/video conversion to WAV...");
    console.log("📁 File details:", {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: new Date(file.lastModified).toISOString()
    });

    // Use shared utility for conversion
    const { convertToWavWithFFmpeg } = await import("@/lib/ffmpegConvert");
    return await convertToWavWithFFmpeg(file, {
      setIsConverting,
      setConversionProgress,
      setConversionStep,
    });
  };  const { mutateAsync: uploadMediaMutation, isPending: isUploading } =
    useMutation({
      mutationKey: ["sonic-brief/upload-media"],
      mutationFn: async (values: MediaUploadValues) =>
        await uploadFile(
          values.mediaFile, 
          values.promptCategory, 
          values.promptSubcategory
        ),
      onSuccess: (data) => toast.success(`File processed successfully! Job ID: ${data.job_id}`),
      onError: (error) =>
        toast.error(
          error instanceof Error ? error.message : `There was an error processing your file. Please try again.`
        ),
    });const onSubmit = useCallback(
    async (values: MediaUploadValues) => {
      setIsSubmitting(true);
      console.log("🚀 Form submission started");
      console.log("📋 Submission details:", { 
        fileType, 
        hasFile: !!values.mediaFile,
        fileName: values.mediaFile?.name,
        fileSize: values.mediaFile?.size,
        promptCategory: values.promptCategory,
        promptSubcategory: values.promptSubcategory
      });
      
      // Guard: ensure a media file exists before proceeding. Users can select
      // dropdowns before attaching a file; prevent the submit flow from
      // executing in that case and surface a validation error.
      if (!values.mediaFile) {
        console.warn("No media file provided - aborting submit");
        toast.error("Please select or upload a media file before submitting.");
        // Mark form error so UI can reflect it
        form.setError("mediaFile", { type: "manual", message: "Please add a media file." });
        setIsSubmitting(false);
        return;
      }

      let processedFile = values.mediaFile;
      // Sanitize filename before upload
      if (processedFile) {
        const originalName = processedFile.name;
        const cleanName = sanitizeFilename(originalName);
        console.log("🧹 Filename sanitization:", {
          original: originalName,
          sanitized: cleanName,
          changed: cleanName !== originalName
        });
        if (cleanName !== originalName) {
          processedFile = new (window as any).File([processedFile], cleanName, { 
            type: processedFile.type, 
            lastModified: processedFile.lastModified 
          }) as File;
        }
      }
        // Convert audio and video files to WAV (extract audio from video)
      if (processedFile && (fileType === "audio" || fileType === "video")) {
        console.log(`🎵 ${fileType === "audio" ? "Audio" : "Video"} file detected, starting conversion process...`);
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
          
          console.log("🔄 Calling convertToWav function...");
          const conversionStartTime = performance.now();
          processedFile = await convertToWav(processedFile);
          const conversionEndTime = performance.now();
          const conversionDuration = ((conversionEndTime - conversionStartTime) / 1000).toFixed(2);
            console.log("✅ Conversion completed successfully!");
          console.log("⏱️ Conversion took:", conversionDuration, "seconds");
          console.log("📊 Conversion results:", {
            originalSize: values.mediaFile ? `${(values.mediaFile.size / 1024 / 1024).toFixed(2)} MB` : 'unknown',
            convertedSize: `${(processedFile.size / 1024 / 1024).toFixed(2)} MB`,
            compressionRatio: values.mediaFile ? `${((values.mediaFile.size - processedFile.size) / values.mediaFile.size * 100).toFixed(1)}%` : 'unknown',
            originalType: values.mediaFile?.type || 'unknown',
            convertedType: processedFile.type
          });
          
          toast.success("Media converted to WAV format successfully!");
        } catch (error: unknown) {
          console.error("❌ Media conversion failed:");
          const errorDetails = {
            errorMessage: error instanceof Error ? error.message : 'Unknown error',
            errorStack: error instanceof Error ? error.stack : undefined,
            errorName: error instanceof Error ? error.name : 'Error',
            originalFileName: processedFile?.name,
            originalFileSize: processedFile?.size,
            originalFileType: processedFile?.type,
            timestamp: new Date().toISOString()
          };
          console.error("💥 Conversion error details:", errorDetails);
          
          toast.error("Media conversion failed. Uploading original file instead.");
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
        console.log("📄 Non-audio file or no file, skipping conversion");
        if (processedFile) {
          console.log("📁 File details:", {
            name: processedFile.name,
            size: `${(processedFile.size / 1024 / 1024).toFixed(2)} MB`,
            type: processedFile.type,
            category: fileType
          });
        }
      }

      console.log("📤 Starting file upload...");
      console.log("📋 Upload details:", { 
        fileName: processedFile?.name,
        fileType: processedFile?.type,
        fileSize: processedFile?.size,
        category: values.promptCategory,
        subcategory: values.promptSubcategory
      });

      try {
        const uploadStartTime = performance.now();
        const result = await uploadMediaMutation({
          ...values,
          mediaFile: processedFile,
        });
        const uploadEndTime = performance.now();
        const uploadDuration = ((uploadEndTime - uploadStartTime) / 1000).toFixed(2);

        console.log("✅ Upload completed successfully!");
        console.log("⏱️ Upload took:", uploadDuration, "seconds");
        console.log("📋 Upload result:", result);

        // Reset form state after successful upload
        console.log("🧹 Resetting form...");
        form.reset({
          mediaFile: undefined,
          promptCategory: "",
          promptSubcategory: "",
        });
        // Ensure controlled selects and form validation are in sync
        setFileType(null);
        setTranscriptText("");
        setShowTranscriptInput(false);
        setSelectedCategory(""); // Reset category selection
        setSelectedSubcategory(""); // Reset subcategory selection
        // Clear any lingering errors and re-run validation so form.formState.isValid updates
        form.clearErrors();
        // trigger full form validation update (non-blocking)
        void form.trigger();
        console.log("✨ Form reset completed successfully!");
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
      } finally {
        // Ensure submitting state is cleared regardless of success or failure
        setIsSubmitting(false);
      }
    },
    [form, uploadMediaMutation, fileType]
  );  const handleFileSelect = (file: File) => {
    form.setValue("mediaFile", file);
    setFileType(getFileType(file));
    setTranscriptText("");
    setShowTranscriptInput(false);
    form.clearErrors("mediaFile");
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };  const handleTranscriptUpload = () => {
    if (!transcriptText.trim()) {
      toast.error("Please enter transcript text");
      return;
    }

    // Create a File object from the pasted text
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const fileName = `transcript-${timestamp}.txt`;
    
    // Create a proper File object using the native constructor with proper typing
    const transcriptFile = new (window as any).File([transcriptText], fileName, {
      type: 'text/plain',
      lastModified: Date.now()
    }) as File;

    console.log("Created transcript file:", {
      name: transcriptFile.name,
      size: transcriptFile.size,
      type: transcriptFile.type,
      hasFileProperties: !!(transcriptFile as any).name && !!(transcriptFile as any).lastModified
    });

    // Set the file in form and trigger validation
    form.setValue("mediaFile", transcriptFile);
    console.log("Form value set, triggering validation...");
    
    // Force form validation
    form.trigger("mediaFile").then((isValid) => {
      console.log("Media file validation result:", isValid);
      console.log("Form errors:", form.formState.errors);
      console.log("Form is valid:", form.formState.isValid);
    });
    
    setFileType("transcript");
    setShowTranscriptInput(false);
    form.clearErrors("mediaFile");
    
    toast.success("Transcript uploaded successfully!");
  };

  const selectedCategoryData = categories?.find((cat) => cat.category_id === selectedCategory);

  const renderFileIcon = () => {
    if (!fileType || fileType === "other") 
      return <File className="h-8 w-8 text-muted-foreground" />;

    const config = FILE_TYPES[fileType];
    const IconComponent = config.icon;
    return <IconComponent className="h-8 w-8 text-primary" />;
  };

  const renderFileTypeInfo = () => {
    if (!fileType || fileType === "other") return null;

    const config = FILE_TYPES[fileType];
    const IconComponent = config.icon;

    return (
      <div className="flex items-center gap-2 text-sm">
        <Badge variant="secondary" className={config.color}>
          <IconComponent className="h-3 w-3 mr-1" />
          {fileType.charAt(0).toUpperCase() + fileType.slice(1)}
        </Badge>
        <span className="text-muted-foreground">{config.description}</span>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Combined Upload and Prompt Selection Card */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Media & Select Meeting Type
              </CardTitle>
              <CardDescription>
                Upload your file and select the service area and meeting type for analysis.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* File Upload Section */}
              <FormField
                control={form.control}
                name="mediaFile"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Media File</FormLabel>
                    <FormControl>
                      <div className="space-y-4">
                        <div
                          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer hover:bg-muted/50 ${
                            isDragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25"
                          } ${field.value ? "border-green-500 bg-green-50 dark:bg-green-950" : ""}`}
                          onDrop={handleDrop}
                          onDragOver={(e) => {
                            e.preventDefault();
                            setIsDragOver(true);
                          }}
                          onDragLeave={() => setIsDragOver(false)}
                          onClick={() => fileInputRef.current?.click()}
                        >
                          <input
                            ref={fileInputRef}
                            type="file"
                            accept="audio/*,video/*,image/*,.pdf,.doc,.docx,.txt,.rtf,.srt,.vtt,.json"
                            onChange={(e) => {
                              const file = e.target.files?.[0];
                              if (file) handleFileSelect(file);
                            }}
                            className="hidden"
                          />
                          {field.value ? (
                            <div className="space-y-2">
                              <div className="flex items-center justify-center">{renderFileIcon()}</div>
                              <div className="space-y-1">
                                <p className="font-medium">{field.value.name}</p>
                                <p className="text-sm text-muted-foreground">
                                  {(field.value.size / 1024 / 1024).toFixed(2)} MB
                                </p>
                                {renderFileTypeInfo()}
                              </div>
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  field.onChange(undefined);
                                  setFileType(null);
                                  setTranscriptText("");
                                  setShowTranscriptInput(false);
                                }}
                                className="mt-2"
                              >
                                <X className="h-4 w-4 mr-1" />
                                Remove
                              </Button>
                            </div>
                          ) : (
                            <div className="space-y-2">
                              <Upload className="h-12 w-12 mx-auto text-muted-foreground" />
                              <div>
                                <p className="text-lg font-medium">Drop files here or click to browse</p>
                                <p className="text-sm text-muted-foreground">
                                  Supports audio, video, documents, transcripts, and images
                                </p>
                              </div>
                            </div>
                          )}
                        </div>
                        {/* Transcript Input Option */}
                        <div className="flex items-center justify-center">
                          <span className="text-sm text-muted-foreground">or</span>
                        </div>
                        <div className="space-y-2">
                          {!showTranscriptInput ? (
                            <Button
                              type="button"
                              variant="outline"
                              onClick={() => setShowTranscriptInput(true)}
                              disabled={!!field.value}
                              className="w-full"
                            >
                              <FileText className="h-4 w-4 mr-2" />
                              {field.value ? "Remove file first to add text" : "Paste Transcript Text"}
                            </Button>
                          ) : (
                            <div className="space-y-3">
                              <Textarea
                                placeholder="Paste your transcript text here..."
                                value={transcriptText}
                                onChange={(e) => setTranscriptText(e.target.value)}
                                rows={6}
                                className="resize-none"
                                disabled={!!field.value}
                              />
                              <div className="flex gap-2">
                                <Button
                                  type="button"
                                  onClick={handleTranscriptUpload}
                                  disabled={!transcriptText.trim() || !!field.value}
                                  className="flex-1"
                                >
                                  <CheckCircle2 className="h-4 w-4 mr-2" />
                                  Use Transcript
                                </Button>
                                <Button
                                  type="button"
                                  variant="outline"
                                  onClick={() => {
                                    setShowTranscriptInput(false);
                                    setTranscriptText("");
                                  }}
                                >
                                  Cancel
                                </Button>
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              {/* Service Area and Meeting Type Selection */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <FormField
                    control={form.control}
                    name="promptCategory"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Service Area</FormLabel>
                        <div className="flex flex-col sm:flex-row sm:items-center sm:space-x-2 gap-2 sm:gap-0">
                          <Select
                            value={selectedCategory || ""}
                            onValueChange={(value) => {
                              field.onChange(value);
                              setSelectedCategory(value);
                              setSelectedSubcategory("");
                              form.setValue("promptSubcategory", "");
                            }}
                            // Disable category select until a media file (or transcript) is attached
                            disabled={isLoadingCategories || !form.getValues("mediaFile")}
                          >
                            <FormControl>
                              <SelectTrigger className="w-full sm:w-64">
                                <SelectValue placeholder="Select a service area" />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              {categories?.map((category) => (
                                <SelectItem key={category.category_id} value={category.category_id} className="!bg-background !text-foreground hover:!bg-muted">
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
                        <FormLabel>Meeting Type</FormLabel>
                        <Select
                          value={selectedSubcategory || ""}
                          onValueChange={(value) => {
                            field.onChange(value);
                            setSelectedSubcategory(value);
                          }}
                          // Disable subcategory until a file is attached and a category selected
                          disabled={!form.getValues("mediaFile") || !selectedCategory}
                        >
                          <FormControl>
                            <SelectTrigger className="w-full sm:w-64">
                              <SelectValue placeholder="Select a meeting type" />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {selectedCategoryData?.subcategories.map((subcategory) => (
                              <SelectItem key={subcategory.subcategory_id} value={subcategory.subcategory_id} className="!bg-background !text-foreground hover:!bg-muted">
                                {subcategory.subcategory_name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                {/* Right Column - Prompt Preview */}
                <div className="space-y-2">
                  <FormLabel htmlFor="prompt-preview">Prompt Preview</FormLabel>
                  <div className="h-[200px] border rounded-md bg-muted/50">
                    <Textarea
                      id="prompt-preview"
                      value={(() => {
                        if (!selectedSubcategory || !selectedCategoryData) {
                          return "";
                        }
                        const subcategory = selectedCategoryData.subcategories.find(
                          sub => sub.subcategory_id === selectedSubcategory
                        );
                        if (!subcategory?.prompts) {
                          return "No prompts found for this meeting type.";
                        }
                        // Format prompts for display
                        return Object.entries(subcategory.prompts)
                          .map(([key, value]) => `${key}:\n${value}`)
                          .join('\n\n---\n\n');
                      })()}
                      placeholder="Select a service area and meeting type to view the associated prompts..."
                      readOnly
                      className="h-full resize-none bg-transparent border-none focus:ring-0 text-sm"
                    />
                  </div>
                  <FormDescription>
                    This displays the prompts that will be used for AI analysis when you select a meeting type.
                  </FormDescription>
                </div>
              </div>
            </CardContent>
          </Card>
          {/* Processing Info */}
          {fileType && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="h-5 w-5 text-blue-500 mt-0.5" />
                  <div className="space-y-1">
                    <p className="font-medium text-sm">Processing Information</p>
                    <p className="text-sm text-muted-foreground">
                      {fileType === "audio" && "Audio will be transcribed and analyzed using AI prompts."}
                      {fileType === "video" && "Audio will be extracted from video, transcribed, and analyzed."}
                      {fileType === "document" && "Text content will be extracted and analyzed using AI prompts."}
                      {fileType === "transcript" && "Transcript will be directly analyzed using AI prompts."}
                      {fileType === "image" && "Text will be extracted using OCR and analyzed using AI prompts."}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
          {/* Submit Button */}
          <Button
            type="submit"
            disabled={isUploading || isSubmitting || !form.formState.isValid || isConverting}
            className="w-full"
            size="lg"
          >
            {(isUploading || isSubmitting) ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Processing Upload...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload and Process
              </>
            )}
          </Button>
        </form>
      </Form>
      {/* Conversion Progress Dialog */}
      <Dialog open={isConverting} onOpenChange={() => {}}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Music className="h-5 w-5 text-primary" />
              Converting Audio to WAV
            </DialogTitle>
            <DialogDescription>
              Please wait while we convert your audio file to WAV format for Azure Speech.
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
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {/* Retention Disclaimer */}
      <RetentionDisclaimer />
    </div>
  );
}
