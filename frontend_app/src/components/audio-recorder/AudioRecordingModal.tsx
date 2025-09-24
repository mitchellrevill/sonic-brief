import { useRef, useState, useEffect } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Slider } from "@/components/ui/slider";
import { Mic, Square, Play, Pause, Volume2, VolumeX, RotateCcw, Check } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

interface AudioRecordingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRecordingComplete: (file: File) => void;
}

enum RecordingState {
  IDLE = "idle",
  RECORDING = "recording", 
  PAUSED = "paused",
  RECORDED = "recorded",
  PROCESSING = "processing"
}

function getRandomString(length = 8) {
  return Math.random().toString(36).substring(2, 2 + length);
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function AudioRecordingModal({ isOpen, onClose, onRecordingComplete }: AudioRecordingModalProps) {
  const [state, setState] = useState<RecordingState>(RecordingState.IDLE);
  const [audioURL, setAudioURL] = useState<string | null>(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [processingProgress, setProcessingProgress] = useState(0);
  
  // Playback controls
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(75);
  const [isMuted, setIsMuted] = useState(false);
    const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunks = useRef<Blob[]>([]);
  const audioRef = useRef<HTMLAudioElement>(null);
  const recordingTimerRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Clean up on unmount or close
  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
      if (audioURL) {
        URL.revokeObjectURL(audioURL);
      }
    };
  }, [audioURL]);

  // Audio player event handlers
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);

    // Set volume
    audio.volume = volume / 100;
    audio.muted = isMuted;

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
    };
  }, [audioURL, volume, isMuted]);
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      mediaRecorderRef.current = new MediaRecorder(stream);

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunks.current.push(event.data);
      };      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunks.current, { type: "audio/wav" });
        const url = URL.createObjectURL(audioBlob);
        setAudioURL(url);
        setState(RecordingState.RECORDED);
        
        // Stop all tracks to release microphone
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
          streamRef.current = null;
        }
        
        // Don't clear chunks here - we want to keep them for the final recording
      };

      mediaRecorderRef.current.start();
      setState(RecordingState.RECORDING);
      setRecordingDuration(0);
      
      // Start recording timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);

      toast.success("Recording started");
    } catch (error) {
      toast.error("Failed to access microphone");
      console.error("Error starting recording:", error);
    }
  };

  const pauseRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.pause();
      setState(RecordingState.PAUSED);
      
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }
      
      toast.success("Recording paused");
    }
  };

  const resumeRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
      mediaRecorderRef.current.resume();
      setState(RecordingState.RECORDING);
      
      // Resume recording timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration(prev => prev + 1);
      }, 1000);
      
      toast.success("Recording resumed");
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    
    toast.success("Recording completed");
  };

  const playPause = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play();
      setIsPlaying(true);
    }
  };

  const seek = (newTime: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  };

  const handleVolumeChange = (newVolume: number[]) => {
    const volumeValue = newVolume[0];
    setVolume(volumeValue);
    
    if (audioRef.current) {
      audioRef.current.volume = volumeValue / 100;
    }
  };

  const toggleMute = () => {
    setIsMuted(!isMuted);
    if (audioRef.current) {
      audioRef.current.muted = !isMuted;
    }
  };
  const resetRecording = () => {
    // Stop recording if in progress
    if (mediaRecorderRef.current && 
        (mediaRecorderRef.current.state === "recording" || mediaRecorderRef.current.state === "paused")) {
      mediaRecorderRef.current.stop();
    }
    
    // Clear timer
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
    
    // Release microphone
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    
    // Reset state
    setState(RecordingState.IDLE);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setRecordingDuration(0);
    audioChunks.current = [];
    
    if (audioURL) {
      URL.revokeObjectURL(audioURL);
      setAudioURL(null);
    }
  };

  const acceptRecording = async () => {
    if (!audioURL) return;

    setState(RecordingState.PROCESSING);
    setProcessingProgress(0);

    try {
      // Simulate processing with progress updates
      const progressInterval = setInterval(() => {
        setProcessingProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 10;
        });
      }, 100);      // Convert blob URL to actual file
      const response = await fetch(audioURL);
      const audioBlob = await response.blob();
      const randomName = `recording-${getRandomString(8)}.wav`;
      const file = new File([audioBlob], randomName, { type: "audio/wav" });

      // Complete processing
      setTimeout(() => {
        setProcessingProgress(100);
        setTimeout(() => {
          onRecordingComplete(file);
          onClose();
          resetRecording();
          toast.success("Recording saved successfully");
        }, 500);
      }, 1000);

    } catch (error) {
      setState(RecordingState.RECORDED);
      setProcessingProgress(0);
      toast.error("Failed to process recording");
      console.error("Error processing recording:", error);
    }
  };
  const handleClose = () => {
    if (state === RecordingState.RECORDING || state === RecordingState.PAUSED) {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
      }
    }
    resetRecording();
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Audio Recording</DialogTitle>          <DialogDescription>
            {state === RecordingState.IDLE && "Click the microphone to start recording"}
            {state === RecordingState.RECORDING && "Recording in progress..."}
            {state === RecordingState.PAUSED && "Recording paused - click resume to continue"}
            {state === RecordingState.RECORDED && "Review your recording"}
            {state === RecordingState.PROCESSING && "Processing recording..."}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">          {/* Recording Controls */}
          <div className="flex flex-col items-center space-y-4">
            {/* Main Record Button */}
            <div className="relative">
              <button
                onClick={state === RecordingState.IDLE ? startRecording : stopRecording}
                disabled={state === RecordingState.PROCESSING}
                className={cn(
                  "w-20 h-20 flex items-center justify-center rounded-full text-white shadow-lg transition-all duration-200 focus:outline-none focus:ring-2",
                  state === RecordingState.RECORDING || state === RecordingState.PAUSED
                    ? "bg-red-500 hover:bg-red-600 focus:ring-red-400"
                    : "bg-green-500 hover:bg-green-600 focus:ring-green-400",
                  state === RecordingState.PROCESSING && "opacity-50 cursor-not-allowed"
                )}
                aria-label={state === RecordingState.RECORDING || state === RecordingState.PAUSED ? "Stop Recording" : "Start Recording"}
              >
                {state === RecordingState.RECORDING || state === RecordingState.PAUSED ? (
                  <Square className="w-10 h-10" />
                ) : (
                  <Mic className="w-10 h-10" />
                )}
              </button>
              
              {/* Recording indicator */}
              {state === RecordingState.RECORDING && (
                <div className="absolute -top-2 -right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center">
                  <div className="w-2 h-2 bg-white rounded-full" />
                </div>
              )}
              
              {/* Paused indicator */}
              {state === RecordingState.PAUSED && (
                <div className="absolute -top-2 -right-2 w-6 h-6 bg-yellow-500 rounded-full flex items-center justify-center">
                  <Pause className="w-3 h-3 text-white" />
                </div>
              )}
            </div>

            {/* Pause/Resume Button */}
            {(state === RecordingState.RECORDING || state === RecordingState.PAUSED) && (
              <Button
                onClick={state === RecordingState.RECORDING ? pauseRecording : resumeRecording}
                variant="outline"
                className="flex items-center gap-2"
              >
                {state === RecordingState.RECORDING ? (
                  <>
                    <Pause className="w-4 h-4" />
                    Pause
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Resume
                  </>
                )}
              </Button>
            )}

            {/* Recording Duration */}
            {(state === RecordingState.RECORDING || state === RecordingState.PAUSED) && (
              <div className={cn(
                "text-lg font-mono",
                state === RecordingState.RECORDING ? "text-red-600" : "text-yellow-600"
              )}>
                {formatTime(recordingDuration)}
                {state === RecordingState.PAUSED && " (Paused)"}
              </div>
            )}
          </div>

          {/* Playback Controls */}
          {audioURL && state !== RecordingState.PROCESSING && (
            <div className="space-y-4">
              <audio ref={audioRef} src={audioURL} preload="metadata" />
              
              {/* Playback Button and Time */}
              <div className="flex items-center space-x-4">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={playPause}
                  className="w-12 h-12 rounded-full p-0"
                >
                  {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </Button>
                
                <div className="flex-1 space-y-2">
                  {/* Progress Bar */}
                  <Slider
                    value={[currentTime]}
                    max={duration}
                    step={0.1}
                    onValueChange={([value]) => seek(value)}
                    className="w-full"
                  />
                  
                  {/* Time Display */}
                  <div className="flex justify-between text-sm text-muted-foreground">
                    <span>{formatTime(currentTime)}</span>
                    <span>{formatTime(duration)}</span>
                  </div>
                </div>
              </div>

              {/* Volume Control */}
              <div className="flex items-center space-x-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={toggleMute}
                  className="p-2"
                >
                  {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </Button>
                
                <Slider
                  value={[isMuted ? 0 : volume]}
                  max={100}
                  step={1}
                  onValueChange={handleVolumeChange}
                  className="flex-1"
                />
                
                <span className="text-sm text-muted-foreground w-8">
                  {isMuted ? 0 : volume}
                </span>
              </div>
            </div>
          )}

          {/* Processing Progress */}
          {state === RecordingState.PROCESSING && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Processing recording...</span>
                <span>{processingProgress}%</span>
              </div>
              <Progress value={processingProgress} className="w-full" />
            </div>
          )}          {/* Action Buttons */}
          <div className="flex space-x-2">
            {state === RecordingState.RECORDED && (
              <>
                <Button
                  variant="outline"
                  onClick={resetRecording}
                  className="flex-1"
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Re-record
                </Button>
                <Button
                  onClick={acceptRecording}
                  className="flex-1"
                >
                  <Check className="w-4 h-4 mr-2" />
                  Accept
                </Button>
              </>
            )}
            
            {(state === RecordingState.IDLE || state === RecordingState.RECORDED) && (
              <Button
                variant="outline"
                onClick={handleClose}
                className={state === RecordingState.IDLE ? "w-full" : ""}
              >
                Cancel
              </Button>
            )}
            
            {(state === RecordingState.RECORDING || state === RecordingState.PAUSED) && (
              <Button
                variant="outline"
                onClick={resetRecording}
                className="w-full"
              >
                Cancel Recording
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
