import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Clock, Download, Trash2, AlertCircle } from "lucide-react";
import { formatDistance } from "date-fns";
import type { DraftRecording } from "@/lib/draft-storage";
import { formatBytes } from "@/lib/draft-storage";

interface DraftRestorationBannerProps {
  draft: DraftRecording;
  onRestore: () => void;
  onDiscard: () => void;
  onDownload: () => void;
  isRestoring?: boolean;
}

export function DraftRestorationBanner({
  draft,
  onRestore,
  onDiscard,
  onDownload,
  isRestoring = false,
}: DraftRestorationBannerProps) {
  const draftAge = formatDistance(new Date(draft.timestamp), new Date(), { addSuffix: true });
  const draftSize = formatBytes(draft.audioBlob.size);
  const draftDuration = Math.floor(draft.duration / 60);

  return (
    <Alert className="mb-6 border-2 border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950/30">
      <AlertCircle className="h-5 w-5 text-blue-600 dark:text-blue-400" />
      <AlertTitle className="text-blue-900 dark:text-blue-100 font-semibold">
        Draft Recording Found
      </AlertTitle>
      <AlertDescription className="space-y-4">
        <div className="text-blue-800 dark:text-blue-200">
          You have an unsaved recording for <strong>{draft.categoryName}</strong> • <strong>{draft.subcategoryName}</strong>
        </div>
        
        <div className="flex flex-wrap gap-2 text-sm text-blue-700 dark:text-blue-300">
          <div className="flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" />
            <span>Saved {draftAge}</span>
          </div>
          <span className="text-blue-400">•</span>
          <span>{draftDuration}:{(draft.duration % 60).toString().padStart(2, '0')} duration</span>
          <span className="text-blue-400">•</span>
          <span>{draftSize}</span>
        </div>

        <div className="flex flex-wrap gap-2 pt-2">
          <Button
            onClick={onRestore}
            disabled={isRestoring}
            size="sm"
            className="bg-blue-600 hover:bg-blue-700 text-white dark:bg-blue-500 dark:hover:bg-blue-600"
          >
            {isRestoring ? (
              <>
                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white mr-2"></div>
                Restoring...
              </>
            ) : (
              "Restore Draft"
            )}
          </Button>
          
          <Button
            onClick={onDownload}
            variant="outline"
            size="sm"
            className="border-blue-300 text-blue-700 hover:bg-blue-100 dark:border-blue-700 dark:text-blue-300 dark:hover:bg-blue-900/50"
          >
            <Download className="h-3.5 w-3.5 mr-1.5" />
            Download
          </Button>
          
          <Button
            onClick={onDiscard}
            variant="outline"
            size="sm"
            className="border-red-300 text-red-700 hover:bg-red-50 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950/50"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Discard
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}
