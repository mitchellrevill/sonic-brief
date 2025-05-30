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
    if (!ffmpegRef.current) {
      const ffmpeg = new FFmpeg();
      
      await ffmpeg.load();
      
      ffmpegRef.current = ffmpeg;
    }
    return ffmpegRef.current;
  };

const convertToWebm = async (file: File): Promise<File> => {
    try {
      setConversionStep("Loading FFmpeg...");
      setConversionProgress(10);
      
      const ffmpeg = await loadFFmpeg();
      
      setConversionStep("Preparing audio file...");
      setConversionProgress(25);
      
      const inputName = file.name;
      const baseName = inputName.replace(/\.[^/.]+$/, "");
      const outputName = `${baseName}.webm`;

      await ffmpeg.writeFile(inputName, await fetchFile(file));

      setConversionStep("Converting to WebM format...");
      setConversionProgress(50);      const ffmpegArgs = [
        "-i", inputName,
        "-c:a", "libopus",  // Use Opus codec for audio
        "-b:a", "128k",     // Audio bitrate
        "-ac", "1",         // Mono audio
        "-y",               // Overwrite output file
        outputName,
      ];
      
      await ffmpeg.exec(ffmpegArgs);
      
      setConversionStep("Finalizing conversion...");
      setConversionProgress(85);      const data = await ffmpeg.readFile(outputName);
      const dataSize = data instanceof Uint8Array ? data.byteLength : data.length;
      
      if (dataSize === 0) {
        throw new Error("Output file is empty");
      }

      await ffmpeg.deleteFile(inputName);
      await ffmpeg.deleteFile(outputName);      setConversionProgress(100);
      
      // Create a proper File object directly from the converted data
      const convertedFile = new File([data], outputName, {
        type: "audio/webm",
        lastModified: Date.now(),
      });
      
      return convertedFile;} catch (error: unknown) {
      // Reset conversion UI state
      setConversionStep("");
      setConversionProgress(0);
      
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
      let processedFile = values.mediaFile;
      if (processedFile && typeof processedFile !== "string") {
        try {
          setIsConverting(true);
          setConversionProgress(0);
          setConversionStep("Starting conversion...");
          
          processedFile = await convertToWebm(processedFile);
          
          toast.success("Audio converted to WebM format successfully!");
        } catch (error: unknown) {
          toast.error("Audio conversion failed. Uploading original file instead.");
          // Use original file when conversion fails
          processedFile = values.mediaFile;
        } finally {
          setIsConverting(false);
          setConversionProgress(0);
          setConversionStep("");
        }
      }
        try {
        await uploadAudioMutation({
          ...values,
          mediaFile: processedFile,
        });
        
      } catch (uploadError: unknown) {
        throw uploadError; // Re-throw to let the mutation handle it
      }
      
      form.reset({
        mediaFile: undefined,
        promptCategory: "",
        promptSubcategory: "",
      });
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
