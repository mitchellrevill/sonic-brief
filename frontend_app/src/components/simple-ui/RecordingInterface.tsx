import { useState, useRef, useEffect } from "react";
// Utility to detect iOS
function isIOS() {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false;
  return /iPad|iPhone|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
}
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarkdownRenderer } from "./MarkdownRenderer";
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
  Eye,
  ChevronLeft,
  ChevronRight,
  MessageSquare
} from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { uploadFile, fetchAudioBlob } from "@/lib/api";
import { convertToWavWithFFmpeg } from "@/lib/ffmpegConvert";
import { toast } from "sonner";
import { useRouter } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { fetchSubcategories, type SubcategoryResponse } from "@/api/prompt-management";

interface RecordingInterfaceProps {
  categoryId: string;
  subcategoryId: string;
  categoryName: string;
  subcategoryName: string;
  preSessionData?: Record<string, any>;
  onBack: () => void;
  onUploadComplete: () => void;
}

export function RecordingInterface(props: RecordingInterfaceProps) {
  const { categoryId, subcategoryId, categoryName, subcategoryName, preSessionData = {}, onBack, onUploadComplete } = props;
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  // FFmpeg conversion state
  const [isConverting, setIsConverting] = useState(false);
  const [conversionProgress, setConversionProgress] = useState(0);
  const [conversionStep, setConversionStep] = useState("");
  // Talking points state
  const [currentTalkingPointIndex, setCurrentTalkingPointIndex] = useState(0);

  // Fetch subcategory to get in-session talking points
  const { data: subcategories } = useQuery({
    queryKey: ['subcategories'],
    queryFn: () => fetchSubcategories(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  const currentSubcategory = (subcategories as SubcategoryResponse[])?.find(sub => sub.id === subcategoryId);
  const inSessionTalkingPoints = currentSubcategory?.inSessionTalkingPoints || [];
  
  // Flatten talking points for easy navigation
  const allTalkingPoints = inSessionTalkingPoints.flatMap((section: any) => 
    section.fields || []
  );

  // Only log pre-session data in development and only when it changes
  useEffect(() => {
    if (import.meta.env.DEV) {
      console.debug('Pre-session data received:', preSessionData);
    }
  }, [preSessionData]);

  const nextTalkingPoint = () => {
    if (currentTalkingPointIndex < allTalkingPoints.length - 1) {
      setCurrentTalkingPointIndex(prev => prev + 1);
    }
  };

  const prevTalkingPoint = () => {
    if (currentTalkingPointIndex > 0) {
      setCurrentTalkingPointIndex(prev => prev - 1);
    }
  };

  // TalkingPointsDisplay component
  const TalkingPointsDisplay = () => {
    if (!allTalkingPoints.length) return null;

    const currentPoint = allTalkingPoints[currentTalkingPointIndex];

    return (
      <Card className="mb-6 border-gray-200 bg-gray-50 backdrop-blur-sm border-2 shadow-lg">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-sm sm:text-base font-semibold">
              <MessageSquare className="h-4 w-4 sm:h-5 sm:w-5 text-gray-600" />
              <span className="truncate">
                Talking Points ({currentTalkingPointIndex + 1} of {allTalkingPoints.length})
              </span>
            </CardTitle>
            <div className="flex gap-1 sm:gap-2 flex-shrink-0">
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-full border-gray-200 hover:bg-gray-100 hover:border-gray-300 transition-all duration-200 touch-manipulation"
                onClick={prevTalkingPoint}
                disabled={currentTalkingPointIndex === 0}
                aria-label="Previous talking point"
                style={{ touchAction: 'manipulation' }}
              >
                <ChevronLeft className="h-3 w-3 sm:h-4 sm:w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8 sm:h-9 sm:w-9 rounded-full border-gray-200 hover:bg-gray-100 hover:border-gray-300 transition-all duration-200 touch-manipulation"
                onClick={nextTalkingPoint}
                disabled={currentTalkingPointIndex === allTalkingPoints.length - 1}
                aria-label="Next talking point"
                style={{ touchAction: 'manipulation' }}
              >
                <ChevronRight className="h-3 w-3 sm:h-4 sm:w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="space-y-3">
            <div className="font-semibold text-gray-900">
              {currentPoint?.name || `Point ${currentTalkingPointIndex + 1}`}
            </div>
            <div className="text-gray-800 leading-relaxed">
              {currentPoint?.type === 'markdown' && currentPoint?.value ? (
                <MarkdownRenderer content={currentPoint.value} />
              ) : (
                currentPoint?.value || 'No content available'
              )}
            </div>
            {currentPoint?.type && currentPoint.type !== 'text' && (
              <Badge variant="secondary" className="text-xs bg-gray-100 text-gray-700">
                {currentPoint.type}
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

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

      // clear any previous chunks
      audioChunks.current = [];
      setAudioURL(null);

      const mr = new MediaRecorder(stream);
      mediaRecorderRef.current = mr;
  console.debug('MediaRecorder created', { mr });

      mr.onstart = () => {
        setIsRecording(true);
        setIsPaused(false);
        setRecordingTime(0);
        toast.success("Recording started");
      };

      mr.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };

      mr.onpause = () => {
        setIsPaused(true);
      };

      mr.onresume = () => {
        setIsPaused(false);
      };

      mr.onstop = () => {
        try {
          const audioBlob = new Blob(audioChunks.current, { type: "audio/webm" });
          const url = URL.createObjectURL(audioBlob);
          setAudioURL(url);
        } catch (err) {
          console.error('Error creating audio blob:', err);
          toast.error('Could not create recording');
        }

        // release microphone tracks (guarded)
        if (streamRef.current) {
          try {
            streamRef.current.getTracks().forEach(track => track.stop());
          } catch (e) {
            console.warn('Error stopping tracks after onstop', e);
          }
        }
      };

      try {
        mr.start();
        console.debug('MediaRecorder started', { state: mr.state });
      } catch (startErr) {
        console.error('MediaRecorder.start() failed', startErr);
        toast.error('Unable to start recording on this device/browser.');
        // stop tracks if start failed
        if (streamRef.current) {
          try { streamRef.current.getTracks().forEach(t => t.stop()); } catch (e) { /* ignore */ }
        }
        mediaRecorderRef.current = null;
        return;
      }
    } catch (error) {
      console.error("Error starting recording:", error);
      toast.error("Failed to start recording. Please check microphone permissions.");
    }
  };

  const pauseRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === 'recording') {
      try {
        mr.pause();
        // onpause handler will update state
        toast.info("Recording paused");
      } catch (e) {
        console.warn('Pause failed', e);
      }
    }
  };

  const resumeRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state === 'paused') {
      try {
        mr.resume();
        // onresume handler will update state
        toast.info("Recording resumed");
      } catch (e) {
        console.warn('Resume failed', e);
      }
    }
  };
  const stopRecording = () => {
    const mr = mediaRecorderRef.current;
    console.debug('stopRecording invoked', { mrState: mr?.state, hasStream: !!streamRef.current });
    if (mr) {
      try {
        // If paused, resume first (some engines need this)
        if (mr.state === 'paused') {
          try { mr.resume(); console.debug('Resumed before stop'); } catch (e) { console.warn('resume before stop failed', e); }
        }

        if (mr.state === 'recording' || mr.state === 'paused') {
          try { mr.requestData(); } catch (e) { console.debug('requestData unsupported', e); }
          mr.stop();
          console.debug('mr.stop() called');
        } else if (mr.state === 'inactive') {
          console.debug('MediaRecorder already inactive');
        }
      } catch (e) {
        console.warn('MediaRecorder stop failed, falling back to track stop', e);
      }

      setIsRecording(false);
      setIsPaused(false);
      toast.success("Recording completed");

      // Ensure microphone tracks are stopped after a short delay to allow onstop to run
      setTimeout(() => {
        if (streamRef.current) {
          try {
            streamRef.current.getTracks().forEach(track => track.stop());
            console.debug('Tracks stopped in fallback');
          } catch (err) {
            console.warn('Error stopping tracks in fallback', err);
          }
        }
      }, 250);
      // Clear mediaRecorderRef to avoid reuse
      mediaRecorderRef.current = null;
    } else if (streamRef.current) {
      // Fallback: stop tracks if recorder not present
      try {
        streamRef.current.getTracks().forEach(track => track.stop());
        console.debug('Tracks stopped: recorder missing');
      } catch (err) {
        console.warn('Fallback stop tracks error', err);
      }
      setIsRecording(false);
      setIsPaused(false);
      toast.success("Recording stopped");
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

      // Convert to WAV before upload (show progress)
      setIsConverting(true);
      setConversionProgress(0);
      setConversionStep("Starting conversion...");
      const wavFile = await convertToWavWithFFmpeg(file, {
        setConversionProgress,
        setConversionStep,
      });
      setIsConverting(false);
      setConversionStep("");

      const uploadResponse = await uploadFile(wavFile, categoryId, subcategoryId, preSessionData);
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
      setIsConverting(false);
      setConversionStep("");
      setConversionProgress(0);
    }
  };

  // Reset recording state
  const resetRecording = () => {
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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <Card className="w-full max-w-md border-2 border-green-200 shadow-2xl bg-white">
          <CardContent className="pt-8 pb-8">
            <div className="text-center space-y-6">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto shadow-lg">
                <Check className="w-10 h-10 text-green-600" />
              </div>
              <div className="space-y-2">
                <h3 className="text-2xl font-bold text-green-600">
                  Upload Successful!
                </h3>
                <p className="text-slate-600 font-medium">Your recording has been submitted for processing.</p>
              </div>
              <div className="space-y-4">
                {jobId && (
                  <Button 
                    onClick={() => router.navigate({ to: `/audio-recordings/${jobId}` })}
                    variant="outline"
                    className="w-full h-12 sm:h-14 text-sm sm:text-base font-semibold border-2 border-gray-200 hover:bg-gray-50 hover:border-gray-300 touch-manipulation"
                    style={{ touchAction: 'manipulation' }}
                  >
                    <Eye className="w-4 h-4 sm:w-5 sm:h-5 mr-2 sm:mr-3" />
                    View Details
                  </Button>
                )}
                <Button 
                  onClick={onUploadComplete} 
                  className="w-full h-12 sm:h-14 text-sm sm:text-base font-semibold bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 shadow-lg hover:shadow-xl transition-all duration-200 touch-manipulation"
                  style={{ touchAction: 'manipulation' }}
                >
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
    <div className="min-h-screen bg-gradient-to-br from-green-50 via-white to-gray-50 p-4 sm:p-6">
      <div className="max-w-md mx-auto">
        {/* Header */}
        <div className="flex items-center space-x-3 sm:space-x-4 mb-6 sm:mb-8">
          <Button 
            variant="ghost" 
            onClick={onBack}
            className="text-muted-foreground hover:text-foreground hover:bg-white/50 rounded-full h-10 w-10 sm:h-12 sm:w-12 p-0 touch-manipulation"
          >
            <ArrowLeft className="w-5 h-5 sm:w-6 sm:h-6" />
          </Button>
          <div className="flex-1 min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold bg-gradient-to-r from-green-600 to-gray-600 bg-clip-text text-transparent truncate">
              Record Meeting
            </h1>
            <p className="text-sm text-slate-600 font-medium truncate">{categoryName} • {subcategoryName}</p>
          </div>
        </div>

        {/* Talking Points Display */}
        <TalkingPointsDisplay />

        {/* Recording Status */}
        <Card className="mb-6 shadow-xl border-2 bg-gradient-to-r from-white via-slate-50 to-white backdrop-blur-sm">
          <CardContent className="pt-8 pb-8">
            <div className="text-center space-y-6">
              {/* Recording Button/Indicator */}
              <div className="relative">
                <Button
                  onClick={isRecording ? stopRecording : !audioURL ? startRecording : undefined}
                  disabled={audioURL !== null && !isRecording}
                  className={`w-32 h-32 sm:w-36 sm:h-36 rounded-full p-0 border-4 transition-all duration-300 shadow-2xl transform hover:scale-105 active:scale-95 touch-manipulation relative z-10 ${
                    isRecording 
                      ? isPaused 
                        ? 'bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700 border-orange-300 shadow-orange-200' 
                        : 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-red-300 shadow-red-200'
                      : audioURL
                        ? 'bg-gradient-to-r from-gray-400 to-gray-500 border-gray-300 cursor-not-allowed shadow-gray-200'
                        : 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 border-green-300 shadow-green-200'
                  }`}
                  style={{ touchAction: 'manipulation' }}
                >
                  {isRecording ? (
                    <Square className="w-14 h-14 sm:w-16 sm:h-16 text-white drop-shadow-lg" />
                  ) : (
                    <Mic className="w-14 h-14 sm:w-16 sm:h-16 text-white drop-shadow-lg" />
                  )}
                </Button>
                {/* Recording indicator ring */}
                {isRecording && !isPaused && (
                  <div className="absolute inset-0 rounded-full border-4 border-red-200 pointer-events-none -z-0" aria-hidden="true"></div>
                )}
              </div>

              {/* Timer */}
              <div className="space-y-3">
                <div className="flex items-center justify-center space-x-3 bg-slate-100 rounded-full px-4 sm:px-6 py-2 sm:py-3 border-2 border-slate-200">
                  <Clock className="w-4 h-4 sm:w-5 sm:h-5 text-slate-600" />
                  <span className="text-2xl sm:text-3xl font-mono font-bold text-slate-800 tracking-wider">
                    {formatTime(recordingTime)}
                  </span>
                </div>
                {/* Status text */}
                <div className="text-sm sm:text-base font-medium px-2">
                  {!isRecording && !audioURL && (
                    <span className="text-slate-600">Tap the microphone to start recording</span>
                  )}
                  {isRecording && !isPaused && (
                    <span className="text-red-600 font-semibold">Recording in progress...</span>
                  )}
                  {isRecording && isPaused && (
                    <span className="text-orange-600 font-semibold">Recording paused</span>
                  )}
                  {!isRecording && audioURL && (
                    <span className="text-green-600 font-semibold flex items-center justify-center gap-2">
                      <Check className="w-4 h-4 sm:w-5 sm:h-5" />
                      Recording complete
                    </span>
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
              className="w-full h-14 sm:h-16 text-base sm:text-lg font-semibold bg-white hover:bg-slate-50 border-2 border-slate-200 hover:border-slate-300 shadow-lg hover:shadow-xl transition-all duration-200 touch-manipulation"
              size="lg"
              style={{ touchAction: 'manipulation' }}
            >
              {isPaused ? (
                <>
                  <Play className="w-5 h-5 sm:w-6 sm:h-6 mr-3 text-green-600" />
                  Resume Recording
                </>
              ) : (
                <>
                  <Pause className="w-5 h-5 sm:w-6 sm:h-6 mr-3 text-orange-600" />
                  Pause Recording
                </>
              )}
            </Button>
          </div>
        )}

        {/* Playback and Upload */}
        {audioURL && !isRecording && (
          <div className="space-y-6">
            <Card className="shadow-lg border-2 bg-gradient-to-r from-green-50 via-white to-gray-50">
              <CardHeader>
                <CardTitle className="text-xl font-semibold bg-gradient-to-r from-green-600 to-gray-600 bg-clip-text text-transparent">
                  Recording Playback
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 bg-slate-50 rounded-lg border">
                  <span className="text-sm font-medium text-slate-700">Duration:</span>
                  <Badge variant="outline" className="text-sm font-semibold px-3 py-1">
                    {formatTime(recordingTime)}
                  </Badge>
                </div>
                {isIOS() ? (
                  <div className="p-4 bg-gradient-to-r from-orange-50 to-yellow-50 border-2 border-orange-200 rounded-lg text-orange-700 text-sm text-center font-medium">
                    Playback not supported on iOS
                  </div>
                ) : (
                  <div className="p-4 bg-slate-50 rounded-lg border-2">
                    <audio 
                      ref={audioRef}
                      src={audioURL} 
                      className="w-full"
                      controls
                    />
                  </div>
                )}
                {/* FFmpeg conversion progress */}
                {(isConverting || conversionProgress > 0) && (
                  <div className="p-4 bg-gray-50 rounded-lg border-2 border-gray-200">
                    <div className="mb-2 text-sm font-medium text-gray-800">{conversionStep}</div>
                    <Progress value={conversionProgress} className="h-2" />
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <Button 
                    onClick={resetRecording}
                    variant="outline"
                    className="h-12 sm:h-14 text-sm sm:text-base font-semibold border-2 hover:bg-slate-50 hover:border-slate-300 touch-manipulation"
                    style={{ touchAction: 'manipulation' }}
                  >
                    Record Again
                  </Button>
                  <Button 
                    onClick={uploadRecording}
                    disabled={isUploading || isConverting}
                    className="h-12 sm:h-14 text-sm sm:text-base font-semibold bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 shadow-lg hover:shadow-xl transition-all duration-200 touch-manipulation"
                    style={{ touchAction: 'manipulation' }}
                  >
                    {isUploading || isConverting ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 sm:h-5 sm:w-5 border-b-2 border-white mr-2 sm:mr-3"></div>
                        {isConverting ? "Converting..." : "Uploading..."}
                      </>
                    ) : (
                      <>
                        <Upload className="w-4 h-4 sm:w-5 sm:h-5 mr-2 sm:mr-3" />
                        Submit Recording
                      </>
                    )}
                  </Button>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        <Alert className="mt-8 border-2 border-gray-200 bg-gradient-to-r from-gray-50 to-gray-100 shadow-sm">
          <AlertCircle className="h-5 w-5 text-blue-600" />
          <AlertDescription className="text-sm text-blue-800 font-medium">
            <strong className="text-blue-900">Tips:</strong> Find a quiet space, speak clearly, and keep your device close to the speaker for best results.
          </AlertDescription>
        </Alert>

        {/* Upload existing recording footnote */}
        <div className="mt-6 text-center">
          <p className="text-sm text-slate-600">
            Have an existing recording?{" "}
            <button
              onClick={() => router.navigate({ to: "/audio-upload" })}
              className="text-blue-600 underline hover:text-blue-700 font-medium transition-colors"
            >
              Upload it here
            </button>
          </p>
        </div>
      </div>

    </div>
  );
}
