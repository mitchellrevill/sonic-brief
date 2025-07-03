import { useState, useRef, useEffect } from "react";
// Utility to detect iOS
function isIOS() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
}
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Mic, 
  Square, 
  Play, 
  Pause, 
  Upload, 
  ArrowLeft, 
  Clock,
  Check,
  AlertCircle,
  Eye
} from "lucide-react";
import { uploadFile, fetchAudioBlob } from "@/lib/api";
import { toast } from "sonner";
import { useRouter } from "@tanstack/react-router";

interface RecordingInterfaceProps {
  categoryId: string;
  subcategoryId: string;
  categoryName: string;
  subcategoryName: string;
  onBack: () => void;
  onUploadComplete: () => void;
}

export function RecordingInterface({ 
  categoryId, 
  subcategoryId, 
  categoryName, 
  subcategoryName, 
  onBack,
  onUploadComplete 
}: RecordingInterfaceProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);

  const router = useRouter();
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Timer effect
  useEffect(() => {
    if (isRecording && !isPaused) {
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isRecording, isPaused]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      mediaRecorderRef.current = new MediaRecorder(stream);
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunks.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: "audio/webm" });
        const url = URL.createObjectURL(audioBlob);
        setAudioURL(url);
        
        // Stop all tracks to release microphone
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setIsPaused(false);
      setRecordingTime(0);
      
      toast.success("Recording started");
    } catch (error) {
      console.error("Error starting recording:", error);
      toast.error("Failed to start recording. Please check microphone permissions.");
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      toast.info("Recording paused");
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      toast.info("Recording resumed");
    }
  };
  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      setIsPaused(false);
      toast.success("Recording completed");
    }
  };
  const uploadRecording = async () => {
    if (!audioURL) return;

    setIsUploading(true);
    try {
      // Convert URL to File
      const blob = await fetchAudioBlob(audioURL);
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
      const fileName = `recording-${timestamp}.webm`;
      const file = new File([blob], fileName, { type: "audio/webm" });

      const uploadResponse = await uploadFile(file, categoryId, subcategoryId);
      
      // Capture the job ID from the response
      if (uploadResponse?.job_id) {
        setJobId(uploadResponse.job_id);
      }
      
      setUploadSuccess(true);
      toast.success("Recording uploaded successfully!");
      
    } catch (error) {
      console.error("Error uploading recording:", error);
      toast.error("Failed to upload recording. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };  const resetRecording = () => {
    setAudioURL(null);
    setRecordingTime(0);
    setUploadSuccess(false);
    setJobId(null);
    audioChunks.current = [];
    if (audioRef.current) {
      audioRef.current.currentTime = 0;
    }
  };
  if (uploadSuccess) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-2 border-green-200">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <Check className="w-8 h-8 text-green-600" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-foreground">Upload Successful!</h3>
                <p className="text-muted-foreground">Your recording has been submitted for processing.</p>
              </div>
              <div className="space-y-3">                {jobId && (
                  <Button 
                    onClick={() => router.navigate({ to: `/audio-recordings/${jobId}` })}
                    variant="outline"
                    className="w-full"
                  >
                    <Eye className="w-4 h-4 mr-2" />
                    View Details
                  </Button>
                )}
                <Button onClick={onUploadComplete} className="w-full">
                  Record Another
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="flex items-center space-x-4 mb-6">
          <Button 
            variant="ghost" 
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-xl font-semibold">Record Meeting</h1>
            <p className="text-sm text-muted-foreground">{categoryName} • {subcategoryName}</p>
          </div>
        </div>

        {/* Recording Status */}
        <Card className="mb-6">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">              {/* Recording Button/Indicator */}
              <Button
                onClick={isRecording ? stopRecording : !audioURL ? startRecording : undefined}
                disabled={audioURL !== null && !isRecording}
                className={`w-24 h-24 rounded-full p-0 border-4 transition-all duration-200 ${
                  isRecording 
                    ? isPaused 
                      ? 'bg-orange-500 hover:bg-orange-600 border-orange-300 animate-none' 
                      : 'bg-red-500 hover:bg-red-600 border-red-300 animate-pulse'
                    : audioURL
                      ? 'bg-gray-400 border-gray-300 cursor-not-allowed'
                      : 'bg-green-500 hover:bg-green-600 border-green-300'
                }`}
              >
                {isRecording ? (
                  <Square className="w-12 h-12 text-white" />
                ) : (
                  <Mic className="w-12 h-12 text-white" />
                )}
              </Button>

              {/* Timer */}
              <div className="space-y-2">
                <div className="flex items-center justify-center space-x-2">
                  <Clock className="w-4 h-4 text-muted-foreground" />
                  <span className="text-2xl font-mono font-medium">
                    {formatTime(recordingTime)}
                  </span>
                </div>
                  {/* Status text */}
                <div className="text-sm">
                  {!isRecording && !audioURL && (
                    <span className="text-muted-foreground">Tap to start recording</span>
                  )}
                  {isRecording && !isPaused && (
                    <span className="text-red-600 font-medium">Recording... Tap to stop</span>
                  )}
                  {isRecording && isPaused && (
                    <span className="text-orange-600 font-medium">Paused - Tap to stop</span>
                  )}
                  {!isRecording && audioURL && (
                    <span className="text-green-600 font-medium">Recording complete</span>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>        {/* Recording Controls */}
        {isRecording && (
          <div className="mb-6">
            <Button 
              onClick={isPaused ? resumeRecording : pauseRecording}
              variant="outline"
              className="w-full h-16 text-lg"
              size="lg"
            >
              {isPaused ? (
                <>
                  <Play className="w-6 h-6 mr-2" />
                  Resume Recording
                </>
              ) : (
                <>
                  <Pause className="w-6 h-6 mr-2" />
                  Pause Recording
                </>
              )}
            </Button>
          </div>
        )}

        {/* Playback and Upload */}
        {audioURL && !isRecording && (
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recording Playback</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Duration:</span>
                  <Badge variant="outline">{formatTime(recordingTime)}</Badge>
                </div>
                {isIOS() ? (
                  <div className="p-2 bg-orange-50 border border-orange-200 rounded text-orange-700 text-xs text-center">
                    Playback not supported on iOS
                  </div>
                ) : (
                  <audio 
                    ref={audioRef}
                    src={audioURL} 
                    className="w-full"
                    controls
                  />
                )}
                <div className="grid grid-cols-2 gap-3">
                  <Button 
                    onClick={resetRecording}
                    variant="outline"
                    className="h-12"
                  >
                    Record Again
                  </Button>
                  <Button 
                    onClick={uploadRecording}
                    disabled={isUploading}
                    className="h-12 bg-green-600 hover:bg-green-700"
                  >
                    {isUploading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Uploading...
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 mr-2" />
                        Submit Recording
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        <Alert className="mt-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="text-sm">
            <strong>Tips:</strong> Find a quiet space, speak clearly, and keep your device close to the speaker for best results.
          </AlertDescription>
        </Alert>

        {/* Upload existing recording footnote */}
        <div className="mt-4 text-center">
          <p className="text-xs text-muted-foreground">
            Have an existing recording?{" "}
            <button
              onClick={() => router.navigate({ to: "/audio-upload" })}
              className="text-primary underline hover:text-primary/80 transition-colors"
            >
              Upload it here
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
