import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Check, X, Edit3 } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { getDisplayName } from "@/lib/display-name-utils";
import { updateJobDisplayName } from "@/lib/api";

interface EditableDisplayNameProps {
  job: {
    id: string;
    displayname?: string;
    display_name?: string;
    file_name?: string;
    filename?: string;
    file_path?: string;
  };
  className?: string;
  showEditIcon?: boolean;
}

export function EditableDisplayName({ job, className = "", showEditIcon = true }: EditableDisplayNameProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const queryClient = useQueryClient();

  const displayName = getDisplayName(job);

  const updateJobMutation = useMutation({
    mutationFn: async (newDisplayName: string) => {
      return await updateJobDisplayName(job.id, newDisplayName);
    },
    onSuccess: () => {
      // Invalidate jobs queries to refresh the data
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      queryClient.invalidateQueries({ queryKey: ["job", job.id] });
      toast.success("Job name updated successfully");
      setIsEditing(false);
    },
    onError: () => {
      toast.error("Failed to update job name");
    },
  });

  const handleStartEdit = () => {
    setEditValue(displayName);
    setIsEditing(true);
  };

  const handleSave = () => {
    if (editValue.trim() && editValue !== displayName) {
      updateJobMutation.mutate(editValue.trim());
    } else {
      setIsEditing(false);
    }
  };

  const handleCancel = () => {
    setEditValue("");
    setIsEditing(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave();
    } else if (e.key === "Escape") {
      handleCancel();
    }
  };

  if (isEditing) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Input
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onKeyDown={handleKeyDown}
          className="h-8 text-sm text-foreground bg-background border-border"
          autoFocus
          maxLength={255}
        />
        <Button
          size="sm"
          variant="ghost"
          onClick={handleSave}
          disabled={updateJobMutation.isPending}
          className="h-8 w-8 p-0"
        >
          <Check className="h-4 w-4" />
        </Button>
        <Button
          size="sm"
          variant="ghost"
          onClick={handleCancel}
          disabled={updateJobMutation.isPending}
          className="h-8 w-8 p-0"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-2 group ${className}`}>
      <span className="truncate">{displayName}</span>
      {showEditIcon && (
        <Button
          size="sm"
          variant="ghost"
          onClick={handleStartEdit}
          className="h-6 w-6 p-0 opacity-0 group-hover:opacity-100 transition-opacity"
        >
          <Edit3 className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}