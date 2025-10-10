import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { sharingToasts } from "@/lib/toast-utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Loader2, Share2, AlertCircle } from "lucide-react";
import { shareJob } from "@/lib/api";

const jobShareSchema = z.object({
  target_user_email: z.string().email("Please enter a valid email address"),
  permission_level: z.enum(["view", "edit", "admin"], {
    required_error: "Please select a permission level",
  }),
  message: z.string().optional(),
});

type JobShareFormData = z.infer<typeof jobShareSchema>;

interface JobShareDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  jobId: string;
  jobTitle?: string;
}

export function JobShareDialog({
  isOpen,
  onOpenChange,
  jobId,
  jobTitle = "Recording",
}: JobShareDialogProps) {
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<JobShareFormData>({
    resolver: zodResolver(jobShareSchema),
    defaultValues: {
      target_user_email: "",
      permission_level: "view",
      message: "",
    },
  });
  const shareJobMutation = useMutation({
    mutationFn: (data: JobShareFormData) => shareJob(jobId, data),    onSuccess: (_, variables) => {
      sharingToasts.granted(variables.target_user_email, jobTitle);
      queryClient.invalidateQueries({ queryKey: ["jobSharingInfo", jobId] });
      queryClient.invalidateQueries({ queryKey: ["sharedJobs"] });
      queryClient.invalidateQueries({ queryKey: ["audioRecordings"] });
      form.reset();
      onOpenChange(false);
    },
    onError: (error, variables) => {
      sharingToasts.failed(variables.target_user_email, error.message);
    },
  });

  const handleSubmit = async (data: JobShareFormData) => {
    setIsSubmitting(true);
    try {
      await shareJobMutation.mutateAsync(data);
    } catch (error) {
      // Error is handled by the mutation
    } finally {
      setIsSubmitting(false);
    }
  };

  const permissionDescriptions = {
    view: "Can view transcriptions and analysis results",
    edit: "Can view and edit transcription content", 
    admin: "Full access including sharing permissions",
  };

  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Share2 className="h-5 w-5 text-primary" />
            Share Recording
          </DialogTitle>
          <DialogDescription>
            Share "{jobTitle}" with another user and set their permission level.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="target_user_email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>User Email</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter user's email address"
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="permission_level"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Permission Level</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value} disabled={isSubmitting}>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select permission level" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="view">
                        <div className="flex flex-col items-start">
                          <span className="font-medium">View</span>
                          <span className="text-xs text-muted-foreground">
                            Can view transcriptions and analysis
                          </span>
                        </div>
                      </SelectItem>
                      <SelectItem value="edit">
                        <div className="flex flex-col items-start">
                          <span className="font-medium">Edit</span>
                          <span className="text-xs text-muted-foreground">
                            Can view and edit content
                          </span>
                        </div>
                      </SelectItem>
                      <SelectItem value="admin">
                        <div className="flex flex-col items-start">
                          <span className="font-medium">Admin</span>
                          <span className="text-xs text-muted-foreground">
                            Full access including sharing
                          </span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <FormDescription>
                    {form.watch("permission_level") && 
                      permissionDescriptions[form.watch("permission_level")]
                    }
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="message"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Message (Optional)</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Add a message for the recipient..."
                      className="resize-none"
                      rows={3}
                      {...field}
                      disabled={isSubmitting}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex items-center gap-3 pt-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isSubmitting}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isSubmitting}
                className="flex-1"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sharing...
                  </>
                ) : (
                  <>
                    <Share2 className="mr-2 h-4 w-4" />
                    Share
                  </>
                )}
              </Button>
            </div>
          </form>
        </Form>

        {shareJobMutation.error && (
          <div className="mt-4 p-3 bg-destructive/10 text-destructive rounded-md flex items-start gap-2 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-medium">Sharing failed</p>
              <p>{shareJobMutation.error.message}</p>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
