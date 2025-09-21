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
import { EditableDisplayName } from "@/components/ui/editable-display-name";
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
import { Link } from "@tanstack/react-router";

export interface AudioRecordingCardProps {
  recording: {
    id: string;
    displayname?: string;
    display_name?: string;
    file_name?: string;
    filename?: string;
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
}: AudioRecordingCardProps) {

  // Local date parsing helper to support numeric timestamps and ISO strings
  function parseDateLocal(input: string | number | undefined | null): Date | null {
    if (input === undefined || input === null || input === "") return null;
    if (typeof input === "number") {
      if (input < 1e12) return new Date(input * 1000);
      return new Date(input);
    }
    if (/^\d+$/.test(String(input))) {
      const n = parseInt(String(input), 10);
      if (n < 1e12) return new Date(n * 1000);
      return new Date(n);
    }
    const d = new Date(String(input));
    return isNaN(d.getTime()) ? null : d;
  }

  const _date = parseDateLocal(recording.created_at);
  const formattedDate = _date
    ? _date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
    : "-";

  const formattedTime = _date
    ? _date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true })
    : "-";

  return (
    <Card className={cn(
      "group transition-all duration-200 hover:shadow-lg hover:shadow-black/5 border border-border/50 hover:border-border bg-card/50 backdrop-blur-sm h-full flex flex-col",
      className
    )}>
      <CardContent className="p-4 space-y-4 flex flex-col h-full justify-between">
        {/* Header with Title and Status */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex items-center gap-2">
              <FileAudio className="h-4 w-4 text-muted-foreground flex-shrink-0" />
              <EditableDisplayName 
                job={recording}
                className="font-semibold text-sm leading-tight line-clamp-2 min-w-0 flex-1"
              />
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

        {/* Action Buttons - responsive: text buttons on lg+ and icon-only on small/medium */}
        <div className="flex flex-wrap items-center justify-between pt-2 border-t border-border/50">
          <div className="flex flex-wrap items-center gap-2 min-w-0">
            <div className="flex items-center gap-2 flex-shrink-0">
              {onPlay && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onPlay}
                  className="h-8 px-2 lg:px-3 min-w-0 flex items-center gap-2"
                >
                  <Play className="h-3.5 w-3.5" />
                  <span className="hidden lg:inline-block truncate">Play</span>
                </Button>
              )}

              <Link to="/audio-recordings/$id" params={{ id: recording.id }} className="min-w-0">
                <Button
                  variant="default"
                  size="sm"
                  className="h-8 px-2 lg:px-3 min-w-0 flex items-center gap-2"
                >
                  <Eye className="h-3.5 w-3.5" />
                  <span className="hidden lg:inline-block truncate">View</span>
                </Button>
              </Link>

              {onShare && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onShare}
                  className="h-8 px-2 lg:px-3 min-w-0 flex items-center gap-2"
                >
                  <User className="h-3.5 w-3.5" />
                  <span className="hidden lg:inline-block truncate">Share</span>
                </Button>
              )}
            </div>
          </div>

          <div className="flex items-center">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
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
                    <DropdownMenuItem onClick={onDelete} className="text-destructive focus:text-destructive">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </DropdownMenuItem>
                  </>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
