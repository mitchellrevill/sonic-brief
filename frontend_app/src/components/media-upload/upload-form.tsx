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
import { Loader2, RefreshCcw, Upload, FileText, Film, Music, Image, File, ChevronDown, ChevronUp, Copy, Check, Search, Folder, FolderOpen, ChevronRight } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { useEffect, useRef } from "react";
// Removed select dropdown approach; implementing sidebar instead
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
  // Parent category currently expanded to show its child categories (hierarchical folders)
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  // Track search input for categories and meeting types
  const [categorySearch, setCategorySearch] = useState("");
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

  // Watch form values to trigger re-renders when they change
  const formValues = form.watch();

  // Use formValues to ensure component re-renders when form changes
  const currentCategory = formValues.promptCategory;
  const currentSubcategory = formValues.promptSubcategory;

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
      
      // Guard: ensure a media file exists before proceeding. Users can select
      // dropdowns before attaching a file; prevent the submit flow from
      // executing in that case and surface a validation error.
      if (!values.mediaFile) {
        toast.error("Please select or upload a media file before submitting.");
        // Mark form error so UI can reflect it
        form.setError("mediaFile", { type: "manual", message: "Please add a media file." });
        setIsSubmitting(false);
        return;
      }

      // Additional validation guards for category/subcategory
      if (!values.promptCategory) {
        console.warn("No category selected - aborting submit");
        toast.error("Please select a service area before submitting.");
        form.setError("promptCategory", { type: "manual", message: "Please select a service area." });
        setIsSubmitting(false);
        return;
      }

      if (!values.promptSubcategory) {
        console.warn("No subcategory selected - aborting submit");
        toast.error("Please select a meeting type before submitting.");
        form.setError("promptSubcategory", { type: "manual", message: "Please select a meeting type." });
        setIsSubmitting(false);
        return;
      }

      let processedFile = values.mediaFile;
      // Sanitize filename before upload
      if (processedFile) {
        const originalName = processedFile.name;
        const cleanName = sanitizeFilename(originalName);
        if (cleanName !== originalName) {
          processedFile = new (window as any).File([processedFile], cleanName, { 
            type: processedFile.type, 
            lastModified: processedFile.lastModified 
          }) as File;
        }
      }
        // Convert audio and video files to WAV (extract audio from video)
      if (processedFile && (fileType === "audio" || fileType === "video")) {
        
        try {
          setIsConverting(true);
          setConversionProgress(0);
          setConversionStep("Starting conversion...");
          
          processedFile = await convertToWav(processedFile);
          
          toast.success("Media converted to WAV format successfully!");
        } catch (error: unknown) {
          
          toast.error("Media conversion failed. Uploading original file instead.");
          // Use original file when conversion fails
          processedFile = values.mediaFile;
        } finally {
          setIsConverting(false);
          setConversionProgress(0);
          setConversionStep("");
        }
      } else {
        if (processedFile) {
        }
      }

      try {
        await uploadMediaMutation({
          ...values,
          mediaFile: processedFile,
        });

        // Reset form state after successful upload
        form.reset({
          mediaFile: undefined,
          promptCategory: "",
          promptSubcategory: "",
        });
        // Ensure controlled selects and form validation are in sync
        setFileType(null);
        setTranscriptText("");
        setShowTranscriptInput(false);
        setExpandedCategories(new Set()); // Reset expanded categories
        // Clear any lingering errors and re-run validation so form.formState.isValid updates
        form.clearErrors();
        // trigger full form validation update (non-blocking)
        void form.trigger().then(() => {
        });
      } catch (uploadError: unknown) {
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
    // Reset category/subcategory selections when a new file is selected
    // This ensures clean state for each new file
    if (currentCategory || currentSubcategory) {
      form.setValue("promptCategory", "");
      form.setValue("promptSubcategory", "");
      form.clearErrors("promptCategory");
      form.clearErrors("promptSubcategory");
    }
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

    // Set the file in form and trigger validation
    form.setValue("mediaFile", transcriptFile);

    // Reset category/subcategory selections when transcript is uploaded
    if (currentCategory || currentSubcategory) {
      form.setValue("promptCategory", "");
      form.setValue("promptSubcategory", "");
      form.clearErrors("promptCategory");
      form.clearErrors("promptSubcategory");
    }

    // Force form validation
    form.trigger("mediaFile");

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
    if (!currentSubcategory || !subcategories) return "";
    const sub = subcategories.find(s => s.id === currentSubcategory);
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

  const toggleCategory = (categoryId: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId);
      } else {
        newSet.add(categoryId);
      }
      return newSet;
    });
  };

  const handleCategorySelect = (id: string) => {
    if (!formValues.mediaFile) {
      toast.error("Please upload a file before selecting a service area");
      return;
    }
    form.setValue("promptCategory", id);
    form.setValue("promptSubcategory", "");
    // Clear any existing errors for these fields
    form.clearErrors("promptCategory");
    form.clearErrors("promptSubcategory");
    // Trigger validation to update form state
    form.trigger(["promptCategory", "promptSubcategory"]);
    // Auto-expand when selecting a category
    if (!expandedCategories.has(id)) {
      toggleCategory(id);
    }
  };
  
  const handleSubcategorySelect = (id: string) => {
    if (!formValues.mediaFile) {
      toast.error("Please upload a file before selecting a meeting type");
      return;
    }

    // Find the subcategory and auto-select its parent category if not already selected
    const subcategory = subcategories?.find(s => s.id === id);
    if (!subcategory) {
      return;
    }

    const parentCategoryId = subcategory.category_id;
    if (!currentCategory || currentCategory !== parentCategoryId) {
      form.setValue("promptCategory", parentCategoryId);
      form.clearErrors("promptCategory");
      // Auto-expand the parent category
      if (!expandedCategories.has(parentCategoryId)) {
        toggleCategory(parentCategoryId);
      }
    }

    form.setValue("promptSubcategory", id);
    // Clear any existing errors for this field
    form.clearErrors("promptSubcategory");
    // Trigger validation to update form state for both fields
    form.trigger(["promptCategory", "promptSubcategory"]);
  };

  const getSubcategoriesForCategory = (categoryId: string) => {
    return (subcategories || []).filter(sub => sub.category_id === categoryId);
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
                          <Button type="button" size="sm" variant="ghost" onClick={(e) => { 
                            e.stopPropagation(); 
                            field.onChange(undefined); 
                            setFileType(null); 
                            setShowTranscriptInput(false); 
                            setTranscriptText(""); 
                            // Reset category/subcategory selections when file is removed
                            form.setValue("promptCategory", "");
                            form.setValue("promptSubcategory", "");
                            form.clearErrors();
                            void form.trigger();
                          }}>Remove</Button>
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

          {/* Categories & Subcategories (Sidebar Layout) */}
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Service Area & Meeting Type</h3>
              <Button type="button" size="sm" variant="outline" onClick={() => refetchCategories()} disabled={isLoadingCategories}>
                <RefreshCcw className="h-4 w-4 mr-2" /> {isLoadingCategories ? 'Refreshing' : 'Refresh'}
              </Button>
            </div>

            {/* Validation Error Messages */}
            <FormField
              control={form.control}
              name="promptCategory"
              render={({ fieldState }) => (
                <FormItem className="space-y-0">
                  {fieldState.error && (
                    <FormMessage className="text-sm text-destructive">
                      {fieldState.error.message}
                    </FormMessage>
                  )}
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="promptSubcategory"
              render={({ fieldState }) => (
                <FormItem className="space-y-0">
                  {fieldState.error && (
                    <FormMessage className="text-sm text-destructive">
                      {fieldState.error.message}
                    </FormMessage>
                  )}
                </FormItem>
              )}
            />

            <div className="flex gap-6 h-[60vh]">
              {/* Sidebar */}
              <div className={`w-80 border rounded-xl bg-card/60 backdrop-blur-sm flex flex-col overflow-hidden ${!formValues.mediaFile ? 'opacity-50 pointer-events-none' : ''}`}>
                {/* Header */}
                <div className="p-4 border-b border-border">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-semibold text-foreground">Categories & Meeting Types</h4>
                  </div>
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <input
                      type="text"
                      value={categorySearch}
                      onChange={(e) => setCategorySearch(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                        }
                      }}
                      placeholder={isLoadingCategories ? 'Loading...' : !formValues.mediaFile ? 'Upload a file to search categories...' : 'Search categories...'}
                      className="w-full pl-10 pr-4 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50"
                      disabled={isLoadingCategories || !formValues.mediaFile}
                    />
                  </div>
                </div>

                {/* Tree View */}
                <div className="flex-1 overflow-y-auto p-2">
                  {!formValues.mediaFile && (
                    <div className="p-4 text-sm text-muted-foreground text-center">
                      <div className="space-y-2">
                        <Upload className="h-8 w-8 mx-auto text-gray-400" />
                        <p>Upload a file first to access service areas and meeting types.</p>
                      </div>
                    </div>
                  )}

                  {(() => {
                    const allCats = categories || [];
                    const rootCategories = allCats.filter(cat => !cat.parent_category_id).sort((a, b) => a.name.localeCompare(b.name));
                    const childrenByParent: Record<string, any[]> = {};
                    
                    allCats.forEach(cat => {
                      if (cat.parent_category_id) {
                        childrenByParent[cat.parent_category_id] = childrenByParent[cat.parent_category_id] || [];
                        childrenByParent[cat.parent_category_id].push(cat);
                      }
                    });

                    // Sort children alphabetically too
                    Object.keys(childrenByParent).forEach(parentId => {
                      childrenByParent[parentId].sort((a, b) => a.name.localeCompare(b.name));
                    });

                    const normalizedSearch = categorySearch.trim().toLowerCase();
                    const filteredRoots = normalizedSearch
                      ? rootCategories.filter(r => 
                          r.name.toLowerCase().includes(normalizedSearch) || 
                          (childrenByParent[r.id] || []).some(ch => ch.name.toLowerCase().includes(normalizedSearch))
                        )
                      : rootCategories;

                    return (
                      <div className="space-y-0.5">
                        {filteredRoots.map((category) => {
                          const categoryId = category.id;
                          const isExpanded = expandedCategories.has(categoryId);
                          const isSelected = currentCategory === categoryId;
                          const subcats = getSubcategoriesForCategory(categoryId).sort((a, b) => a.name.localeCompare(b.name));
                          const childCats = (childrenByParent[categoryId] || []).filter(child => 
                            !normalizedSearch || child.name.toLowerCase().includes(normalizedSearch)
                          );

                          return (
                            <div key={categoryId} className="select-none">
                              <div
                                className={`flex items-center px-3 py-2 rounded-lg cursor-pointer transition-all duration-200 group ${
                                  isSelected
                                    ? "bg-gray-100 dark:bg-gray-900/50 text-gray-700 dark:text-gray-300 shadow-sm"
                                    : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                                }`}
                              >
                                <button
                                  type="button"
                                  className="mr-2 p-1 rounded-md hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleCategory(categoryId);
                                  }}
                                >
                                  {subcats.length + childCats.length > 0 ? (
                                    isExpanded ? (
                                      <ChevronDown className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                                    ) : (
                                      <ChevronRight className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                                    )
                                  ) : (
                                    <div className="h-3.5 w-3.5" />
                                  )}
                                </button>

                                <div 
                                  className="flex items-center flex-1 min-w-0"
                                  onClick={() => handleCategorySelect(categoryId)}
                                >
                                  {isExpanded ? (
                                    <FolderOpen className="h-4 w-4 mr-3 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                                  ) : (
                                    <Folder className="h-4 w-4 mr-3 text-gray-600 dark:text-gray-400 flex-shrink-0" />
                                  )}

                                  <span className="flex-1 font-medium text-sm truncate">{category.name}</span>

                                  <span className="text-xs bg-gray-100 dark:bg-gray-900/50 text-gray-600 dark:text-gray-400 px-2 py-1 rounded-full ml-3 flex-shrink-0">
                                    {subcats.length + childCats.length}
                                  </span>
                                </div>
                              </div>

                              {isExpanded && (
                                <div className="ml-6 mt-2 space-y-1 border-l-2 border-gray-200 dark:border-gray-700 pl-4">
                                  {/* Child categories (folders) */}
                                  {childCats.map((child) => {
                                    const childId = child.id;
                                    const isChildSelected = currentCategory === childId;
                                    const isChildExpanded = expandedCategories.has(childId);
                                    const childSubcats = getSubcategoriesForCategory(childId).sort((a, b) => a.name.localeCompare(b.name));

                                    return (
                                      <div key={childId} className="select-none">
                                        <div
                                          className={`flex items-center px-3 py-1.5 rounded-md cursor-pointer transition-all duration-200 group ${
                                            isChildSelected ? "bg-gray-50 dark:bg-gray-900/30 text-gray-600 dark:text-gray-400 shadow-sm" : "hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-600 dark:text-gray-400"
                                          }`}
                                        >
                                          <button
                                            type="button"
                                            className="mr-2 p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                                            onClick={(e) => {
                                              e.stopPropagation();
                                              toggleCategory(childId);
                                            }}
                                          >
                                            {childSubcats.length > 0 ? (
                                              isChildExpanded ? (
                                                <ChevronDown className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                                              ) : (
                                                <ChevronRight className="h-3.5 w-3.5 text-gray-500 dark:text-gray-400" />
                                              )
                                            ) : (
                                              <div className="h-3.5 w-3.5" />
                                            )}
                                          </button>

                                          <div 
                                            className="flex items-center flex-1 min-w-0"
                                            onClick={() => handleCategorySelect(childId)}
                                          >
                                            <Folder className="h-4 w-4 mr-3 text-gray-500 dark:text-gray-400 flex-shrink-0" />
                                            <span className="flex-1 text-sm truncate">{child.name}</span>
                                            <span className="text-xs bg-gray-100 dark:bg-gray-900/50 text-gray-600 dark:text-gray-400 px-2 py-1 rounded-full ml-3 flex-shrink-0">
                                              {childSubcats.length}
                                            </span>
                                          </div>
                                        </div>

                                        {/* Meeting types under child category */}
                                        {isChildExpanded && childSubcats.length > 0 && (
                                          <div className="ml-4 mt-2 space-y-1">
                                            {childSubcats.map((subcategory) => {
                                              const subId = subcategory.id;
                                              const isSubSelected = currentSubcategory === subId;

                                              return (
                                                <div
                                                  key={subId}
                                                  className={`flex items-center px-3 py-1.5 rounded-md cursor-pointer transition-all duration-200 ${
                                                    isSubSelected ? 
                                                      "bg-primary/10 dark:bg-primary/20 text-primary dark:text-primary shadow-sm" : 
                                                      "hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-600 dark:text-gray-400"
                                                  }`}
                                                  onClick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    handleSubcategorySelect(subId);
                                                  }}
                                                >
                                                  <FileText className="h-4 w-4 mr-3 text-primary dark:text-primary flex-shrink-0" />
                                                  <span className="flex-1 text-sm truncate">{subcategory.name}</span>
                                                </div>
                                              );
                                            })}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}

                                  {/* Meeting types directly under root category */}
                                  {subcats.length > 0 && (
                                    <div className="space-y-1">
                                      {subcats.map((subcategory) => {
                                        const subId = subcategory.id;
                                        const isSubSelected = currentSubcategory === subId;

                                        return (
                                          <div
                                            key={subId}
                                            className={`flex items-center px-3 py-1.5 rounded-md cursor-pointer transition-all duration-200 ${
                                              isSubSelected ? 
                                                "bg-primary/10 dark:bg-primary/20 text-primary dark:text-primary shadow-sm" : 
                                                "hover:bg-gray-50 dark:hover:bg-gray-800/50 text-gray-600 dark:text-gray-400"
                                            }`}
                                            onClick={(e) => {
                                              e.preventDefault();
                                              e.stopPropagation();
                                              handleSubcategorySelect(subId);
                                            }}
                                          >
                                            <FileText className="h-4 w-4 mr-3 text-primary dark:text-primary flex-shrink-0" />
                                            <span className="flex-1 text-sm truncate">{subcategory.name}</span>
                                          </div>
                                        );
                                      })}
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                        
                        {filteredRoots.length === 0 && (
                          <div className="p-4 text-sm text-muted-foreground text-center">
                            No categories match "{categorySearch}"
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-border">
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    {(categories || []).length} folders • {(subcategories || []).length} meeting types
                  </div>
                </div>
              </div>

              {/* Main Content Area */}
              <div className="flex-1 h-[60vh] overflow-hidden">
                {!formValues.mediaFile && (
                  <div className="h-full flex items-center justify-center border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                    <div className="text-center space-y-2">
                      <Upload className="h-12 w-12 mx-auto text-gray-400" />
                      <p className="text-gray-500 dark:text-gray-400">Upload a file first to select service areas and meeting types</p>
                    </div>
                  </div>
                )}

                {formValues.mediaFile && !currentCategory && !currentSubcategory && (
                  <div className="h-full flex items-center justify-center border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                    <div className="text-center space-y-2">
                      <Folder className="h-12 w-12 mx-auto text-gray-400" />
                      <p className="text-gray-500 dark:text-gray-400">Select a service area and meeting type from the sidebar</p>
                    </div>
                  </div>
                )}

                {formValues.mediaFile && currentCategory && !currentSubcategory && (
                  <div className="h-full flex items-center justify-center border-2 border-dashed border-gray-200 dark:border-gray-700 rounded-xl">
                    <div className="text-center space-y-2">
                      <FileText className="h-12 w-12 mx-auto text-gray-400" />
                      <p className="text-gray-500 dark:text-gray-400">Choose a meeting type to continue</p>
                    </div>
                  </div>
                )}

                {formValues.mediaFile && currentCategory && currentSubcategory && (
                  <div className="h-full border rounded-xl bg-card/60 backdrop-blur-sm p-6 flex flex-col">
                    <div className="flex-1 space-y-4 overflow-hidden">
                      <div>
                        <h4 className="font-semibold text-lg mb-2">Selection Summary</h4>
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Folder className="h-4 w-4 text-gray-500" />
                            <span className="text-sm"><strong>Service Area:</strong> {categories?.find(c => c.id === currentCategory)?.name}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <FileText className="h-4 w-4 text-primary" />
                            <span className="text-sm"><strong>Meeting Type:</strong> {subcategories?.find(s => s.id === currentSubcategory)?.name}</span>
                          </div>
                        </div>
                      </div>

                      {/* Prompt Preview inline underneath selection */}
                      <div className="flex-1 border-t pt-4 min-h-0">
                        <div className="flex items-center justify-between mb-2">
                          <div>
                            <p className="font-medium">Prompt Preview</p>
                            <p className="text-xs text-muted-foreground">These prompts will shape the AI analysis.</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button type="button" variant="outline" size="sm" disabled={!promptPreviewText} onClick={(e) => { e.stopPropagation(); handleCopyPrompt(); }}>
                              {copiedPrompt ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                            </Button>
                            <button type="button" onClick={() => setPromptPreviewOpen(o => !o)} className="p-2 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
                              {promptPreviewOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                            </button>
                          </div>
                        </div>
                        {promptPreviewOpen && (
                          <div className="h-full rounded-xl border border-border/40 bg-card p-3 overflow-y-auto text-xs whitespace-pre-wrap font-mono leading-relaxed selection:bg-primary/20 shadow-sm">
                            {promptPreviewText || 'No prompts.'}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>



          {/* Processing Info */}
          {/* You can add a processing info component here if needed, or remove this block */}
          <div className="pt-4">
            <Button
              type="submit"
              disabled={isUploading || isSubmitting || !formValues.mediaFile || !currentCategory || !currentSubcategory || isConverting}
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
