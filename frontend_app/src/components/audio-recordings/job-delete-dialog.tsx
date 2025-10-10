import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { fileToasts } from "@/lib/toast-utils";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Loader2, Trash2, AlertTriangle } from "lucide-react";
import { softDeleteJob } from "@/lib/api";

interface JobDeleteDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  jobId: string;
  jobTitle?: string;
  onDeleteSuccess?: () => void;
}

export function JobDeleteDialog({
  isOpen,
  onOpenChange,
  jobId,
  jobTitle = "Recording",
  onDeleteSuccess,
}: JobDeleteDialogProps) {  const queryClient = useQueryClient();
  const [isDeleting, setIsDeleting] = useState(false);
  const deleteJobMutation = useMutation({
    mutationFn: () => softDeleteJob(jobId),
    onSuccess: () => {
      fileToasts.deleted(jobTitle);
      queryClient.invalidateQueries({ queryKey: ["audioRecordings"] });
      queryClient.invalidateQueries({ queryKey: ["sharedJobs"] });
      // Ensure dialog is closed after successful deletion
      onOpenChange(false);
      
      // Call the optional success callback
      if (onDeleteSuccess) {
        onDeleteSuccess();
      }
    },
    onError: (error) => {
      toast.error(`Failed to delete ${jobTitle}`, {
        description: error.message
      });
      // Make sure we reset the deleting state in case of error
      setIsDeleting(false);
    },
    onMutate: () => {
      setIsDeleting(true);
    },
    onSettled: () => {
      setIsDeleting(false);
    },
  });

  const handleDelete = () => {
    deleteJobMutation.mutate();
  };
  return (
    <AlertDialog 
      open={isOpen} 
      onOpenChange={(open) => {
        // Prevent dialog state changes while deletion is in progress
        if (isDeleting && !open) return;
        onOpenChange(open);
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-destructive/10 text-destructive">
              <AlertTriangle className="h-6 w-6" />
            </div>
            <div>
              <AlertDialogTitle>Delete Recording</AlertDialogTitle>
              <AlertDialogDescription className="text-left">
                Are you sure you want to delete "{jobTitle}"?
              </AlertDialogDescription>
            </div>
          </div>
        </AlertDialogHeader>
        
        <div className="py-4">
          <div className="rounded-md bg-blue-50 p-4 border border-blue-200">
            <div className="flex items-start gap-3">
              <div className="p-1 rounded-full bg-blue-100 text-blue-600 mt-0.5">
                <Trash2 className="h-4 w-4" />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-blue-900">
                  This will be a soft delete
                </p>
                <p className="text-sm text-blue-700">
                  The recording will be removed from your account but can be recovered by administrators if needed.
                  Your data is never permanently lost without explicit action.
                </p>
              </div>
            </div>
          </div>
        </div>        <AlertDialogFooter>
          <AlertDialogCancel disabled={isDeleting}>
            Cancel
          </AlertDialogCancel>          <AlertDialogAction
            onClick={(e) => {
              e.preventDefault(); // Prevent default to handle deletion manually
              handleDelete();
            }}
            disabled={isDeleting}
            className="bg-destructive text-white font-medium hover:bg-destructive/90"
          >
            {isDeleting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                <span className="text-white">Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="mr-2 h-4 w-4" />
                <span className="text-white">Delete Recording</span>
              </>
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
