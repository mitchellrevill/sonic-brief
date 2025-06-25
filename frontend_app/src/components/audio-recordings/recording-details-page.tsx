import type { AudioRecording } from "@/api/audio-recordings";
import { StatusBadge } from "@/components/ui/status-badge";
import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Slider } from "@/components/ui/slider";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { useAudioPlayer } from "@/hooks/use-audio-player";
import { getAudioTranscriptionQuery } from "@/queries/audio-recordings.query";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { toast } from "sonner";
import { AnalysisRefinementChat } from "@/components/analysis-refinement/analysis-refinement-chat";
import { FloatingAnalysisChat } from "@/components/analysis-refinement/floating-analysis-chat";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { fetchCategories, fetchSubcategories } from "@/api/prompt-management";
import { isAudioFile, getFileNameFromPath } from "@/lib/file-utils";
import {
  ArrowLeft,
  Download,
  FileAudio,
  FileText,
  Pause,
  Play,
  RefreshCw,
  Tag,
  User,
  Volume2,
  VolumeX,
  Copy,
  Clock,
  Hash,
  Loader2,
  AlertCircle,
  CheckCircle,
  MessageSquare,
  Trash2,
} from "lucide-react";
import { JobShareDialog } from "./job-share-dialog";
import { JobSharingInfo } from "./job-sharing-info";
import { JobDeleteDialog } from "./job-delete-dialog";
import { useState, useEffect } from "react";

interface ExtendedAudioRecording extends AudioRecording {
  analysis_text?: string;
  file_name?: string;
}

interface RecordingDetailsPageProps {
  recording: ExtendedAudioRecording;
}

// Helper function to copy text to clipboard
const copyToClipboard = async (text: string, label: string = "Text") => {
  try {
    await navigator.clipboard.writeText(text);
    toast.success(`${label} copied to clipboard!`);
  } catch (err) {
    console.error('Failed to copy text: ', err);
    toast.error(`Failed to copy ${label.toLowerCase()}`);
  }
};

export function RecordingDetailsPage({ recording }: RecordingDetailsPageProps) {
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);// Check if audio file exists and is a valid audio format
  const hasAudioFile = Boolean(recording.file_path) && isAudioFile(recording.file_path);
  
  // Debug file type detection
  useEffect(() => {
    if (recording.file_path) {
      console.log('File path:', recording.file_path);
      console.log('Is audio file:', isAudioFile(recording.file_path));
      console.log('Has audio file:', hasAudioFile);
    }
  }, [recording.file_path, hasAudioFile]);
  
  // Debug file type detection
  useEffect(() => {
    if (recording.file_path) {
      const urlPath = recording.file_path.split('?')[0];
      const ext = urlPath.split('.').pop()?.toLowerCase() || '';
      console.log('File extension detected:', ext);
      console.log('Is audio file:', isAudioFile(recording.file_path));
      console.log('Has audio file:', hasAudioFile);
    }
  }, [recording.file_path, hasAudioFile]);

  const { 
    data: transcriptionText, 
    refetch: refetchTranscription,
    isLoading: isLoadingTranscription,
    isError: isTranscriptionError,
    error: transcriptionError,
    isFetching: isFetchingTranscription
  } = useQuery(
    getAudioTranscriptionQuery(recording.id),
  );

  // Fetch categories and subcategories for friendly name lookup
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: fetchCategories,
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const { data: subcategories = [] } = useQuery({
    queryKey: ['subcategories'],
    queryFn: () => fetchSubcategories(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Helper functions to get friendly names
  const getCategoryName = (categoryId: string | null | undefined): string => {
    if (!categoryId) return "N/A";
    const category = categories.find(cat => cat.id === categoryId);
    return category?.name || categoryId;
  };

  const getSubcategoryName = (subcategoryId: string | null | undefined): string => {
    if (!subcategoryId) return "N/A";
    const subcategory = subcategories.find(sub => sub.id === subcategoryId);
    return subcategory?.name || subcategoryId;
  };

  // Handle download with feedback
  const handleDownload = (url: string, fileName: string) => {
    try {
      window.open(url, "_blank");
      toast.success(`${fileName} download started`);
    } catch (error) {
      toast.error(`Failed to download ${fileName}`);
    }
  };
  // Only initialize audio player if file path exists
  const {
    audioRef,
    isPlaying,
    isMuted,
    currentTime,
    duration,
    displayVolume,
    togglePlayPause,
    toggleMute,
    handleTimeSliderChange,
    handleVolumeSliderChange,
    formattedCurrentTime,
    formattedDuration,
  } = useAudioPlayer(hasAudioFile ? recording.file_path : '');  const fileName = recording.file_name || 
    (recording.file_path ? getFileNameFromPath(recording.file_path) : null) || 
    "Unnamed Recording";

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      {/* Header Section */}
      <div className="border-b border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <Link to="/audio-recordings">
                <Button
                  variant="outline"
                  size="icon"
                  className="hover:bg-muted"
                >
                  <ArrowLeft className="h-4 w-4" />
                </Button>
              </Link>
              <div className="min-w-0">                <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                  {fileName}
                </h1>
                <SmartBreadcrumb
                  items={[
                    { label: "Audio Recordings", to: "/audio-recordings" },
                    { label: recording.id, isCurrentPage: true }
                  ]}
                  className="text-muted-foreground text-sm"
                  maxItems={4}
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge 
                status={recording.status as any}
                size="md"
                showIcon={true}
                animate={recording.status === "processing"}
              />
            </div>
          </div>
        </div>
      </div>      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Audio Player & Metadata */}
          <div className="lg:col-span-2 space-y-6">
            {/* Enhanced Audio Player Card - Only shown when audio file exists */}
            {hasAudioFile && (
              <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2">
                    <span className="bg-primary/10 rounded-full p-2">
                      <FileAudio className="text-primary h-5 w-5" />
                    </span>
                    Audio Player
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <audio
                    ref={audioRef}
                    src={recording.file_path}
                    preload="metadata"
                    className="hidden"
                  />

                  {/* Enhanced Audio Player Interface */}
                  <div className="bg-gradient-to-r from-muted/50 to-muted/30 rounded-xl p-6 space-y-4">
                    {/* Main Controls Row */}
                    <div className="flex items-center gap-4">
                      <Button
                        size="icon"
                        className="bg-primary text-primary-foreground hover:bg-primary/90 h-12 w-12 rounded-full shadow-lg transition-all duration-200 hover:scale-105"
                        onClick={togglePlayPause}
                      >
                        {isPlaying ? (
                          <Pause className="h-5 w-5" />
                        ) : (
                          <Play className="h-5 w-5 ml-0.5" />
                        )}
                      </Button>

                      <div className="flex-1 space-y-2">
                        <Slider
                          value={[currentTime]}
                          max={duration || 100}
                          step={1}
                          className="cursor-pointer"
                          onValueChange={handleTimeSliderChange}
                        />
                        <div className="flex justify-between text-sm text-muted-foreground">
                          <span className="font-mono">{formattedCurrentTime}</span>
                          <span className="font-mono">{formattedDuration}</span>
                        </div>
                      </div>
                    </div>                    {/* Volume Controls */}
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                      <div className="flex items-center gap-2">
                        <Button 
                          variant="ghost" 
                          size="icon" 
                          onClick={toggleMute}
                          className="h-8 w-8"
                        >
                          {isMuted ? (
                            <VolumeX className="h-4 w-4" />
                          ) : (
                            <Volume2 className="h-4 w-4" />
                          )}
                        </Button>
                        <Slider
                          value={[displayVolume]}
                          max={100}
                          step={1}
                          className="w-24 cursor-pointer"
                          onValueChange={handleVolumeSliderChange}
                        />
                        <span className="text-sm text-muted-foreground w-8">
                          {Math.round(displayVolume)}%
                        </span>
                      </div>
                      <Button
                        variant="outline"
                        onClick={() => handleDownload(recording.file_path, "Audio file")}
                        className="hover:bg-muted w-full sm:w-auto"
                      >
                        <Download className="mr-2 h-4 w-4" />
                        Download
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Tabs for Transcription and Analysis */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm">
              <Tabs defaultValue="transcription" className="w-full">                <CardHeader className="pb-4">
                  <div className="flex items-center justify-between">
                    <TabsList className="grid grid-cols-2 w-full max-w-md">
                      <TabsTrigger value="transcription" className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Transcription
                      </TabsTrigger>
                      <TabsTrigger value="analysis" className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        Analysis
                      </TabsTrigger>
                    </TabsList>
                    {transcriptionText && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => refetchTranscription()}
                        disabled={isFetchingTranscription}
                        className="ml-2"
                      >
                        {isFetchingTranscription ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <RefreshCw className="h-4 w-4" />
                        )}
                      </Button>
                    )}
                  </div>
                </CardHeader><CardContent>                  <TabsContent value="transcription" className="mt-0 space-y-4">
                    {isLoadingTranscription || isFetchingTranscription ? (
                      <div className="flex flex-col items-center justify-center py-12 space-y-4 animate-in fade-in duration-500">
                        <div className="rounded-full bg-primary/10 p-3 animate-pulse">
                          <Loader2 className="h-6 w-6 text-primary animate-spin" />
                        </div>
                        <div className="text-center space-y-2">
                          <h3 className="font-medium">Loading transcription...</h3>
                          <p className="text-sm text-muted-foreground">
                            Please wait while we fetch the transcription data
                          </p>
                        </div>
                      </div>                    ) : isTranscriptionError ? (
                      <div className="flex flex-col items-center justify-center py-12 space-y-4 animate-in fade-in duration-500">
                        <div className="rounded-full bg-destructive/10 p-3 animate-pulse">
                          <AlertCircle className="h-6 w-6 text-destructive" />
                        </div>
                        <div className="text-center space-y-2">
                          <h3 className="font-medium">Failed to load transcription</h3>
                          <p className="text-sm text-muted-foreground">
                            {transcriptionError instanceof Error 
                              ? transcriptionError.message 
                              : "There was an error loading the transcription"
                            }
                          </p>
                        </div>
                        <Button 
                          onClick={() => refetchTranscription()}
                          variant="outline"
                          disabled={isFetchingTranscription}
                          className="transition-all duration-200 hover:scale-105"
                        >
                          {isFetchingTranscription ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Retrying...
                            </>
                          ) : (
                            <>
                              <RefreshCw className="mr-2 h-4 w-4" />
                              Try Again
                            </>
                          )}
                        </Button>
                      </div>                    ) : transcriptionText ? (
                      <div className="animate-in slide-in-from-bottom duration-700">
                        <div className="space-y-2">
                          <div className="flex items-center gap-2 text-sm text-muted-foreground animate-in fade-in duration-500 delay-200">
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span>Transcription loaded successfully</span>
                          </div>                          <div className="rounded-lg bg-muted/50 p-4 h-[600px] lg:h-[700px] xl:h-[800px] overflow-y-auto border border-border/50 animate-in fade-in duration-500 delay-300">
                            <pre className="text-sm whitespace-pre-wrap font-sans leading-relaxed">
                              {transcriptionText}
                            </pre>
                          </div>
                        </div>                        {recording.transcription_file_path && (
                          <Button
                            onClick={() => handleDownload(recording.transcription_file_path!, "Transcription")}
                            variant="outline"
                            className="w-full transition-all duration-200 hover:scale-105 animate-in fade-in duration-500 delay-400"
                          >
                            <Download className="mr-2 h-4 w-4" />
                            Download Transcription
                          </Button>
                        )}
                      </div>                    ) : (
                      <div className="flex flex-col items-center justify-center py-12 space-y-4 animate-in fade-in duration-500">
                        <div className="rounded-full bg-muted p-3">
                          <FileText className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <div className="text-center space-y-2">
                          <h3 className="font-medium">No transcription available</h3>
                          <p className="text-sm text-muted-foreground">
                            Click below to load the transcription data
                          </p>
                        </div>
                        <Button 
                          onClick={() => refetchTranscription()}
                          disabled={isFetchingTranscription}
                          className="min-w-[120px] transition-all duration-200 hover:scale-105 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70"
                        >
                          {isFetchingTranscription ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Loading...
                            </>
                          ) : (
                            <>
                              <FileText className="mr-2 h-4 w-4" />
                              Load Transcription
                            </>
                          )}
                        </Button>
                      </div>
                    )}
                  </TabsContent>                  <TabsContent value="analysis" className="mt-0 space-y-4">
                    {recording.analysis_text ? (
                      <div className="space-y-6">                        {/* Original Analysis */}
                        <div className="animate-in slide-in-from-bottom duration-700">                          <div className="rounded-lg bg-muted/50 p-4 h-[600px] lg:h-[700px] xl:h-[800px] overflow-y-auto space-y-4 border border-border/50">
                            {recording.analysis_text
                              .split("\n\n")
                              .map((section: string, index: number) => {
                                const lines = section.split("\n");
                                const title = lines[0];
                                const content = lines.slice(1);

                                return (
                                  <div key={index} className="space-y-2 animate-in fade-in duration-500" style={{ animationDelay: `${index * 100}ms` }}>
                                    <h4 className="font-semibold text-foreground">
                                      {title}
                                    </h4>
                                    <ul className="list-disc list-inside text-sm text-muted-foreground space-y-1 ml-4">
                                      {content.map((point: string, subIndex: number) => (
                                        <li key={subIndex}>{point}</li>
                                      ))}
                                    </ul>
                                  </div>
                                );
                              })}
                          </div>

                          {recording.analysis_file_path && (
                            <Button
                              onClick={() => handleDownload(recording.analysis_file_path!, "Analysis PDF")}
                              variant="outline"
                              className="w-full transition-all duration-200 hover:scale-105 animate-in fade-in duration-500 delay-300"
                            >
                              <Download className="mr-2 h-4 w-4" />
                              Download Analysis PDF
                            </Button>                          )}
                        </div>

                        {/* Analysis Refinement Chat removed - moved to sidebar */}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-12 space-y-4 animate-in fade-in duration-500">
                        <div className="rounded-full bg-muted p-3">
                          <FileText className="h-6 w-6 text-muted-foreground" />
                        </div>
                        <div className="text-center space-y-2">
                          <h3 className="font-medium">No analysis available</h3>
                          <p className="text-sm text-muted-foreground">
                            Analysis will appear here once processing is complete
                          </p>
                        </div>
                      </div>
                    )}
                  </TabsContent>
                </CardContent>
              </Tabs>
            </Card>
          </div>          {/* Sidebar with Recording Details */}
          <div className="space-y-6">
            {/* Recording Information Card */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-in slide-in-from-right duration-700">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2">
                  <span className="bg-primary/10 rounded-full p-2">
                    <Tag className="text-primary h-4 w-4" />
                  </span>
                  Recording Details
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Job ID */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <Hash className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">Job ID</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="bg-muted/50 rounded px-2 py-1 text-sm font-mono flex-1 truncate">
                      {recording.id}
                    </code>                    <Button
                      variant="outline"
                      size="icon"
                      className="h-7 w-7 transition-all duration-200 hover:scale-110"
                      onClick={() => copyToClipboard(recording.id, "Job ID")}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                <Separator />                {/* User ID */}
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <User className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">User ID</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="bg-muted/50 rounded px-2 py-1 text-sm font-mono flex-1 truncate">
                      {recording.user_id}
                    </code>                    <Button
                      variant="outline"
                      size="icon"
                      className="h-7 w-7 transition-all duration-200 hover:scale-110"
                      onClick={() => copyToClipboard(recording.user_id, "User ID")}
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>
                </div>

                <Separator />

                {/* Timestamps */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">Timestamps</span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Created:</span>
                      <span className="font-mono">
                        {new Date(recording.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Updated:</span>
                      <span className="font-mono">
                        {new Date(recording.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                  </div>
                </div>

                <Separator />                {/* Categories */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-sm">
                    <Tag className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">Categories</span>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div>
                      <span className="text-muted-foreground block mb-1">Category:</span>
                      <div className="bg-muted/50 rounded px-2 py-1 text-xs break-all">
                        {getCategoryName(recording.prompt_category_id)}
                        {recording.prompt_category_id && getCategoryName(recording.prompt_category_id) !== recording.prompt_category_id && (
                          <span className="text-muted-foreground ml-2">({recording.prompt_category_id})</span>
                        )}
                      </div>
                    </div>
                    <div>
                      <span className="text-muted-foreground block mb-1">Subcategory:</span>
                      <div className="bg-muted/50 rounded px-2 py-1 text-xs break-all">
                        {getSubcategoryName(recording.prompt_subcategory_id)}
                        {recording.prompt_subcategory_id && getSubcategoryName(recording.prompt_subcategory_id) !== recording.prompt_subcategory_id && (
                          <span className="text-muted-foreground ml-2">({recording.prompt_subcategory_id})</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>            {/* Actions Card */}
            <Card className="border-border/50 bg-card/50 backdrop-blur-sm animate-in slide-in-from-right duration-700 delay-200">
              <CardHeader className="pb-4">
                <CardTitle className="flex items-center gap-2">
                  <span className="bg-primary/10 rounded-full p-2">
                    <RefreshCw className="text-primary h-4 w-4" />
                  </span>
                  Actions
                </CardTitle>
              </CardHeader>              <CardContent className="space-y-3">                {hasAudioFile ? (
                  <Button
                    variant="outline"
                    className="w-full justify-start transition-all duration-200 hover:scale-105 hover:bg-muted"
                    onClick={() => handleDownload(recording.file_path, "Audio file")}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download Audio File
                  </Button>
                ) : recording.file_path && (
                  <Button
                    variant="outline"
                    className="w-full justify-start transition-all duration-200 hover:scale-105 hover:bg-muted"
                    onClick={() => handleDownload(recording.file_path, "Source file")}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download Source File
                  </Button>
                )}
                
                {recording.transcription_file_path && (
                  <Button
                    variant="outline"
                    className="w-full justify-start transition-all duration-200 hover:scale-105 hover:bg-muted"
                    onClick={() => handleDownload(recording.transcription_file_path!, "Transcription")}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download Transcription
                  </Button>
                )}
                
                {recording.analysis_file_path && (
                  <Button
                    variant="outline"
                    className="w-full justify-start transition-all duration-200 hover:scale-105 hover:bg-muted"
                    onClick={() => handleDownload(recording.analysis_file_path!, "Analysis PDF")}
                  >
                    <Download className="mr-2 h-4 w-4" />
                    Download Analysis
                  </Button>
                )}

                {/* Analysis Refinement Chat Button - Prominent in Actions */}
                {recording.analysis_text && (
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button 
                        variant="default" 
                        className="w-full justify-start transition-all duration-200 hover:scale-105 bg-gradient-to-r from-primary to-primary/80 hover:from-primary/90 hover:to-primary/70 shadow-md"
                      >
                        <MessageSquare className="mr-2 h-4 w-4" />
                        Chat with Analysis
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-4xl max-h-[90vh] flex flex-col p-0 gap-0">
                      <DialogHeader className="px-6 py-4 border-b bg-muted/30">
                        <DialogTitle className="flex items-center gap-3">
                          <span className="bg-primary/10 rounded-full p-2.5">
                            <MessageSquare className="text-primary h-5 w-5" />
                          </span>
                          <div>
                            <div className="text-lg font-semibold">Refine Your Analysis</div>
                            <p className="text-sm text-muted-foreground font-normal mt-1">
                              Chat with AI to refine and explore your analysis results
                            </p>
                          </div>
                        </DialogTitle>
                      </DialogHeader>
                      
                      <div className="flex-1 min-h-0">
                        <AnalysisRefinementChat 
                          jobId={recording.id}
                          className="border-0 bg-transparent h-full rounded-none"
                        />
                      </div>
                    </DialogContent>
                  </Dialog>
                )}
                
                <div className="pt-2 border-t border-border/50">
                  {/* Secondary Actions */}
                </div>

                {/* Share Button */}
                <Button variant="outline" onClick={() => setShareDialogOpen(true)} className="w-full justify-start transition-all duration-200 hover:scale-105 hover:bg-muted">
                  <User className="mr-2 h-4 w-4" />
                  Share
                </Button>

                {/* Delete Button */}
                <Button 
                  variant="outline" 
                  onClick={() => setDeleteDialogOpen(true)} 
                  className="w-full justify-start transition-all duration-200 hover:scale-105 hover:bg-muted text-destructive hover:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete                </Button>              </CardContent>
            </Card>
          </div>
        </div>
      </div>      {/* Floating Analysis Chat - Mobile/Global Access */}
      <FloatingAnalysisChat 
        jobId={recording.id} 
        hasAnalysis={Boolean(recording.analysis_text)}
      />

      {/* Sharing Info Display - New Component */}
      <JobSharingInfo jobId={recording.id} jobTitle={fileName} />

      {/* Share Dialog - New Component */}
      <JobShareDialog
        isOpen={shareDialogOpen}
        onOpenChange={setShareDialogOpen}
        jobId={recording.id}
        jobTitle={fileName}
      />      {/* Delete Dialog */}
      <JobDeleteDialog
        isOpen={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        jobId={recording.id}
        jobTitle={fileName}
        onDeleteSuccess={() => {
          // Navigate back to the recordings list after successful delete
          window.location.href = "/audio-recordings";
        }}
      />
    </div>
  );
}
