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
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { mediaUploadSchema } from "@/schema/audio-upload.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Loader2, RefreshCcw, Music, FileText } from "lucide-react";
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
  );  const [selectedPrompts, setSelectedPrompts] = useState<Record<string, string>>({});
  const [currentPromptKey, setCurrentPromptKey] = useState<string>("");
  const [currentPromptValue, setCurrentPromptValue] = useState<string>("");
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

const convertToWav = async (file: File): Promise<File> => {
    try {
      setConversionStep("Loading FFmpeg...");
      setConversionProgress(10);
      
      const ffmpeg = await loadFFmpeg();
      
      setConversionStep("Preparing audio file...");
      setConversionProgress(25);
      
      const inputName = file.name;
      const baseName = inputName.replace(/\.[^/.]+$/, "");
      const outputName = `${baseName}.wav`;

      await ffmpeg.writeFile(inputName, await fetchFile(file));

      setConversionStep("Converting to WAV format...");
      setConversionProgress(50);      const ffmpegArgs = [
        "-i", inputName,
        "-acodec", "pcm_s16le",  // Use PCM 16-bit little-endian codec
        "-ar", "16000",          // Sample rate 16kHz (good for speech)
        "-ac", "1",              // Mono audio
        "-y",                    // Overwrite output file
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
        type: "audio/wav",
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
            processedFile = await convertToWav(processedFile);
          
          toast.success("Audio converted to WAV format successfully!");
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
  );  const selectedCategoryData = categories?.find(
    (cat) => cat.category_id === selectedCategory,
  );

  const selectedSubcategoryData = selectedCategoryData?.subcategories.find(
    (subcat) => subcat.subcategory_id === selectedSubcategory,
  );  // Update selected prompts when subcategory changes
  useEffect(() => {
    if (selectedSubcategoryData?.prompts) {
      console.log("Setting prompts:", selectedSubcategoryData.prompts);
      setSelectedPrompts(selectedSubcategoryData.prompts);
      // Set the first prompt as default if available
      const promptKeys = Object.keys(selectedSubcategoryData.prompts);
      const firstPromptKey = promptKeys[0];
      if (firstPromptKey) {
        console.log("Setting first prompt key:", firstPromptKey);
        setCurrentPromptKey(firstPromptKey);
        setCurrentPromptValue(selectedSubcategoryData.prompts[firstPromptKey]);
      }
    } else {
      console.log("No prompts found, clearing");
      setSelectedPrompts({});
      setCurrentPromptKey("");
      setCurrentPromptValue("");
    }
  }, [selectedSubcategoryData]);

  // Update current prompt value when prompt key changes
  useEffect(() => {
    if (currentPromptKey && selectedPrompts[currentPromptKey]) {
      console.log("Updating current prompt value for key:", currentPromptKey);
      setCurrentPromptValue(selectedPrompts[currentPromptKey]);
    }
  }, [currentPromptKey, selectedPrompts]);

  // Debug logging
  console.log("selectedPrompts:", selectedPrompts);
  console.log("selectedPrompts keys length:", Object.keys(selectedPrompts).length);
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
            />            <FormField
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
            />            {/* Editable Prompt Section */}
            {Object.keys(selectedPrompts).length > 0 && (
              <div className="space-y-4 border-2 border-blue-300 p-4 rounded-lg bg-blue-50">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold">Edit Selected Prompt</h3>
                </div>
                
                {/* Debug info */}
                <div className="text-xs text-blue-600 bg-white p-2 rounded border">
                  <p>Debug - Current prompt key: "{currentPromptKey}"</p>
                  <p>Debug - Current prompt value length: {currentPromptValue.length}</p>
                  <p>Debug - Available prompt keys: {Object.keys(selectedPrompts).join(", ")}</p>
                </div>
                
                <div className="grid gap-4">
                  {/* Prompt Selector */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Select Prompt to Edit:</label>
                    <Select
                      value={currentPromptKey}
                      onValueChange={(value) => {
                        console.log("Prompt selector changed to:", value);
                        setCurrentPromptKey(value);
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Choose a prompt to edit" />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.keys(selectedPrompts).map((promptKey) => (
                          <SelectItem key={promptKey} value={promptKey}>
                            {promptKey.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  
                  {/* Show if currentPromptKey exists */}
                  <div className="text-xs text-blue-600">
                    {currentPromptKey ? `✅ Current prompt key exists: ${currentPromptKey}` : "❌ No current prompt key set"}
                  </div>
                  
                  {/* Editable Text Area - Always show for debugging */}
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Edit {currentPromptKey ? currentPromptKey.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase()) : "No Prompt Selected"} Prompt:
                    </label>
                    <Textarea
                      value={currentPromptValue}
                      onChange={(e) => {
                        console.log("Textarea changed, new value length:", e.target.value.length);
                        setCurrentPromptValue(e.target.value);
                        // Update the selectedPrompts state with the new value
                        if (currentPromptKey) {
                          setSelectedPrompts(prev => ({
                            ...prev,
                            [currentPromptKey]: e.target.value
                          }));
                        }
                      }}
                      className="min-h-[200px] resize-vertical border-2 border-green-300"
                      placeholder={currentPromptKey ? "Enter your custom prompt here..." : "Select a prompt above to edit"}
                      disabled={!currentPromptKey}
                    />
                    <p className="text-xs text-muted-foreground">
                      This prompt will be used for analysis. You can modify it to better suit your needs.
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Prompt Display Area */}
            {Object.keys(selectedPrompts).length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <h3 className="text-lg font-semibold">All Analysis Configuration Prompts</h3>
                </div>                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-1">
                  {Object.entries(selectedPrompts).map(([promptKey, promptValue]) => (
                    <Card key={promptKey} className={`w-full ${currentPromptKey === promptKey ? 'ring-2 ring-primary' : ''}`}>
                      <CardHeader className="pb-3">
                        <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wide flex justify-between items-center">
                          {promptKey.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                          {currentPromptKey === promptKey && (
                            <span className="text-xs bg-primary text-primary-foreground px-2 py-1 rounded">
                              Currently Editing
                            </span>
                          )}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <Textarea
                          value={promptValue}
                          readOnly
                          className="min-h-[120px] resize-none bg-muted/50 text-sm leading-relaxed"
                          placeholder="No prompt content available"
                        />
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            )}            {/* Debug: Always visible test area */}
            <div className="space-y-4 border-2 border-dashed border-orange-300 p-4 rounded-lg bg-orange-50">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-orange-600" />
                <h3 className="text-lg font-semibold text-orange-800">DEBUG: Prompt Display Test</h3>
              </div>
              <p className="text-sm text-orange-700">
                Selected prompts count: {Object.keys(selectedPrompts).length}
              </p>
              <p className="text-sm text-orange-700">
                Selected category: {selectedCategory || "None"}
              </p>
              <p className="text-sm text-orange-700">
                Selected subcategory: {selectedSubcategory || "None"}
              </p>
              <p className="text-sm text-orange-700">
                Current prompt key: {currentPromptKey || "None"}
              </p>
              <p className="text-sm text-orange-700">
                Current prompt length: {currentPromptValue.length} characters
              </p>
              {Object.keys(selectedPrompts).length > 0 && (
                <div className="space-y-2">
                  <p className="text-sm font-medium text-orange-800">Available prompts:</p>
                  {Object.entries(selectedPrompts).map(([key, value]) => (
                    <div key={key} className="text-xs text-orange-600 bg-white p-2 rounded border">
                      <strong>{key}:</strong> {value.substring(0, 100)}...
                    </div>
                  ))}
                </div>
              )}
            </div><Button
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
        <DialogHeader>          <DialogTitle className="flex items-center gap-2">
            <Music className="h-5 w-5 text-primary" />
            Converting Audio to WAV
          </DialogTitle>
          <DialogDescription>
            Please wait while we convert your audio file to WAV format for processing.
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
