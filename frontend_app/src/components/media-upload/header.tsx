import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { useBreadcrumbs } from "@/hooks/use-breadcrumbs";
import { Button } from "@/components/ui/button";
import { Upload, Mic } from "lucide-react";

interface MediaUploadHeaderProps {
  onStartRecording?: () => void;
  isRecording?: boolean;
}

export function MediaUploadHeader({ onStartRecording, isRecording = false }: MediaUploadHeaderProps) {
  const breadcrumbs = useBreadcrumbs();

  return (
    <div>
      <div className="container mx-auto px-4 py-6">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-zinc-200/70 text-zinc-700 dark:bg-zinc-700/60 dark:text-zinc-100">
            <Upload className="h-6 w-6" />
          </div>
          <div className="space-y-1 flex-1">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-zinc-800 to-zinc-600 dark:from-zinc-200 dark:to-zinc-400 bg-clip-text text-transparent">
              Media Upload
            </h1>
            <SmartBreadcrumb items={breadcrumbs} />
            <p className="text-muted-foreground">
              Upload or record media for transcription and analysis
            </p>
          </div>
          {onStartRecording && (
            <Button
              onClick={onStartRecording}
              disabled={isRecording}
              size="sm"
              variant="outline"
            >
              <Mic className={`h-4 w-4 mr-2 ${isRecording ? 'text-red-500' : ''}`} />
              {isRecording ? 'Recording...' : 'Start Recording'}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
