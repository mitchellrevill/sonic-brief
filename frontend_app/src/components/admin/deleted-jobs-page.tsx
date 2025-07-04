import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Trash2,
  RotateCcw,
  Calendar,
  User,
  FileAudio,
  Loader2,
  AlertTriangle,
  Filter,
  RefreshCw,
} from "lucide-react";
import { getDeletedJobs, restoreJob, permanentDeleteJob, fetchAllUsers } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/ui/status-badge";
import { toast } from "sonner";
import { useState, useMemo } from "react";

// Define proper TypeScript types for better type safety
type UserRecord = {
  id: string;
  email: string;
  name?: string;
  permission?: string;
};

type UsersResponse = {
  users: UserRecord[];
  status?: number;
};

type DeletedJob = {
  id: string;
  user_id: string;
  deleted_by: string;
  file_name?: string;
  file_path?: string;
  status?: string;
  created_at?: string;
  deleted_at?: string;
  user_email?: string;
  transcription_file_path?: string;
  analysis_file_path?: string;
};

type DeletedJobsResponse = {
  status: string;
  message: string;
  count: number;
  jobs: DeletedJob[];
};

export function AdminDeletedJobsPage() {
  const breadcrumbs = useBreadcrumbs();
  const queryClient = useQueryClient();
  const [userFilter, setUserFilter] = useState<string>("all");
  
  // Fetch users for filter dropdown
  const { data: usersData } = useQuery<UserRecord[] | UsersResponse>({
    queryKey: ["users"],
    queryFn: fetchAllUsers,
    staleTime: 60000, // Cache for 1 minute
  });
  
  const {
    data: deletedJobsData,
    isLoading,
    error,
    refetch,
  } = useQuery<DeletedJobsResponse>({
    queryKey: ["deletedJobs"],
    queryFn: getDeletedJobs,
    staleTime: 30000, // Cache for 30 seconds
  });

  const restoreJobMutation = useMutation({
    mutationFn: restoreJob,
    onSuccess: () => {
      toast.success("Job restored successfully!");
      queryClient.invalidateQueries({ queryKey: ["deletedJobs"] });
      queryClient.invalidateQueries({ queryKey: ["audioRecordings"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to restore job: ${error.message}`);
    },
  });

  const permanentDeleteMutation = useMutation({
    mutationFn: permanentDeleteJob,
    onSuccess: () => {
      toast.success("Job permanently deleted!");
      queryClient.invalidateQueries({ queryKey: ["deletedJobs"] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to permanently delete job: ${error.message}`);
    },
  });

  // Build a map of user IDs to user information for displaying user details
  const userMap = useMemo(() => {
    if (!usersData) return {};
    
    const users: UserRecord[] = Array.isArray(usersData) 
      ? usersData 
      : usersData.users || [];
    
    return users.reduce((acc: Record<string, { email: string, name?: string }>, user: UserRecord) => {
      acc[user.id] = { 
        email: user.email,
        name: user.name || undefined
      };
      return acc;
    }, {});
  }, [usersData]);

  // Filter deleted jobs by user
  const filteredDeletedJobs = useMemo(() => {
    if (!deletedJobsData?.jobs) return [];
    
    const jobs = deletedJobsData.jobs;
    
    if (userFilter === "all") {
      return jobs;
    }
    
    return jobs.filter(job => job.deleted_by === userFilter || job.user_id === userFilter);
  }, [deletedJobsData?.jobs, userFilter]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
              <p className="text-muted-foreground">Loading deleted recordings...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
        <div className="container mx-auto px-4 py-6">
          <Card className="max-w-md mx-auto">
            <CardContent className="p-6 text-center">
              <p className="text-destructive">Failed to load deleted recordings</p>
              <p className="text-sm text-muted-foreground mt-2">
                {(error as Error).message}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const deletedJobs = deletedJobsData?.jobs || [];
  
  const userRecords: UserRecord[] = usersData ? (Array.isArray(usersData) ? usersData : usersData.users || []) : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      {/* Header */}
      <div className="border-b border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-destructive/10 text-destructive">
              <Trash2 className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                Deleted Recordings
              </h1>
              <SmartBreadcrumb items={breadcrumbs} />
              <p className="text-muted-foreground">
                Admin view of soft-deleted recordings ({filteredDeletedJobs.length} of {deletedJobs.length} total)
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-2 w-full md:w-auto">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Filter by user:</span>
            <Select 
              value={userFilter} 
              onValueChange={(value) => setUserFilter(value)}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue placeholder="Select user" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Users</SelectItem>
                {userRecords.map((user: UserRecord) => (
                  <SelectItem key={user.id} value={user.id}>
                    {user.name || user.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <Button 
            variant="outline" 
            size="sm" 
            onClick={() => refetch()} 
            className="flex items-center gap-2 w-full md:w-auto"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
        </div>
        
        <div className="space-y-6">
          {filteredDeletedJobs.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <Trash2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <h3 className="text-lg font-medium mb-2">No deleted recordings found</h3>
                <p className="text-muted-foreground">
                  {userFilter === "all" 
                    ? "There are no deleted recordings in the system." 
                    : "No deleted recordings found for the selected user."}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredDeletedJobs.map((job) => (
                <DeletedJobCard
                  key={job.id}
                  job={job}
                  userMap={userMap}
                  onRestore={(jobId) => restoreJobMutation.mutate(jobId)}
                  onPermanentDelete={(jobId) => permanentDeleteMutation.mutate(jobId)}
                  isRestoring={restoreJobMutation.isPending}
                  isPermanentDeleting={permanentDeleteMutation.isPending}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface DeletedJobCardProps {
  job: DeletedJob;
  userMap: Record<string, { email: string; name?: string }>;
  onRestore: (jobId: string) => void;
  onPermanentDelete: (jobId: string) => void;
  isRestoring: boolean;
  isPermanentDeleting: boolean;
}

function DeletedJobCard({ 
  job, 
  userMap,
  onRestore, 
  onPermanentDelete, 
  isRestoring, 
  isPermanentDeleting 
}: DeletedJobCardProps) {
  const handleRestore = () => {
    onRestore(job.id);
  };

  const handlePermanentDelete = () => {
    onPermanentDelete(job.id);
  };

  // Get user display info from the map
  const ownerInfo = job.user_id ? userMap[job.user_id] : null;
  const ownerDisplay = ownerInfo
    ? ownerInfo.name || ownerInfo.email
    : job.user_email || "Unknown user";
  
  // Get user who deleted the job
  const deletedByInfo = job.deleted_by ? userMap[job.deleted_by] : null;
  const deletedByDisplay = deletedByInfo
    ? deletedByInfo.name || deletedByInfo.email
    : "Unknown admin";
  return (
    <Card className="hover:shadow-md transition-all duration-200 border-destructive/20 bg-card">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1 min-w-0">
            <CardTitle className="text-base font-medium truncate">
              {job.file_name || "Unknown Recording"}
            </CardTitle>            <div className="flex items-center gap-2">
              <StatusBadge status={job.status as "completed" | "processing" | "uploaded" | "failed" | "error" | "default" || "default"} />
              <Badge variant="secondary" className="text-xs">
                Deleted
              </Badge>
            </div>
          </div>
          <FileAudio className="h-5 w-5 text-muted-foreground shrink-0" />
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Job Details */}
        <div className="space-y-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            Created: {job.created_at ? 
              formatDistanceToNow(new Date(job.created_at), { addSuffix: true }) :
              "Unknown date"
            }
          </div>
          <div className="flex items-center gap-1">
            <Trash2 className="h-3 w-3" />
            Deleted: {job.deleted_at ? 
              formatDistanceToNow(new Date(job.deleted_at), { addSuffix: true }) :
              "Unknown date"
            } by <span className="font-medium text-destructive">{deletedByDisplay}</span>
          </div>
          <div className="flex items-center gap-1">
            <User className="h-3 w-3" />
            Owner: <span className="font-medium">{ownerDisplay}</span>
          </div>
        </div>

        {/* Admin Actions */}
        <div className="flex gap-2 pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRestore}
            disabled={isRestoring || isPermanentDeleting}
            className="flex-1 text-green-600 hover:text-green-700 hover:bg-green-50"
          >
            {isRestoring ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4" />
            )}
            <span className="ml-1">Restore</span>
          </Button>

          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                disabled={isRestoring || isPermanentDeleting}
                className="flex-1 text-destructive hover:text-destructive hover:bg-destructive/10"
              >
                <AlertTriangle className="h-4 w-4" />
                <span className="ml-1">Permanent</span>
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle className="flex items-center gap-2">
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                  Permanently Delete Recording
                </AlertDialogTitle>
                <AlertDialogDescription>
                  Are you sure you want to permanently delete "{job.file_name || 'this recording'}"? 
                  This action cannot be undone and all data will be permanently lost.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancel</AlertDialogCancel>
                <AlertDialogAction
                  onClick={handlePermanentDelete}
                  className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                >
                  Permanently Delete
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      </CardContent>
    </Card>
  );
}
