import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { Button } from "@/components/ui/button";
import { 
  Upload, 
  Mic, 
  FileText, 
  Film, 
  Music, 
  FileAudio,
  Image,
  File
} from "lucide-react";

interface MediaUploadHeaderProps {
  onStartRecording?: () => void;
  isRecording?: boolean;
}

export function MediaUploadHeader({ 
  onStartRecording, 
  isRecording = false 
}: MediaUploadHeaderProps) {
  return (
    <div className="border-b bg-card/50">
      <div className="container mx-auto px-4 py-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-2 text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-3">
              <div className="flex items-center gap-1">
                <Upload className="h-6 w-6 text-primary" />
                <FileAudio className="h-5 w-5 text-muted-foreground" />
                <Film className="h-5 w-5 text-muted-foreground" />
                <FileText className="h-5 w-5 text-muted-foreground" />
              </div>
              <h1 className="text-2xl md:text-3xl font-bold tracking-tight">
                Media Upload
              </h1>
            </div>
              <SmartBreadcrumb
              items={[{ label: "Media Upload", isCurrentPage: true }]}
              className="justify-center md:justify-start"
            />
            
            <div className="space-y-2">
              <p className="text-muted-foreground text-sm md:text-base max-w-2xl">
                Upload audio, video, documents, transcripts, or record directly. 
                All file types are processed for analysis and insights.
              </p>
              
              <div className="flex flex-wrap gap-2 justify-center md:justify-start text-xs">
                <div className="flex items-center gap-1 px-2 py-1 bg-muted rounded-md">
                  <Music className="h-3 w-3" />
                  Audio
                </div>
                <div className="flex items-center gap-1 px-2 py-1 bg-muted rounded-md">
                  <Film className="h-3 w-3" />
                  Video
                </div>
                <div className="flex items-center gap-1 px-2 py-1 bg-muted rounded-md">
                  <FileText className="h-3 w-3" />
                  Documents
                </div>
                <div className="flex items-center gap-1 px-2 py-1 bg-muted rounded-md">
                  <File className="h-3 w-3" />
                  Transcripts
                </div>
                <div className="flex items-center gap-1 px-2 py-1 bg-muted rounded-md">
                  <Image className="h-3 w-3" />
                  Images
                </div>
              </div>
            </div>
          </div>
          
          {onStartRecording && (
            <div className="flex justify-center md:justify-end">
              <Button 
                onClick={onStartRecording}
                disabled={isRecording}
                size="lg"
                className="flex items-center gap-2 min-w-[160px]"
              >
                <Mic className={`h-4 w-4 ${isRecording ? 'animate-pulse text-red-500' : ''}`} />
                {isRecording ? 'Recording...' : 'Start Recording'}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
