import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { Play, Pause, X, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatTime } from "@/lib/date";
import { getFileNameFromPath } from "@/lib/file-utils";

interface MiniAudioPlayerProps {
  src: string;
  onClose: () => void;
  className?: string;
}

export function MiniAudioPlayer({ src, onClose, className }: MiniAudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMuted, setIsMuted] = useState(false);
  const [volume, setVolume] = useState(75);  
  // Get file name for display
  const fileName = getFileNameFromPath(src);  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
      setIsLoading(false);
    };
    const handleEnded = () => setIsPlaying(false);
    const handleError = () => {
      setError("Failed to load audio");
      setIsLoading(false);
    };
    const handleVolumeChange = () => {
      setIsMuted(audio.muted);
      setVolume(Math.round(audio.volume * 100));
    };
    
    // Set initial volume
    audio.volume = volume / 100;
    audio.muted = isMuted;
    
    // Add event listeners
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("error", handleError);
    audio.addEventListener("volumechange", handleVolumeChange);
    
    // Auto-play when component mounts
    audio.load();
    audio.play().catch(err => {
      console.error("Auto-play prevented:", err);
      setIsPlaying(false);
    });
    setIsPlaying(true);
    
    return () => {
      audio.pause();
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("error", handleError);
      audio.removeEventListener("volumechange", handleVolumeChange);
    };  }, [src, volume, isMuted]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.play().catch((error) => {
        console.error("Error playing audio:", error);
        setIsPlaying(false);
      });
    } else {
      audio.pause();
    }
  }, [isPlaying]);
  
  const togglePlayPause = () => {
    setIsPlaying((prev) => !prev);
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;
    const newMuted = !isMuted;
    audio.muted = newMuted;
    setIsMuted(newMuted);
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Only handle if no input is focused
      const activeElement = document.activeElement;
      if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
        return;
      }

      switch (e.code) {
        case 'Space':
          e.preventDefault();
          togglePlayPause();
          break;
        case 'KeyM':
          e.preventDefault();
          toggleMute();
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          if (audioRef.current) {
            audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
          }
          break;
        case 'ArrowRight':
          e.preventDefault();
          if (audioRef.current) {
            audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
          }
          break;
      }
    };

    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, [togglePlayPause, toggleMute, onClose, duration]);

  const handleTimeSliderChange = (value: number[]) => {
    const newTime = value[0];
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };
  
  const handleVolumeChange = (value: number[]) => {
    const newVolume = value[0];
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume / 100;
      if (newVolume > 0 && audioRef.current.muted) {
        audioRef.current.muted = false;
        setIsMuted(false);
      }
    }
  };
  
  return (
    <div className={cn(
      "fixed bottom-0 left-0 right-0 bg-background border-t border-border z-50 p-3 shadow-lg",
      className
    )}>
      <audio 
        ref={audioRef}
        src={src}
        preload="metadata"
        className="hidden"
      />
      
      <div className="container mx-auto max-w-3xl">
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            className="bg-primary text-primary-foreground h-8 w-8 rounded-full p-0 hover:bg-primary/90"
            onClick={togglePlayPause}
            disabled={isLoading || !!error}
          >
            {isPlaying ? (
              <Pause className="h-4 w-4" />
            ) : (
              <Play className="h-4 w-4 ml-0.5" />
            )}
          </Button>
          
          <div className="hidden sm:block text-sm max-w-[180px] truncate text-muted-foreground">
            {fileName}
          </div>
          
          <div className="flex-1 space-y-1.5">
            <Slider
              value={[currentTime]}
              max={duration || 100}
              step={1}
              className="cursor-pointer"
              onValueChange={handleTimeSliderChange}
              disabled={isLoading || !!error}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span className="font-mono">
                {formatTime(currentTime)}
              </span>
              <span className="font-mono">
                {formatTime(duration)}
              </span>
            </div>
          </div>
          
          {/* Volume control */}
          <div className="hidden sm:flex items-center gap-2">
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={toggleMute}
              className="h-8 w-8 flex-shrink-0"
            >
              {isMuted ? (
                <VolumeX className="h-4 w-4" />
              ) : (
                <Volume2 className="h-4 w-4" />
              )}
            </Button>
            <Slider
              value={[volume]}
              max={100}
              step={1}
              className="w-20 cursor-pointer"
              onValueChange={handleVolumeChange}
              disabled={isLoading || !!error}
            />
          </div>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={onClose}
            className="h-8 w-8 p-0 flex-shrink-0"
          >
            <X className="h-4 w-4" />
            <span className="sr-only">Close</span>
          </Button>
        </div>
          {error && (
          <div className="mt-1 text-sm text-destructive">
            {error}. <a href={src} target="_blank" rel="noopener noreferrer" className="underline">Open in new tab</a>.
          </div>
        )}
        
        {isLoading && (
          <div className="mt-1 text-sm text-muted-foreground">
            Loading audio...
          </div>
        )}
        
        {!error && !isLoading && (
          <div className="mt-1 text-xs text-muted-foreground hidden sm:block">
            Keyboard shortcuts: Space (play/pause), M (mute), ← → (skip 10s), Esc (close)
          </div>
        )}
      </div>
    </div>
  );
}
