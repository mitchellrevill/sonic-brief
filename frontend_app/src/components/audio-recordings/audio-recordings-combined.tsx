import type { AudioListValues } from "@/schema/audio-list.schema";
import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
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
import { cn } from "@/lib/utils";
import { getAudioRecordingsQuery } from "@/queries/audio-recordings.query";
import { audioListSchema, statusEnum } from "@/schema/audio-list.schema";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import { Eye, RefreshCcw } from "lucide-react";
import { useForm } from "react-hook-form";

const statusVariants: Record<string, string> = {
  completed: "bg-green-500 text-white",
  processing: "bg-yellow-500 text-black",
  uploaded: "bg-blue-500 text-white",
  failed: "bg-red-500 text-white",
  default: "bg-gray-400 text-white",
};

const RECORDS_PER_PAGE = 10;

export function AudioRecordingsCombined({
  initialFilters,
}: {
  initialFilters: AudioListValues;
}) {
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedRecording, setSelectedRecording] = useState<any>(null);
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

  return (
    <>
      <Card className="mx-auto mt-8 w-full">
        <CardHeader>
          <CardTitle>Audio Recordings</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form className="space-y-4">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <FormField
                  control={form.control}
                  name="job_id"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Job ID</FormLabel>
                      <FormControl>
                        <Input placeholder="Enter Job ID" {...field} />
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
                      <FormLabel>Status</FormLabel>
                      <Select
                        value={field.value}
                        onValueChange={field.onChange}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select status" />
                        </SelectTrigger>
                        <SelectContent>
                          {statusEnum.options.map((status) => (
                            <SelectItem key={status} value={status}>
                              {status.charAt(0).toUpperCase() + status.slice(1)}
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
                    <DatePicker
                      field={field}
                      label="Upload Date"
                      placeholder="Pick an upload date"
                    />
                  )}
                />
              </div>

              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  onClick={handleReset}
                  disabled={isLoading}
                  type="reset"
                >
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  {isLoading ? "Resetting..." : "Reset"}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleRefresh}
                  disabled={isLoading}
                  type="button"
                >
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  {isLoading ? "Refreshing..." : "Refresh"}
                </Button>
              </div>
            </form>
          </Form>

          {isLoading && <Progress value={90} className="mt-4 mb-4" />}

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Job ID</TableHead>
                <TableHead>File Name</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Upload Date</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            {isLoading ? (
              <AudioTableSkeleton />
            ) : (
              <TableBody>
                {paginatedData && paginatedData.length > 0 ? (
                  paginatedData.map((row: any) => (
                    <TableRow key={row.id}>
                      <TableCell>{row.id}</TableCell>
                      <TableCell className="max-w-[250px] truncate font-medium text-blue-500">
                        {row.file_name ||
                          row.file_path.split("/").pop() ||
                          "Unnamed Recording"}
                      </TableCell>
                      <TableCell>
                        <Badge
                          className={cn(
                            "flex min-w-[100px] items-center justify-center rounded-md px-4 py-1 text-xs",
                            statusVariants[row.status] ||
                              statusVariants.default,
                          )}
                        >
                          {row.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {new Date(
                          parseInt(row.created_at),
                        ).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        {/* Action Dropdown */}
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => setSelectedRecording(row)}
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          {selectedRecording &&
                            selectedRecording.id === row.id && (
                              <DropdownMenuContent align="end">
                                <DropdownMenuLabel>Actions</DropdownMenuLabel>
                                <DropdownMenuItem
                                  onClick={() => {
                                    localStorage.setItem(
                                      "current_recording_id",
                                      row.id,
                                    );
                                    router.navigate({
                                      to: `/audio-recordings/$id`,
                                      params: { id: row.id },
                                    });
                                  }}
                                >
                                  <Eye className="mr-2 h-4 w-4" />
                                  View Details
                                </DropdownMenuItem>
                                {row.status === "uploaded" && (
                                  <DropdownMenuItem onClick={() => null}>
                                    <RefreshCcw className="mr-2 h-4 w-4" />
                                    Retry Processing
                                  </DropdownMenuItem>
                                )}
                              </DropdownMenuContent>
                            )}
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={5}
                      className="py-4 text-center text-gray-500"
                    >
                      No results found
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            )}
          </Table>

          {/* Pagination Controls*/}
          <div className="mt-4 flex justify-between">
            <Button
              onClick={() => setCurrentPage(currentPage - 1)}
              disabled={currentPage === 1}
            >
              Previous
            </Button>
            <span>
              Page {currentPage} of {totalPages}
            </span>
            <Button
              onClick={() => setCurrentPage(currentPage + 1)}
              disabled={currentPage >= totalPages}
            >
              Next
            </Button>
          </div>
        </CardContent>
      </Card>
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
