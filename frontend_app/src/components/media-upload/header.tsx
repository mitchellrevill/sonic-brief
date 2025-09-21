import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { Button } from "@/components/ui/button";
import { Upload, Mic, FileText, Film, Music, Image, File } from "lucide-react";

interface MediaUploadHeaderProps {
  onStartRecording?: () => void;
  isRecording?: boolean;
}

export function MediaUploadHeader({ onStartRecording, isRecording = false }: MediaUploadHeaderProps) {
  return (
    <header className="rounded-xl border bg-card px-4 py-6 md:py-7">
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <span className="p-2 rounded-md bg-muted text-primary">
              <Upload className="h-5 w-5" />
            </span>
            <h1 className="text-2xl md:text-3xl font-semibold tracking-tight">Media Upload</h1>
          </div>
          <SmartBreadcrumb items={[{ label: 'Media Upload', isCurrentPage: true }]} className="hidden md:flex" />
          <p className="text-sm text-muted-foreground max-w-2xl">Upload or record media for transcription and analysis.</p>
          <div className="flex flex-wrap gap-1.5">
            {[{icon: Music, label:'Audio'},{icon: Film,label:'Video'},{icon: FileText,label:'Docs'},{icon: File,label:'Transcripts'},{icon: Image,label:'Images'}].map(b => (
              <span key={b.label} className="inline-flex items-center gap-1 rounded-md bg-muted px-2 py-1 text-[11px] font-medium">
                <b.icon className="h-3.5 w-3.5" /> {b.label}
              </span>
            ))}
          </div>
        </div>
        {onStartRecording && (
          <div className="flex items-start md:items-end">
            <Button
              onClick={onStartRecording}
              disabled={isRecording}
              size="sm"
              className="rounded-md"
            >
              <Mic className={`h-4 w-4 mr-2 ${isRecording ? 'animate-pulse text-red-500' : ''}`} />
              {isRecording ? 'Recording...' : 'Start Recording'}
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}
