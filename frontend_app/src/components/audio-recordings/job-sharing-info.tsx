import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sharingToasts } from "@/lib/toast-utils";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
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
  Users,
  Shield,
  Eye,
  Edit,
  UserMinus,
  Clock,
  Loader2,
} from "lucide-react";
import { getJobSharingInfo, unshareJob } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";

interface JobSharingInfoProps {
  jobId: string;
  jobTitle?: string;
}

type PermissionLevel = "view" | "edit" | "admin" | "owner";

interface ShareEntry {
  user_id: string;
  user_email: string;
  permission_level: string; // Use string to match API response
  shared_at: number;
  shared_by: string;
  message?: string;
}

const permissionIcons = {
  view: Eye,
  edit: Edit,
  admin: Shield,
  owner: Shield,
};

const permissionColors = {
  view: "bg-blue-100 text-blue-800 border-blue-200",
  edit: "bg-green-100 text-green-800 border-green-200",
  admin: "bg-purple-100 text-purple-800 border-purple-200",
  owner: "bg-orange-100 text-orange-800 border-orange-200",
};

export function JobSharingInfo({ jobId, jobTitle = "Recording" }: JobSharingInfoProps) {
  const queryClient = useQueryClient();

  const {
    data: sharingInfo,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["jobSharingInfo", jobId],
    queryFn: () => getJobSharingInfo(jobId),
    staleTime: 30000, // Cache for 30 seconds
  });

  const unshareJobMutation = useMutation({
    mutationFn: (userEmail: string) => unshareJob(jobId, userEmail),
    onSuccess: (_, userEmail) => {
      sharingToasts.revoked(userEmail);
      queryClient.invalidateQueries({ queryKey: ["jobSharingInfo", jobId] });
      queryClient.invalidateQueries({ queryKey: ["sharedJobs"] });
      queryClient.invalidateQueries({ queryKey: ["audioRecordings"] });
    },
    onError: (error, userEmail) => {
      sharingToasts.failed(userEmail, error.message);
    },
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }
  if (error) {
    // If access is denied, don't show the component at all
    if (error.message.includes("403") || error.message.includes("Access denied")) {
      return null;
    }
    
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            <p>Unable to load sharing information</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!sharingInfo?.shared_with?.length) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-muted-foreground">
            <Users className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>This recording is not shared with anyone</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const handleUnshare = (userEmail: string) => {
    unshareJobMutation.mutate(userEmail);
  };

  return (
    <Card>
      <CardHeader className="pb-4">
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5 text-primary" />
          Shared With ({sharingInfo.total_shares})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">        {sharingInfo.shared_with.map((share: ShareEntry) => {
          const permissionLevel = share.permission_level as PermissionLevel;
          const PermissionIcon = permissionIcons[permissionLevel] || Eye;
          
          return (
            <div key={share.user_id} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 bg-muted rounded-full flex items-center justify-center">
                      <PermissionIcon className="h-4 w-4 text-muted-foreground" />
                    </div>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm truncate">
                      {share.user_email}
                    </p>                    <div className="flex items-center gap-2 mt-1">
                      <Badge
                        variant="outline"
                        className={`text-xs ${permissionColors[permissionLevel] || permissionColors.view}`}
                      >
                        {share.permission_level}
                      </Badge>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {formatDistanceToNow(new Date(share.shared_at), { addSuffix: true })}
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Only show unshare button if current user is owner */}
                {sharingInfo.is_owner && (
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-muted-foreground hover:text-destructive"
                        disabled={unshareJobMutation.isPending}
                      >
                        <UserMinus className="h-4 w-4" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Remove Sharing</AlertDialogTitle>
                        <AlertDialogDescription>
                          Are you sure you want to remove sharing with {share.user_email}? 
                          They will no longer be able to access "{jobTitle}".
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => handleUnshare(share.user_email)}
                          className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                        >
                          Remove Access
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                )}
              </div>
              
              {share.message && (
                <div className="ml-11 p-2 bg-muted/50 rounded-md text-xs text-muted-foreground">
                  "{share.message}"
                </div>
              )}
              
              {share !== sharingInfo.shared_with[sharingInfo.shared_with.length - 1] && (
                <Separator className="ml-11" />
              )}
            </div>
          );
        })}
        
        {sharingInfo.is_owner && (
          <div className="pt-2 border-t">
            <p className="text-xs text-muted-foreground">
              You are the owner of this recording and can manage sharing permissions.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
