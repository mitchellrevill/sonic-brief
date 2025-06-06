import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Label } from "@/components/ui/label";
import { Loader2, Mic, Bot } from "lucide-react";
import { toast } from "sonner";
import { updateUserTranscriptionMethod } from "@/lib/api";
import type { User } from "@/lib/api";

interface TranscriptionMethodDialogProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  onUpdate?: () => void;
}

export function TranscriptionMethodDialog({ 
  isOpen, 
  onClose, 
  user,
  onUpdate 
}: TranscriptionMethodDialogProps) {
  const [transcriptionMethod, setTranscriptionMethod] = useState<"AZURE_AI_SPEECH" | "GPT4O_AUDIO">(
    user.transcription_method || "AZURE_AI_SPEECH"
  );
  const [isUpdating, setIsUpdating] = useState(false);

  const handleSave = async () => {
    if (!transcriptionMethod) return;

    setIsUpdating(true);
    try {
      await updateUserTranscriptionMethod(String(user.id), transcriptionMethod);
      toast.success("Transcription method updated successfully");
      onUpdate?.();
      onClose();
    } catch (error) {
      console.error("Error updating transcription method:", error);
      toast.error(error instanceof Error ? error.message : "Failed to update transcription method");
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mic className="h-5 w-5 text-primary" />
            Update Transcription Method
          </DialogTitle>
          <DialogDescription>
            Choose the transcription method for {user.email}. This setting will apply to all new audio recordings.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="transcription-method">Transcription Method</Label>
            <Select 
              value={transcriptionMethod} 
              onValueChange={(value) => setTranscriptionMethod(value as "AZURE_AI_SPEECH" | "GPT4O_AUDIO")}
            >
              <SelectTrigger id="transcription-method">
                <SelectValue placeholder="Select transcription method" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="AZURE_AI_SPEECH">
                  <div className="flex items-center gap-2">
                    <Mic className="h-4 w-4 text-blue-500" />
                    <div className="flex flex-col items-start">
                      <span className="font-medium">Azure AI Speech</span>
                      <span className="text-xs text-muted-foreground">
                        Traditional speech-to-text service
                      </span>
                    </div>
                  </div>
                </SelectItem>
                <SelectItem value="GPT4O_AUDIO">
                  <div className="flex items-center gap-2">
                    <Bot className="h-4 w-4 text-green-500" />
                    <div className="flex flex-col items-start">
                      <span className="font-medium">GPT-4o Audio Preview</span>
                      <span className="text-xs text-muted-foreground">
                        Advanced AI transcription with context understanding
                      </span>
                    </div>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
            <p className="font-medium mb-1">Current setting:</p>
            <div className="flex items-center gap-2">
              {user.transcription_method === "GPT4O_AUDIO" ? (
                <Bot className="h-4 w-4 text-green-500" />
              ) : (
                <Mic className="h-4 w-4 text-blue-500" />
              )}
              <span>
                {user.transcription_method === "GPT4O_AUDIO" 
                  ? "GPT-4o Audio Preview" 
                  : "Azure AI Speech"}
              </span>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isUpdating}>
            Cancel
          </Button>
          <Button 
            onClick={handleSave} 
            disabled={isUpdating || transcriptionMethod === user.transcription_method}
          >
            {isUpdating ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Updating...
              </>
            ) : (
              "Update Method"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
