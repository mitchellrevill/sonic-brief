import { useCallback, useEffect, useRef, useState } from "react";
import { formatTime } from "@/lib/date";

export function useAudioPlayer(src: string | undefined) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [displayVolume, setDisplayVolume] = useState(75);
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Reset state when source changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setHasError(false);
    setIsLoading(!!src);
  }, [src]);

  // Effect for setting up audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !src) return;

    const handleLoadStart = () => {
      setIsLoading(true);
      setHasError(false);
    };

    const handleLoadedMetadata = () => {
      setIsLoading(false);
      if (audio.duration && isFinite(audio.duration)) {
        setDuration(audio.duration);
      } else {
        // Fallback: try to get duration after a short delay
        setTimeout(() => {
          if (audio.duration && isFinite(audio.duration)) {
            setDuration(audio.duration);
          }
        }, 100);
      }
    };

    const handleLoadedData = () => {
      setIsLoading(false);
      // Double-check duration after data is loaded
      if (audio.duration && isFinite(audio.duration)) {
        setDuration(audio.duration);
      }
    };

    const handleCanPlay = () => {
      setIsLoading(false);
      // Final attempt to get duration
      if (audio.duration && isFinite(audio.duration)) {
        setDuration(audio.duration);
      }
    };

    const handleTimeUpdate = () => {
      if (audio.currentTime !== undefined && isFinite(audio.currentTime)) {
        setCurrentTime(audio.currentTime);
      }
      
      // Sometimes duration becomes available during playback
      if (audio.duration && isFinite(audio.duration) && duration === 0) {
        setDuration(audio.duration);
      }
    };

    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };

    const handleError = (e: Event) => {
      console.error('Audio error:', e);
      setIsLoading(false);
      setHasError(true);
      setIsPlaying(false);
    };

    const handleDurationChange = () => {
      if (audio.duration && isFinite(audio.duration)) {
        setDuration(audio.duration);
      }
    };

    const handleVolumeChange = () => {
      // Sync state if volume changed externally (less common, but good practice)
      // Avoid feedback loop by checking if it's significantly different
      const currentVolumePercent = Math.round(audio.volume * 100);
      if (Math.abs(currentVolumePercent - displayVolume) > 1) {
        setDisplayVolume(currentVolumePercent);
      }
      setIsMuted(audio.muted); // Also sync muted state
    };

    // Set initial volume and muted state from default state
    audio.volume = displayVolume / 100;
    audio.muted = isMuted;

    // Add all event listeners
    audio.addEventListener('loadstart', handleLoadStart);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('loadeddata', handleLoadedData);
    audio.addEventListener('canplay', handleCanPlay);
    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener('error', handleError);
    audio.addEventListener('durationchange', handleDurationChange);
    audio.addEventListener("volumechange", handleVolumeChange);

    // Force load metadata
    audio.load();

    // Set initial duration if metadata already loaded
    if (audio.readyState >= 1) {
      handleLoadedMetadata();
    }

    return () => {
      audio.removeEventListener('loadstart', handleLoadStart);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('loadeddata', handleLoadedData);
      audio.removeEventListener('canplay', handleCanPlay);
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener('error', handleError);
      audio.removeEventListener('durationchange', handleDurationChange);
      audio.removeEventListener("volumechange", handleVolumeChange);
    };
    // Rerun effect only if the audio source changes
  }, [src, displayVolume, isMuted, duration]); // Added duration dependency

  // Effect for handling play/pause state changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || hasError) return;

    if (isPlaying) {
      audio.play().catch((error) => {
        console.error("Error playing audio:", error);
        setIsPlaying(false); // Reset state on error
        setHasError(true);
      });
    } else {
      audio.pause();
    }
  }, [isPlaying, hasError]);

  // --- Control Functions ---

  const togglePlayPause = useCallback(async () => {
    const audio = audioRef.current;
    if (!audio || hasError) return;

    try {
      if (isPlaying) {
        audio.pause();
        setIsPlaying(false);
      } else {
        // Ensure audio is loaded before playing
        if (audio.readyState < 2) {
          setIsLoading(true);
          await new Promise((resolve, reject) => {
            const handleCanPlay = () => {
              audio.removeEventListener('canplay', handleCanPlay);
              audio.removeEventListener('error', handleErrorEvent);
              setIsLoading(false);
              resolve(undefined);
            };
            const handleErrorEvent = () => {
              audio.removeEventListener('canplay', handleCanPlay);
              audio.removeEventListener('error', handleErrorEvent);
              setIsLoading(false);
              setHasError(true);
              reject(new Error('Failed to load audio'));
            };
            audio.addEventListener('canplay', handleCanPlay);
            audio.addEventListener('error', handleErrorEvent);
          });
        }
        
        await audio.play();
        setIsPlaying(true);
      }
    } catch (error) {
      console.error('Play/pause error:', error);
      setHasError(true);
      setIsPlaying(false);
    }
  }, [isPlaying, hasError]);

  const toggleMute = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const newMuted = !isMuted;
    audio.muted = newMuted; // Directly update the audio element
    setIsMuted(newMuted); // Update state
  }, [isMuted]);

  const handleTimeSliderChange = useCallback((value: Array<number>) => {
    const audio = audioRef.current;
    if (!audio || !duration) return;

    const newTime = value[0];
    audio.currentTime = newTime;
    setCurrentTime(newTime);
  }, [duration]);

  const handleVolumeSliderChange = useCallback((value: Array<number>) => {
    const audio = audioRef.current;
    if (!audio) return;

    const newVolumePercent = value[0];
    setDisplayVolume(newVolumePercent); // Update state
    audio.volume = newVolumePercent / 100; // Update audio element volume
    
    // If adjusting volume while muted, unmute
    if (newVolumePercent > 0 && audio.muted) {
      audio.muted = false;
      setIsMuted(false);
    }
  }, []);

  // --- Derived Values ---
  const formattedCurrentTime = formatTime(currentTime);
  const formattedDuration = formatTime(duration || 0);

  return {
    audioRef,
    isPlaying,
    isMuted,
    currentTime,
    duration,
    displayVolume,
    isLoading,
    hasError,
    togglePlayPause,
    toggleMute,
    handleTimeSliderChange,
    handleVolumeSliderChange,
    formattedCurrentTime,
    formattedDuration,
  };
}
