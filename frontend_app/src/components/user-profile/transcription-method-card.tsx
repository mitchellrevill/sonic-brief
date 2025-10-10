import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Mic, Bot, Loader2, Settings } from "lucide-react";
import { toast } from "sonner";
import { settingsToasts } from "@/lib/toast-utils";
import { updateUserTranscriptionMethod } from "@/lib/api";
import type { FrontendUser } from "@/hooks/usePermissions";

interface TranscriptionMethodCardProps {
  user: FrontendUser;
}

export function TranscriptionMethodCard({ user }: TranscriptionMethodCardProps) {
  // Use the user's transcription_method if available, otherwise default
  const [transcriptionMethod, setTranscriptionMethod] = useState<"AZURE_AI_SPEECH" | "GPT4O_AUDIO">(
    user.transcription_method || "AZURE_AI_SPEECH"
  );
  const [isUpdating, setIsUpdating] = useState(false);

  const handleSave = async () => {
    if (!transcriptionMethod) return;

    setIsUpdating(true);
    try {
      await updateUserTranscriptionMethod(user.user_id, transcriptionMethod);
      settingsToasts.saved("Transcription method");
    } catch (error) {
      console.error("Error updating transcription method:", error);
      const errorMessage = error instanceof Error ? error.message : "Failed to update transcription method";
      settingsToasts.failed("transcription method");
      toast.error(errorMessage, { description: "Please try again" });
    } finally {
      setIsUpdating(false);
    }
  };
  const getMethodInfo = (method: "AZURE_AI_SPEECH" | "GPT4O_AUDIO") => {
    if (method === "GPT4O_AUDIO") {
      return {
        icon: Bot,
        name: "GPT-4o Audio Preview",
        description: "Advanced AI transcription with context understanding",
        color: "text-green-500"
      };
    }
    return {
      icon: Mic,
      name: "Azure AI Speech",
      description: "Traditional speech-to-text service",
      color: "text-blue-500"
    };
  };

  const currentMethod = getMethodInfo(transcriptionMethod);
  const CurrentIcon = currentMethod.icon;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Settings className="h-5 w-5" />
          Transcription Method
        </CardTitle>
        <CardDescription>
          Choose how your audio recordings will be transcribed
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current Method Display */}
        <div className="rounded-lg bg-muted/50 p-3">
          <p className="text-sm font-medium mb-2">Current method:</p>
          <div className="flex items-center gap-2">
            <CurrentIcon className={`h-4 w-4 ${currentMethod.color}`} />
            <div className="flex flex-col">
              <span className="text-sm font-medium">{currentMethod.name}</span>
              <span className="text-xs text-muted-foreground">{currentMethod.description}</span>
            </div>
          </div>
        </div>

        {/* Method Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Select transcription method:</label>
          <Select 
            value={transcriptionMethod} 
            onValueChange={(value) => setTranscriptionMethod(value as "AZURE_AI_SPEECH" | "GPT4O_AUDIO")}
            disabled={isUpdating}
          >
            <SelectTrigger>
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
        </div>        {/* Save Button */}
        <Button 
          onClick={handleSave} 
          disabled={isUpdating}
          className="w-full"
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

        <p className="text-xs text-muted-foreground">
          This setting will apply to all new audio recordings you create.
        </p>
      </CardContent>
    </Card>
  );
}
