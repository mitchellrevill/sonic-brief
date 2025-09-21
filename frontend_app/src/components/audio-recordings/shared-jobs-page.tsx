import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import { getDisplayName } from "@/lib/display-name-utils";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Users,
  Share2,
  Eye,
  FileAudio,
  Calendar,
  User,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { getSharedJobs } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";
import { StatusBadge } from "@/components/ui/status-badge";

export function SharedJobsPage() {
  const breadcrumbs = useBreadcrumbs();
  
  const {
    data: sharedJobsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["sharedJobs"],
    queryFn: getSharedJobs,
    staleTime: 60000, // Cache for 1 minute
  });

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center justify-center min-h-[400px]">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary mx-auto mb-4" />
              <p className="text-muted-foreground">Loading shared recordings...</p>
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
              <p className="text-destructive">Failed to load shared recordings</p>
              <p className="text-sm text-muted-foreground mt-2">
                {error.message}
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const sharedJobs = sharedJobsData?.shared_jobs || [];
  const ownedSharedJobs = sharedJobsData?.owned_jobs_shared_with_others || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">      {/* Header */}
      <div className="border-b border-border/50 bg-card/50 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10 text-primary">
              <Share2 className="h-6 w-6" />
            </div>
            <div className="space-y-1">
              <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground to-muted-foreground bg-clip-text text-transparent">
                Shared Recordings
              </h1>
              <SmartBreadcrumb items={breadcrumbs} />
              <p className="text-muted-foreground">
                Recordings shared with you and recordings you've shared with others
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-6">
        <div className="space-y-8">
          {/* Recordings Shared With Me */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Users className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">
                Shared With Me ({sharedJobs.length})
              </h2>
            </div>
            
            {sharedJobs.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Users className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                  <h3 className="text-lg font-medium mb-2">No shared recordings</h3>
                  <p className="text-muted-foreground">
                    When others share recordings with you, they'll appear here.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {sharedJobs.map((job) => (
                  <SharedJobCard key={job.id} job={job} isOwner={false} />
                ))}
              </div>
            )}
          </section>

          {/* My Recordings Shared With Others */}
          <section>
            <div className="flex items-center gap-2 mb-4">
              <Share2 className="h-5 w-5 text-primary" />
              <h2 className="text-xl font-semibold">
                My Shared Recordings ({ownedSharedJobs.length})
              </h2>
            </div>
            
            {ownedSharedJobs.length === 0 ? (
              <Card>
                <CardContent className="p-8 text-center">
                  <Share2 className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                  <h3 className="text-lg font-medium mb-2">No shared recordings</h3>
                  <p className="text-muted-foreground">
                    Recordings you share with others will appear here.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {ownedSharedJobs.map((job) => (
                  <SharedJobCard key={job.id} job={job} isOwner={true} />
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

interface SharedJobCardProps {
  job: any;
  isOwner: boolean;
}

function SharedJobCard({ job, isOwner }: SharedJobCardProps) {
  const displayName = getDisplayName(job);
  
  // Get user's permission for this job
  const userShare = !isOwner && job.shared_with?.[0];
  const userPermission = isOwner ? "owner" : userShare?.permission_level || "unknown";
  
  // Get the sharing message for this user (when shared with them)
  const sharingMessage = !isOwner ? userShare?.message : null;

  return (
    <Card className="hover:shadow-md transition-shadow duration-200">
      <CardContent className="p-4">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <FileAudio className="h-4 w-4 text-primary flex-shrink-0" />
              <h3 className="font-medium text-sm truncate" title={displayName}>
                {displayName}
              </h3>
            </div>
            <StatusBadge 
              status={job.status} 
              size="sm"
              animate={job.status === "processing"}
            />
          </div>

          {/* Job ID */}
          <div className="text-xs text-muted-foreground">
            ID: {job.id}
          </div>

          {/* Permission and Sharing Info */}
          <div className="flex items-center gap-2">
            <Badge 
              variant="outline" 
              className={`text-xs ${
                userPermission === "owner" ? "bg-orange-100 text-orange-800 border-orange-200" :
                userPermission === "admin" ? "bg-purple-100 text-purple-800 border-purple-200" :
                userPermission === "edit" ? "bg-green-100 text-green-800 border-green-200" :
                "bg-blue-100 text-blue-800 border-blue-200"
              }`}
            >
              {userPermission}
            </Badge>            {isOwner && job.shared_with && (
              <Badge variant="secondary" className="text-xs">
                {job.shared_with.length} {job.shared_with.length === 1 ? "user" : "users"}
              </Badge>
            )}
          </div>

          {/* Metadata */}
          <div className="space-y-1 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {job.created_at ? 
                formatDistanceToNow(new Date(job.created_at), { addSuffix: true }) :
                "Unknown date"
              }
            </div>
            {!isOwner && job.shared_by_email && (
              <div className="flex items-center gap-1">
                <User className="h-3 w-3" />
                Shared by {job.shared_by_email}
              </div>
            )}
          </div>

          {/* Sharing Message */}
          {sharingMessage && (
            <div className="p-3 bg-muted/50 rounded-md border">
              <p className="text-xs text-muted-foreground mb-1 font-medium">Message:</p>
              <p className="text-sm text-foreground">{sharingMessage}</p>
            </div>
          )}

          {/* Actions */}
          <div className="pt-2 border-t">
            <Link
              to="/audio-recordings/$id"
              params={{ id: job.id }}
              className="w-full"
            >
              <Button variant="outline" size="sm" className="w-full">
                <Eye className="mr-2 h-3 w-3" />
                View Details
                <ArrowRight className="ml-2 h-3 w-3" />
              </Button>
            </Link>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
