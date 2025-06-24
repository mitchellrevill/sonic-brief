import { useQuery } from "@tanstack/react-query";
import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FileAudio,
  Loader2,
  Filter,
  RefreshCw,
  ClipboardList,
  Calendar,
  User,
  Clock,
} from "lucide-react";
import { fetchAllUsers } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/ui/status-badge";
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

type Job = {
  id: string;
  user_id: string;
  file_name?: string;
  file_path?: string;
  status?: string;
  created_at?: string;
  updated_at?: string;
  user_email?: string;
  deleted?: boolean;
};

type JobsResponse = {
  status: string;
  jobs: Job[];
};

export function AdminAllJobsPage() {
  const breadcrumbs = useBreadcrumbs();
  const [userFilter, setUserFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  
  // Fetch users for filter dropdown
  const { data: usersData } = useQuery<UserRecord[] | UsersResponse>({
    queryKey: ["users"],
    queryFn: fetchAllUsers,
    staleTime: 60000, // Cache for 1 minute
  });
    // Fetch all jobs (we need to create a function to get all jobs)
  const fetchAllJobs = async () => {
    const token = localStorage.getItem("token");
    if (!token) throw new Error("No authentication token found. Please log in again.");

    // Use the admin endpoint for all jobs
    const response = await fetch(`${import.meta.env.VITE_API_URL}/api/jobs`, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  };

  const {
    data: jobsData,
    isLoading,
    error,
    refetch,
  } = useQuery<JobsResponse>({
    queryKey: ["adminAllJobs"],
    queryFn: fetchAllJobs,
    staleTime: 30000, // Cache for 30 seconds
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

  // Filter jobs by user and status
  const filteredJobs = useMemo(() => {
    if (!jobsData?.jobs) return [];
    
    const jobs = jobsData.jobs;
    
    return jobs.filter(job => {
      const matchesUser = userFilter === "all" || job.user_id === userFilter;
      const matchesStatus = statusFilter === "all" || job.status === statusFilter;
      return matchesUser && matchesStatus && !job.deleted; // Exclude soft-deleted jobs
    });
  }, [jobsData?.jobs, userFilter, statusFilter]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
              <p className="text-muted-foreground">Loading all recordings...</p>
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
              <p className="text-destructive">Failed to load recordings</p>
              <p className="text-sm text-muted-foreground mt-2">
                {(error as Error).message}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const allJobs = jobsData?.jobs?.filter(job => !job.deleted) || [];
  const userRecords: UserRecord[] = usersData ? (Array.isArray(usersData) ? usersData : usersData.users || []) : [];
  
  // Get unique statuses for the filter
  const uniqueStatuses = [...new Set(allJobs.map(job => job.status).filter(Boolean))];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      {/* Header */}
      <div className="border-b border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <ClipboardList className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                All Recordings
              </h1>
              <SmartBreadcrumb items={breadcrumbs} />
              <p className="text-muted-foreground">
                Admin view of all recordings ({filteredJobs.length} of {allJobs.length} total)
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 mb-6">
          <div className="flex flex-col md:flex-row items-center gap-4 w-full md:w-auto">
            <div className="flex items-center gap-2 w-full md:w-auto">
              <User className="h-4 w-4 text-muted-foreground" />
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
            
            <div className="flex items-center gap-2 w-full md:w-auto">
              <Filter className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">Filter by status:</span>
              <Select 
                value={statusFilter} 
                onValueChange={(value) => setStatusFilter(value)}
              >
                <SelectTrigger className="w-[200px]">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  {uniqueStatuses.filter((status): status is string => typeof status === "string").map((status: string) => (
                    <SelectItem key={status} value={status}>
                      {status.charAt(0).toUpperCase() + status.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
          {filteredJobs.length === 0 ? (
            <Card>
              <CardContent className="p-8 text-center">
                <ClipboardList className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <h3 className="text-lg font-medium mb-2">No recordings found</h3>
                <p className="text-muted-foreground">
                  {userFilter === "all" && statusFilter === "all"
                    ? "There are no recordings in the system." 
                    : "No recordings found matching the selected filters."}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredJobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  userMap={userMap}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface JobCardProps {
  job: Job;
  userMap: Record<string, { email: string; name?: string }>;
}

function JobCard({ 
  job, 
  userMap
}: JobCardProps) {
  // Get user display info from the map
  const ownerInfo = job.user_id ? userMap[job.user_id] : null;
  const ownerDisplay = ownerInfo
    ? ownerInfo.name || ownerInfo.email
    : job.user_email || "Unknown user";

  return (
    <Card className="hover:shadow-md transition-all duration-200">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1 flex-1 min-w-0">
            <CardTitle className="text-base font-medium truncate">
              {job.file_name || "Unknown Recording"}
            </CardTitle>
            <div className="flex items-center gap-2">
              <StatusBadge status={job.status as "completed" | "processing" | "uploaded" | "failed" | "error" | "default" || "default"} />
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
            <Clock className="h-3 w-3" />
            Updated: {job.updated_at ? 
              formatDistanceToNow(new Date(job.updated_at), { addSuffix: true }) :
              "Unknown date"
            }
          </div>
          <div className="flex items-center gap-1">
            <User className="h-3 w-3" />
            Owner: <span className="font-medium">{ownerDisplay}</span>
          </div>
        </div>

        {/* View Details Link */}        <div className="flex gap-2 pt-2 border-t">
          <Button
            variant="outline"
            size="sm"
            className="flex-1 w-full"
            onClick={() => {
              // Navigate programmatically
              window.location.href = `/audio-recordings/${job.id}`;
            }}
          >
            View Details
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
