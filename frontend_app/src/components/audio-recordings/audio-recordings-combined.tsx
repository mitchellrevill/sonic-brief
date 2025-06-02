import type { AudioListValues } from "@/schema/audio-list.schema";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { isAudioFile, getFileNameFromPath, isWellSupportedAudioFormat } from "@/lib/file-utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { StatusBadge } from "@/components/ui/status-badge";
import { MiniAudioPlayer } from "@/components/ui/mini-audio-player";
import { FormatWarningDialog } from "@/components/ui/format-warning-dialog";
import { AudioRecordingCard } from "./audio-recording-card";
import { JobShareDialog } from "./job-share-dialog";
import { JobDeleteDialog } from "./job-delete-dialog";
import { cn } from "@/lib/utils";
import { getAudioRecordingsQuery } from "@/queries/audio-recordings.query";
import { audioListSchema, statusEnum } from "@/schema/audio-list.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import {
  Eye,
  RefreshCcw,
  LayoutGrid,
  LayoutList,
  Download,
  Play,
  Filter,
  Search,
  FileAudio,
  Calendar,
  Loader2,
  User,
  Trash2,
  MoreHorizontal,
} from "lucide-react";
import { useForm } from "react-hook-form";

const RECORDS_PER_PAGE = 12;

export function AudioRecordingsCombined({
  initialFilters,
}: {
  initialFilters: AudioListValues;
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRecording, setSelectedRecording] = useState<any>(null);
  const [viewMode, setViewMode] = useState<"card" | "table">("card");
  const [filtersExpanded, setFiltersExpanded] = useState(true);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [shareRecording, setShareRecording] = useState<any>(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [deleteRecording, setDeleteRecording] = useState<any>(null);
  const [playingAudio, setPlayingAudio] = useState<string | null>(null);
  const [formatWarningOpen, setFormatWarningOpen] = useState(false);
  const [pendingAudioPlay, setPendingAudioPlay] = useState<string | null>(null);
  const router = useRouter();

  const form = useForm<AudioListValues>({
    defaultValues: initialFilters,
    resolver: zodResolver(audioListSchema),
  });

  const watchedFilters = form.watch();

  const cleanedFilters = useMemo(() => {
    const { job_id, status, created_at } = watchedFilters;
    return {
      job_id: job_id || undefined,
      status: status === "all" ? undefined : status,
      created_at: created_at || undefined,
    };
  }, [watchedFilters]);

  const {
    data: audioRecordings,
    isLoading,
    refetch: refetchJobs,
  } = useQuery(getAudioRecordingsQuery(cleanedFilters));

  // Refresh Handler (Keep Filters)
  const handleRefresh = async () => {
    await refetchJobs();
  };

  // Reset button handler - clears filters
  const handleReset = () => {
    form.reset({ job_id: "", status: "all", created_at: "" });
  };

  // Pagination Logic
  const totalPages = Math.ceil(
    (audioRecordings?.length || 0) / RECORDS_PER_PAGE,
  );

  const paginatedData = audioRecordings?.slice(
    (currentPage - 1) * RECORDS_PER_PAGE,
    currentPage * RECORDS_PER_PAGE,
  );
  const handleViewDetails = (recording: any) => {
    localStorage.setItem("current_recording_id", recording.id);
    router.navigate({
      to: `/audio-recordings/$id`,
      params: { id: recording.id },
    });
  };  const handlePlayAudio = (recording: any) => {
    if (isAudioFile(recording.file_path)) {
      // Check if it's a commonly supported format
      if (isWellSupportedAudioFormat(recording.file_path)) {
        // Directly play well-supported formats
        setPlayingAudio(recording.file_path);
      } else {
        // Show warning for other audio formats that might not work well
        setPendingAudioPlay(recording.file_path);
        setFormatWarningOpen(true);
      }
    } else {
      // Non-audio files open directly in a new tab
      window.open(recording.file_path, "_blank");
    }
  };

  const handleDownloadAudio = (recording: any) => {
    window.open(recording.file_path, "_blank");
  };

  const handleRetryProcessing = (recording: any) => {
    // TODO: Implement retry processing logic
    console.log("Retry processing for:", recording.id);
  };

  // Handler to open share dialog
  const handleShare = (recording: any) => {
    setShareRecording(recording);
    setShareDialogOpen(true);
  };

  // Handler to open delete dialog
  const handleDelete = (recording: any) => {
    setDeleteRecording(recording);
    setDeleteDialogOpen(true);
  };

  return (
    <>
      <Card className="mx-auto mt-8 w-full bg-gradient-to-br from-background via-background to-muted/30 border-border/50 shadow-lg backdrop-blur-sm">
        <CardHeader className="pb-6 border-b border-border/50 bg-gradient-to-r from-background/80 to-muted/20">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <FileAudio className="h-6 w-6" />
                </div>
                <div>
                  <CardTitle className="text-3xl font-bold bg-gradient-to-r from-foreground via-primary to-muted-foreground bg-clip-text text-transparent">
                    Audio Recordings
                  </CardTitle>
                  <p className="text-sm text-muted-foreground mt-1">
                    Manage and monitor your audio files and processing status
                  </p>
                </div>
              </div>
              {audioRecordings && (
                <div className="flex items-center gap-4 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <span className="font-medium text-foreground">
                      {audioRecordings.length}
                    </span>
                    recordings
                  </span>
                  <span className="w-1 h-1 bg-muted-foreground rounded-full" />
                  <span>Last updated: {new Date().toLocaleTimeString()}</span>
                </div>
              )}
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
                <Button
                  variant={viewMode === "card" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("card")}
                  className={cn(
                    "transition-all duration-200",
                    viewMode === "card" ? "shadow-sm" : "hover:bg-background/50",
                  )}
                >
                  <LayoutGrid className="mr-2 h-4 w-4" />
                  Cards
                </Button>
                <Button
                  variant={viewMode === "table" ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setViewMode("table")}
                  className={cn(
                    "transition-all duration-200",
                    viewMode === "table" ? "shadow-sm" : "hover:bg-background/50",
                  )}
                >
                  <LayoutList className="mr-2 h-4 w-4" />
                  Table
                </Button>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6 p-6">
          {/* Enhanced Filters Section */}
          <Card className="border-border/50 bg-gradient-to-br from-card/80 to-muted/10 backdrop-blur-sm">
            <CardContent className="p-0">
              <div className="p-4 border-b border-border/50">
                <Button
                  variant="ghost"
                  onClick={() => setFiltersExpanded(!filtersExpanded)}
                  className="w-full justify-between p-0 h-auto hover:bg-transparent"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-primary/10 text-primary">
                      <Filter className="h-4 w-4" />
                    </div>
                    <div className="text-left">
                      <h3 className="font-semibold text-foreground">
                        Search & Filters
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        Refine your search to find specific recordings
                      </p>
                    </div>
                  </div>
                  <div
                    className={cn(
                      "transition-transform duration-200",
                      filtersExpanded ? "rotate-180" : "",
                    )}
                  >
                    <RefreshCcw className="h-4 w-4" />
                  </div>
                </Button>
              </div>

              {filtersExpanded && (
                <div className="p-4 space-y-4 animate-in slide-in-from-top-2 duration-200">
                  <Form {...form}>
                    <form className="space-y-4">
                      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                        <FormField
                          control={form.control}
                          name="job_id"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                <Search className="h-4 w-4 text-muted-foreground" />
                                Job ID
                              </FormLabel>
                              <FormControl>
                                <Input
                                  placeholder="Search by Job ID..."
                                  {...field}
                                  className="bg-background/50 border-border/50 focus:border-primary/50 transition-colors"
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />

                        <FormField
                          control={form.control}
                          name="status"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                <Filter className="h-4 w-4 text-muted-foreground" />
                                Status
                              </FormLabel>
                              <Select
                                value={field.value}
                                onValueChange={field.onChange}
                              >
                                <SelectTrigger className="bg-background/50 border-border/50 focus:border-primary/50 transition-colors">
                                  <SelectValue placeholder="All statuses" />
                                </SelectTrigger>
                                <SelectContent>
                                  {statusEnum.options.map((status) => (
                                    <SelectItem key={status} value={status}>
                                      <div className="flex items-center gap-2">
                                        {status !== "all" && (
                                          <StatusBadge
                                            status={status as any}
                                            size="sm"
                                          />
                                        )}
                                        <span className="capitalize">
                                          {status === "all"
                                            ? "All Statuses"
                                            : status}
                                        </span>
                                      </div>
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                        <FormField
                          control={form.control}
                          name="created_at"
                          render={({ field }) => (
                            <FormItem>
                              <FormLabel className="flex items-center gap-2 text-sm font-medium">
                                <Calendar className="h-4 w-4 text-muted-foreground" />
                                Upload Date
                              </FormLabel>
                              <FormControl>
                                <DatePicker
                                  field={field}
                                  label=""
                                  placeholder="Select date..."
                                />
                              </FormControl>
                              <FormMessage />
                            </FormItem>
                          )}
                        />
                      </div>

                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between pt-4 border-t border-border/50">
                        <div className="flex gap-2">
                          <Button
                            variant="outline"
                            onClick={handleReset}
                            disabled={isLoading}
                            type="reset"
                            className="hover:bg-muted/50 transition-colors"
                          >
                            <RefreshCcw className="mr-2 h-4 w-4" />
                            Reset
                          </Button>
                          <Button
                            variant="outline"
                            onClick={handleRefresh}
                            disabled={isLoading}
                            type="button"
                            className="hover:bg-muted/50 transition-colors"
                          >
                            {isLoading ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <RefreshCcw className="mr-2 h-4 w-4" />
                            )}
                            {isLoading ? "Refreshing..." : "Refresh"}
                          </Button>
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {audioRecordings && (
                            <span>
                              Showing {paginatedData?.length || 0} of{" "}
                              {audioRecordings.length} recordings
                            </span>
                          )}
                        </div>
                      </div>
                    </form>
                  </Form>
                </div>
              )}
            </CardContent>
          </Card>
          {isLoading && (
            <Card className="border-border/50 bg-gradient-to-r from-card/50 to-muted/10">
              <CardContent className="p-6">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    <p className="text-sm font-medium text-foreground">
                      Loading recordings...
                    </p>
                  </div>
                  <Progress value={90} className="h-2" />
                  <p className="text-xs text-muted-foreground">
                    Fetching your audio files and processing status
                  </p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Mobile Card View (Always visible on mobile, toggleable on desktop) */}
          <div className={cn("block", viewMode === "table" ? "lg:hidden" : "")}>
            {isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {Array.from({ length: 6 }).map((_, index) => (
                  <Card key={`skeleton-${index}`} className="p-4">
                    <div className="space-y-3">
                      <div className="flex items-start justify-between">
                        <div className="space-y-2 flex-1">
                          <Skeleton className="h-4 w-3/4" />
                          <Skeleton className="h-3 w-1/2" />
                        </div>
                        <Skeleton className="h-6 w-16 rounded-md" />
                      </div>
                      <div className="space-y-2">
                        <Skeleton className="h-3 w-1/3" />
                        <Skeleton className="h-3 w-1/4" />
                      </div>
                      <div className="flex items-center justify-between pt-2">
                        <div className="flex gap-2">
                          <Skeleton className="h-8 w-16" />
                          <Skeleton className="h-8 w-16" />
                        </div>
                        <Skeleton className="h-8 w-8 rounded" />
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 animate-in fade-in duration-300">
                {paginatedData && paginatedData.length > 0 ? (
                  paginatedData.map((recording: any, index: number) => (
                    <div
                      key={recording.id}
                      className="animate-in slide-in-from-bottom-4 duration-300"
                      style={{ animationDelay: `${index * 100}ms` }}
                    >                      <AudioRecordingCard
                        recording={recording}
                        onViewDetails={() => handleViewDetails(recording)}
                        onPlay={() => handlePlayAudio(recording)}
                        onDownload={() => handleDownloadAudio(recording)}
                        onRetryProcessing={() => handleRetryProcessing(recording)}
                        onShare={() => handleShare(recording)}
                        onDelete={() => handleDelete(recording)}
                      />
                    </div>
                  ))
                ) : (
                  <div className="col-span-full">
                    <Card className="p-8 border-dashed border-2 border-border/50 bg-gradient-to-br from-card/30 to-muted/10">
                      <div className="text-center space-y-4">
                        <div className="mx-auto h-16 w-16 rounded-full bg-gradient-to-br from-primary/10 to-muted/20 flex items-center justify-center">
                          <FileAudio className="h-8 w-8 text-primary/60" />
                        </div>
                        <div className="space-y-2">
                          <h3 className="text-lg font-semibold text-foreground">
                            No recordings found
                          </h3>
                          <p className="text-sm text-muted-foreground max-w-md mx-auto">
                            {Object.values(cleanedFilters).some(Boolean)
                              ? "No recordings match your current filters. Try adjusting your search criteria."
                              : "Upload your first audio recording to get started with transcription and analysis."}
                          </p>
                        </div>
                        <div className="flex flex-col sm:flex-row gap-2 justify-center">
                          {Object.values(cleanedFilters).some(Boolean) && (
                            <Button variant="outline" onClick={handleReset} size="sm">
                              Clear Filters
                            </Button>
                          )}
                          <Button variant="outline" onClick={handleRefresh} size="sm">
                            <RefreshCcw className="mr-2 h-4 w-4" />
                            Refresh
                          </Button>
                        </div>
                      </div>
                    </Card>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Desktop Table View */}
          <div className={cn("hidden", viewMode === "table" ? "lg:block" : "")}>
            <Card className="border-border/50 bg-card/50">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/50">
                    <TableHead className="text-left font-semibold">Job ID</TableHead>
                    <TableHead className="text-left font-semibold">File Name</TableHead>
                    <TableHead className="text-left font-semibold">Status</TableHead>
                    <TableHead className="text-left font-semibold">Upload Date</TableHead>
                    <TableHead className="text-right font-semibold">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                {isLoading ? (
                  <TableBody>
                    {Array.from({ length: 8 }).map((_, index) => (
                      <TableRow key={`table-skeleton-${index}`} className="border-border/50">
                        <TableCell><Skeleton className="h-5 w-24" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-48" /></TableCell>
                        <TableCell><Skeleton className="h-6 w-24" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-28" /></TableCell>
                        <TableCell><Skeleton className="h-8 w-8 rounded ml-auto" /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                ) : (
                  <TableBody>
                    {paginatedData && paginatedData.length > 0 ? (
                      paginatedData.map((row: any) => (
                        <TableRow key={row.id} className="hover:bg-muted/50 border-border/50">
                          <TableCell className="font-mono text-sm">{row.id}</TableCell>                          <TableCell className="max-w-[250px]">
                            <div className="truncate font-medium text-primary">
                              {row.file_name ||
                                getFileNameFromPath(row.file_path) ||
                                "Unnamed Recording"}
                            </div>
                          </TableCell>
                          <TableCell>
                            <StatusBadge
                              status={row.status}
                              size="sm"
                              showIcon={true}
                              animate={row.status === "processing"}
                            />
                          </TableCell>
                          <TableCell className="text-muted-foreground">
                            {new Date(
                              parseInt(row.created_at),
                            ).toLocaleDateString()}
                          </TableCell>
                          <TableCell className="text-right">
                            <DropdownMenu
                              onOpenChange={(open) => {
                                if (open) setSelectedRecording(row);
                              }}
                            >                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-8 w-8"
                                >
                                  <MoreHorizontal className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              {selectedRecording &&
                                selectedRecording.id === row.id && (
                                  <DropdownMenuContent align="end">
                                    <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                    <DropdownMenuItem
                                      onClick={() => handleViewDetails(row)}
                                    >
                                      <Eye className="mr-2 h-4 w-4" />
                                      View Details
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => handlePlayAudio(row)}
                                    >
                                      <Play className="mr-2 h-4 w-4" />
                                      Play Audio
                                    </DropdownMenuItem>
                                    <DropdownMenuItem
                                      onClick={() => handleDownloadAudio(row)}
                                    >
                                      <Download className="mr-2 h-4 w-4" />
                                      Download
                                    </DropdownMenuItem>
                                    <DropdownMenuItem onClick={() => handleShare(row)}>
                                      <User className="mr-2 h-4 w-4" />
                                      Share
                                    </DropdownMenuItem>
                                    {row.status === "uploaded" && (
                                      <DropdownMenuItem onClick={() => handleRetryProcessing(row)}>
                                        <RefreshCcw className="mr-2 h-4 w-4" />
                                        Retry Processing
                                      </DropdownMenuItem>
                                    )}
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem onClick={() => handleDelete(row)}>
                                      <Trash2 className="mr-2 h-4 w-4" />
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                )}
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))
                    ) : null}
                  </TableBody>
                )}
              </Table>
            </Card>
          </div>
          {/* Enhanced Pagination Controls */}
          {totalPages > 1 && (
            <Card className="border-border/50 bg-gradient-to-r from-card/50 to-muted/10">
              <CardContent className="p-4">
                <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1 || isLoading}
                      className="hover:bg-muted transition-colors"
                    >
                      Previous
                    </Button>
                    <div className="flex items-center gap-1">
                      {[...Array(Math.min(totalPages, 5))].map((_, i) => {
                        const pageNum = i + 1;
                        const isActive = pageNum === currentPage;
                        return (
                          <Button
                            key={pageNum}
                            variant={isActive ? "default" : "outline"}
                            size="sm"
                            onClick={() => setCurrentPage(pageNum)}
                            disabled={isLoading}
                            className={cn(
                              "w-8 h-8 p-0 transition-all duration-200",
                              isActive && "bg-primary text-primary-foreground shadow-md",
                            )}
                          >
                            {pageNum}
                          </Button>
                        );
                      })}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage >= totalPages || isLoading}
                      className="hover:bg-muted transition-colors"
                    >
                      Next
                    </Button>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">
                        Page {currentPage} of {totalPages}
                      </span>
                      {audioRecordings && (
                        <>
                          <span className="w-1 h-1 bg-muted-foreground rounded-full" />
                          <span>
                            {audioRecordings.length} total record
                            {audioRecordings.length !== 1 ? "s" : ""}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </CardContent>
      </Card>      {shareRecording && (
        <JobShareDialog
          isOpen={shareDialogOpen}
          onOpenChange={setShareDialogOpen}
          jobId={shareRecording.id}
          jobTitle={
            shareRecording.file_name ||
            getFileNameFromPath(shareRecording.file_path)
          }
        />
      )}      {deleteRecording && (
        <JobDeleteDialog
          isOpen={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          jobId={deleteRecording.id}
          jobTitle={
            deleteRecording.file_name ||
            getFileNameFromPath(deleteRecording.file_path)
          }
          onDeleteSuccess={refetchJobs}
        />      )}
      
      {/* Format Warning Dialog */}
      {pendingAudioPlay && (
        <FormatWarningDialog
          isOpen={formatWarningOpen}
          onOpenChange={setFormatWarningOpen}
          filePath={pendingAudioPlay}
          onContinue={() => setPlayingAudio(pendingAudioPlay)}
        />
      )}
      
      {/* Mini Audio Player */}
      {playingAudio && (
        <MiniAudioPlayer
          src={playingAudio}
          onClose={() => setPlayingAudio(null)}
        />
      )}
    </>
  );
}

interface AudioTableSkeletonProps {
  rows?: number;
}

const DEFAULT_SKELETON_ROWS = 8;

export function AudioTableSkeleton({
  rows = DEFAULT_SKELETON_ROWS,
}: AudioTableSkeletonProps) {
  return (
    <TableBody>
      {Array.from({ length: rows }).map((_, index) => (
        <TableRow key={`skeleton-${index}`}>
          {/* Job ID */}
          <TableCell>
            <Skeleton className="h-5 w-24" />
          </TableCell>
          {/* File Name */}
          <TableCell>
            <Skeleton className="h-5 w-48" />
          </TableCell>
          {/* Status */}
          <TableCell>
            <Skeleton className="h-6 w-[100px] rounded-md" />{" "}
            {/* Mimic Badge */}
          </TableCell>
          {/* Upload Date */}
          <TableCell>
            <Skeleton className="h-5 w-28" />
          </TableCell>
          {/* Actions */}
          <TableCell>
            <Skeleton className="h-8 w-8 rounded-md" />{" "}
            {/* Mimic Icon Button */}
          </TableCell>
        </TableRow>
      ))}
    </TableBody>
  );
}

interface MobileCardSkeletonProps {
  cards?: number;
}

const DEFAULT_SKELETON_CARDS = 5;

export function MobileCardSkeleton({
  cards = DEFAULT_SKELETON_CARDS,
}: MobileCardSkeletonProps) {
  return (
    <div className="space-y-4">
      {Array.from({ length: cards }).map((_, index) => (
        <Card key={`mobile-skeleton-${index}`} className="p-3">
          <div className="space-y-2">
            <div className="flex items-start justify-between">
              <div className="min-w-0 flex-1 space-y-1.5">
                <Skeleton className="h-4 w-32" /> {/* File name */}
                <Skeleton className="h-3 w-24" /> {/* Job ID */}
              </div>
              <Skeleton className="ml-1 h-4 w-12 rounded" /> {/* Status badge */}
            </div>

            <div className="flex items-center justify-between">
              <Skeleton className="h-3 w-16" /> {/* Date */}
              <Skeleton className="h-7 w-7 rounded" /> {/* Actions button */}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}
