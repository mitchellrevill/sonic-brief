import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { getFileNameFromPath } from "@/lib/file-utils";
import { 
  Eye, 
  MoreVertical,
  Play,
  Download,
  RefreshCcw,
  Calendar,
  FileAudio,
  User,
  Hash,
  Trash2
} from "lucide-react";

export interface AudioRecordingCardProps {
  recording: {
    id: string;
    file_name?: string;
    file_path: string;
    status: "completed" | "processing" | "uploaded" | "failed" | "error";
    created_at: number;
    user_id?: string;
  };
  onViewDetails: () => void;
  onPlay?: () => void;
  onDownload?: () => void;
  onRetryProcessing?: () => void;
  onShare?: () => void;
  onDelete?: () => void;
  className?: string;
}

export function AudioRecordingCard({
  recording,
  onViewDetails,
  onPlay,
  onDownload,
  onRetryProcessing,
  onShare,
  onDelete,
  className,
}: AudioRecordingCardProps) {  const fileName = recording.file_name || 
    getFileNameFromPath(recording.file_path) || 
    "Unnamed Recording";

  const formattedDate = new Date(parseInt(recording.created_at.toString())).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  const formattedTime = new Date(parseInt(recording.created_at.toString())).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true
  });

  return (
    <Card className={cn(
      "group transition-all duration-200 hover:shadow-lg hover:shadow-black/5 border border-border/50 hover:border-border bg-card/50 backdrop-blur-sm",
      className
    )}>
      <CardContent className="p-4 space-y-4">
        {/* Header with Title and Status */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <FileAudio className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              <h3 className="font-semibold text-sm leading-tight line-clamp-2">
                {fileName}
              </h3>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Hash className="h-3 w-3" />
              <span className="font-mono">{recording.id.slice(0, 8)}...</span>
            </div>
          </div>
          <StatusBadge 
            status={recording.status} 
            size="sm"
            showIcon={true}
            animate={recording.status === "processing"}
          />
        </div>

        {/* Metadata */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Calendar className="h-3 w-3" />
            <span>{formattedDate} at {formattedTime}</span>
          </div>
          {recording.user_id && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <User className="h-3 w-3" />
              <span className="font-mono">{recording.user_id.slice(0, 8)}...</span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between pt-2 border-t border-border/50">
          <div className="flex items-center gap-2">
            {onPlay && (
              <Button
                variant="outline"
                size="sm"
                onClick={onPlay}
                className="h-8 px-3"
              >
                <Play className="h-3.5 w-3.5 mr-1.5" />
                Play
              </Button>
            )}
            <Button
              variant="default"
              size="sm"
              onClick={onViewDetails}
              className="h-8 px-3"
            >
              <Eye className="h-3.5 w-3.5 mr-1.5" />
              View
            </Button>
            {onShare && (
              <Button
                variant="outline"
                size="sm"
                onClick={onShare}
                className="h-8 px-3"
              >
                <User className="h-3.5 w-3.5 mr-1.5" />
                Share
              </Button>
            )}
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="h-8 w-8 p-0"
              >
                <MoreVertical className="h-4 w-4" />
                <span className="sr-only">Open menu</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuLabel>Actions</DropdownMenuLabel>
              <DropdownMenuItem onClick={onViewDetails}>
                <Eye className="mr-2 h-4 w-4" />
                View Details
              </DropdownMenuItem>
              {onShare && (
                <DropdownMenuItem onClick={onShare}>
                  <User className="mr-2 h-4 w-4" />
                  Share
                </DropdownMenuItem>
              )}
              {onDownload && (
                <DropdownMenuItem onClick={onDownload}>
                  <Download className="mr-2 h-4 w-4" />
                  Download
                </DropdownMenuItem>
              )}
              {recording.status === "uploaded" && onRetryProcessing && (
                <DropdownMenuItem onClick={onRetryProcessing}>
                  <RefreshCcw className="mr-2 h-4 w-4" />
                  Retry Processing
                </DropdownMenuItem>
              )}
              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem 
                    onClick={onDelete}
                    className="text-destructive focus:text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>
    </Card>
  );
}
