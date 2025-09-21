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
import { uploadFile, fetchCategories, fetchSubcategories } from "@/api/prompt-management";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Form, FormField, FormItem, FormMessage } from "@/components/ui/form";
import { Textarea } from "@/components/ui/textarea";
// Removed legacy Select imports after UX modernization
import { Badge } from "@/components/ui/badge";
import { mediaUploadSchema } from "@/schema/audio-upload.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, RefreshCcw, Upload, FileText, Film, Music, Image, File, ChevronDown, ChevronUp, Copy, Check } from "lucide-react";
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
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>("");
  // Parent category currently expanded to show its child categories (hierarchical folders)
  const [expandedParentCategoryId, setExpandedParentCategoryId] = useState<string>("");
  const [fileType, setFileType] = useState<keyof typeof FILE_TYPES | "other" | null>(null);
  // legacy inner zone drag state removed (full-page drag implemented)
  const [isWindowDrag, setIsWindowDrag] = useState(false); // full-page drag highlight
  const [transcriptText, setTranscriptText] = useState("");
  const [showTranscriptInput, setShowTranscriptInput] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [conversionProgress, setConversionProgress] = useState(0);
  const [conversionStep, setConversionStep] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [promptPreviewOpen, setPromptPreviewOpen] = useState(true);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

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
    queryKey: ["sonic-brief", "prompt-management", "categories"],
    queryFn: fetchCategories,
  });

  const { data: subcategories } = useQuery({
    queryKey: ["sonic-brief", "prompt-management", "subcategories"],
    queryFn: () => fetchSubcategories(),
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
    setIsWindowDrag(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) handleFileSelect(files[0]);
  };

  const handleTranscriptUpload = () => {
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

  // window level drag listeners
  useEffect(() => {
    const onDragEnter = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes("Files")) {
        setIsWindowDrag(true);
      }
    };
    const onDragOver = (e: DragEvent) => {
      if (e.dataTransfer?.types.includes("Files")) {
        e.preventDefault();
        setIsWindowDrag(true);
      }
    };
    const onDragLeave = (e: DragEvent) => {
      if ((e.target as HTMLElement) === document.documentElement) {
        setIsWindowDrag(false);
      }
    };
    const onDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsWindowDrag(false);
      if (e.dataTransfer?.files?.length) {
        handleFileSelect(e.dataTransfer.files[0] as File);
      }
    };
    window.addEventListener("dragenter", onDragEnter);
    window.addEventListener("dragover", onDragOver);
    window.addEventListener("dragleave", onDragLeave);
    window.addEventListener("drop", onDrop);
    return () => {
      window.removeEventListener("dragenter", onDragEnter);
      window.removeEventListener("dragover", onDragOver);
      window.removeEventListener("dragleave", onDragLeave);
      window.removeEventListener("drop", onDrop);
    };
  }, []);

  const promptPreviewText = (() => {
    if (!selectedSubcategory || !subcategories) return "";
    const sub = subcategories.find(s => s.id === selectedSubcategory);
    if (!sub?.prompts) return "No prompts found for this meeting type.";
    return Object.entries(sub.prompts)
      .map(([k, v]) => `${k}:\n${v}`)
      .join('\n\n---\n\n');
  })();

  const handleCopyPrompt = () => {
    if (!promptPreviewText) return;
    navigator.clipboard.writeText(promptPreviewText).then(() => {
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 1500);
    });
  };

  const handleCategorySelect = (id: string) => {
    if (!form.getValues("mediaFile")) return;
    setSelectedCategory(id);
    setSelectedSubcategory("");
    form.setValue("promptCategory", id, { shouldValidate: true });
    form.setValue("promptSubcategory", "", { shouldValidate: true });
  };
  const handleSubcategorySelect = (id: string) => {
    setSelectedSubcategory(id);
    form.setValue("promptSubcategory", id, { shouldValidate: true });
  };

  return (
    <div className="space-y-8 relative">
      {isWindowDrag && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-background/80 backdrop-blur-sm border-4 border-dashed border-primary/40 pointer-events-none">
          <div className="text-center space-y-4">
            <Upload className="h-16 w-16 mx-auto text-primary animate-bounce" />
            <p className="text-2xl font-semibold bg-gradient-to-r from-primary to-foreground bg-clip-text text-transparent">Drop to Upload</p>
            <p className="text-sm text-muted-foreground">We will auto-detect the file type.</p>
          </div>
        </div>
      )}
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-10">
          <input type="hidden" {...form.register("promptCategory")} />
            <input type="hidden" {...form.register("promptSubcategory")} />
          {/* Hero / Drop Zone */}
          <FormField
            control={form.control}
            name="mediaFile"
            render={({ field }) => (
              <FormItem>
                <div
                  onClick={() => fileInputRef.current?.click()}
                  onDrop={handleDrop}
                  onDragOver={(e) => { e.preventDefault(); setIsWindowDrag(true); }}
                  className={`relative group rounded-xl border border-dashed bg-card px-6 py-12 transition hover:border-primary/50 cursor-pointer ${field.value ? 'border-solid border-primary/50' : ''}`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="audio/*,video/*,image/*,.pdf,.doc,.docx,.txt,.rtf,.srt,.vtt,.json"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) handleFileSelect(f);
                    }}
                    className="hidden"
                  />
                  {!field.value && !showTranscriptInput && (
                    <div className="relative z-10 mx-auto max-w-xl text-center space-y-6">
                      <div className="flex justify-center">
                        <div className="p-6 rounded-2xl bg-primary/10 text-primary ring-1 ring-primary/30 group-hover:scale-105 transform transition">
                          <Upload className="h-10 w-10" />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <h2 className="text-2xl font-bold tracking-tight">Drop your media or click to browse</h2>
                        <p className="text-sm text-muted-foreground">Audio, video, documents, transcripts, images. We will handle conversion automatically.</p>
                      </div>
                      <div className="flex flex-wrap justify-center gap-2 text-xs text-muted-foreground">
                        <span className="px-2 py-1 rounded-full bg-muted/60">MP3</span>
                        <span className="px-2 py-1 rounded-full bg-muted/60">WAV</span>
                        <span className="px-2 py-1 rounded-full bg-muted/60">MP4</span>
                        <span className="px-2 py-1 rounded-full bg-muted/60">DOCX</span>
                        <span className="px-2 py-1 rounded-full bg-muted/60">PDF</span>
                        <span className="px-2 py-1 rounded-full bg-muted/60">TXT</span>
                      </div>
                      <div className="flex flex-col sm:flex-row gap-3 justify-center">
                        <Button type="button" variant="default" className="sm:w-auto w-full">Browse Files</Button>
                        <Button type="button" variant="outline" className="sm:w-auto w-full" onClick={(e) => { e.stopPropagation(); setShowTranscriptInput(true); }}>Paste Transcript</Button>
                      </div>
                    </div>
                  )}
                  {showTranscriptInput && !field.value && (
                    <div className="relative z-10 max-w-2xl mx-auto space-y-4">
                      <Textarea rows={6} value={transcriptText} onChange={(e) => setTranscriptText(e.target.value)} placeholder="Paste transcript text here..." className="resize-none bg-background/70" />
                      <div className="flex gap-2">
                        <Button type="button" onClick={handleTranscriptUpload} disabled={!transcriptText.trim()}>Use Transcript</Button>
                        <Button type="button" variant="outline" onClick={() => { setShowTranscriptInput(false); setTranscriptText(""); }}>Cancel</Button>
                      </div>
                    </div>
                  )}
                  {field.value && (
                    <div className="relative z-10 max-w-3xl mx-auto grid gap-8 md:grid-cols-2 items-start">
                      <div className="space-y-4">
                        <div className="flex items-center gap-4">
                          {renderFileIcon()}
                          <div>
                            <p className="font-semibold text-lg break-all">{field.value.name}</p>
                            <p className="text-xs text-muted-foreground">{(field.value.size / 1024 / 1024).toFixed(2)} MB</p>
                          </div>
                        </div>
                        {renderFileTypeInfo()}
                        <div className="flex flex-wrap gap-2">
                          <Button type="button" size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}>Replace</Button>
                          <Button type="button" size="sm" variant="ghost" onClick={(e) => { e.stopPropagation(); field.onChange(undefined); setFileType(null); setShowTranscriptInput(false); setTranscriptText(""); }}>Remove</Button>
                        </div>
                      </div>
                      <div className="space-y-3 text-sm text-muted-foreground">
                        <p className="font-medium text-foreground">Next Steps</p>
                        <ol className="list-decimal list-inside space-y-1">
                          <li>Select a Service Area</li>
                          <li>Choose Meeting Type</li>
                          <li>Review prompts & Upload</li>
                        </ol>
                      </div>
                    </div>
                  )}
                </div>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Categories */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">1. Service Area</h3>
              <Button type="button" size="sm" variant="outline" onClick={() => refetchCategories()} disabled={isLoadingCategories}>
                <RefreshCcw className="h-4 w-4 mr-2" /> {isLoadingCategories ? 'Refreshing' : 'Refresh'}
              </Button>
            </div>
            
            {(() => {
              const rootCategories = (categories || []).filter(cat => !cat.parent_category_id);
              const childrenByParent: Record<string, Array<any>> = {};
              (categories || []).forEach(cat => {
                const parent = cat.parent_category_id;
                if (parent) {
                  childrenByParent[parent] = childrenByParent[parent] || [];
                  childrenByParent[parent].push(cat);
                }
              });

              // We no longer jump to a separate child section. Instead each root category can expand inline.
              const toggleExpand = (parentId: string) => {
                setExpandedParentCategoryId(cur => cur === parentId ? "" : parentId);
              };

              return (
                <div className="space-y-4">
                  {/* Main Categories */}
                  <div className="space-y-2" role="radiogroup" aria-label="Service Areas">
                    {rootCategories.map(category => {
                      const active = category.id === selectedCategory;
                      const hasChildren = (childrenByParent[category.id]?.length || 0) > 0;
                      const expanded = expandedParentCategoryId === category.id;
                      return (
                        <div key={category.id} className="border rounded-md bg-white/60 dark:bg-card border-border/30 overflow-hidden">
                          <div className={`flex items-start justify-between gap-3 p-4 cursor-pointer transition hover:border-primary/40 ${active ? 'ring-2 ring-primary/30 border-primary' : ''}`}
                               onClick={() => handleCategorySelect(category.id)}
                               role="radio" aria-checked={active}>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium leading-tight flex items-center gap-2">
                                {category.name}
                                {hasChildren && (
                                  <button type="button" onClick={(e) => { e.stopPropagation(); toggleExpand(category.id); }}
                                          className="text-xs rounded px-2 py-0.5 border border-border/40 hover:border-primary/40 hover:text-primary transition">
                                    {expanded ? 'Hide' : 'Show'} subcategories
                                  </button>
                                )}
                              </p>
                              <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                {subcategories?.filter(sub => sub.category_id === category.id).length || 0} meeting types
                                {hasChildren && ` • ${childrenByParent[category.id].length} subcategories`}
                              </p>
                            </div>
                            {active && <Check className="h-4 w-4 text-primary flex-shrink-0" />}
                          </div>
                          {hasChildren && expanded && (
                            <div className="px-4 pb-4">
                              <div className="flex flex-wrap gap-2">
                                {childrenByParent[category.id].map(child => {
                                  const childActive = child.id === selectedCategory;
                                  return (
                                    <button
                                      key={child.id}
                                      type="button"
                                      disabled={!form.getValues('mediaFile')}
                                      onClick={() => handleCategorySelect(child.id)}
                                      className={`px-3 py-1.5 rounded-full text-xs font-medium border transition ${childActive ? 'bg-primary text-primary-foreground border-primary shadow-sm' : 'bg-muted/70 hover:bg-muted border-border/40 hover:border-primary/30 hover:text-foreground text-muted-foreground'} disabled:opacity-50`}
                                    >
                                      {child.name}
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                    {!rootCategories.length && (
                      <div className="text-sm text-muted-foreground">{isLoadingCategories ? 'Loading categories...' : 'No categories found.'}</div>
                    )}
                  </div>
                </div>
              );
            })()}
            <FormMessage />
          </div>

          {/* Subcategories */}
          {selectedCategory && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">2. Meeting Type</h3>
              <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Meeting Type">
                {subcategories?.filter(sub => sub.category_id === selectedCategory).map(sub => {
                  const active = sub.id === selectedSubcategory;
                  return (
                    <button
                      key={sub.id}
                      type="button"
                      onClick={() => handleSubcategorySelect(sub.id)}
                      role="radio"
                      aria-checked={active}
                      className={`px-3 py-1.5 rounded-full text-sm border transition ${active ? 'bg-primary text-primary-foreground border-primary shadow-sm' : 'bg-muted/80 hover:bg-muted/100 border-border/40'}`}
                    >
                      {sub.name}
                    </button>
                  );
                })}
                {!subcategories?.filter(sub => sub.category_id === selectedCategory).length && (
                  <span className="text-sm text-muted-foreground">No meeting types.</span>
                )}
              </div>
            </div>
          )}

          {/* Prompt Preview */}
          {selectedSubcategory && (
            <div className="space-y-3">
              <button type="button" onClick={() => setPromptPreviewOpen(o => !o)} className="w-full flex items-center justify-between rounded-lg border border-border/40 bg-background/60 backdrop-blur px-4 py-3 text-left hover:border-primary/40 transition">
                <div>
                  <p className="font-medium">3. Prompt Preview</p>
                  <p className="text-xs text-muted-foreground">These prompts will shape the AI analysis.</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="outline" size="sm" disabled={!promptPreviewText} onClick={(e) => { e.stopPropagation(); handleCopyPrompt(); }}>
                    {copiedPrompt ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                  </Button>
                  {promptPreviewOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                </div>
              </button>
              {promptPreviewOpen && (
                <div className="rounded-xl border border-border/40 bg-card p-4 max-h-[260px] overflow-y-auto text-xs whitespace-pre-wrap font-mono leading-relaxed selection:bg-primary/20 shadow-sm">
                  {promptPreviewText || 'No prompts.'}
                </div>
              )}
            </div>
          )}

          {/* Processing Info */}
          {/* You can add a processing info component here if needed, or remove this block */}
          <div className="pt-4">
            <Button
              type="submit"
              disabled={isUploading || isSubmitting || !form.getValues('mediaFile') || !selectedCategory || !selectedSubcategory || isConverting}
              className="w-full h-14 text-base font-medium shadow-lg rounded-xl bg-gradient-to-r from-primary to-primary/80 hover:from-primary hover:to-primary focus-visible:ring-primary/50"
            >
              {(isUploading || isSubmitting) ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Processing Upload...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-5 w-5" />
                  Upload & Analyze
                </>
              )}
            </Button>
          </div>
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
