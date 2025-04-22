import { useCallback, useEffect, useRef, useState } from "react";
import { formatTime } from "@/lib/date";

export function useAudioPlayer(src: string | undefined) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [displayVolume, setDisplayVolume] = useState(75);

  // Effect for setting up audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleLoadedMetadata = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);
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

    audio.addEventListener("timeupdate", handleTimeUpdate);
    audio.addEventListener("loadedmetadata", handleLoadedMetadata);
    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("volumechange", handleVolumeChange);

    // Set initial duration if metadata already loaded
    if (audio.readyState >= 1) {
      handleLoadedMetadata();
    }

    return () => {
      audio.removeEventListener("timeupdate", handleTimeUpdate);
      audio.removeEventListener("loadedmetadata", handleLoadedMetadata);
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("volumechange", handleVolumeChange);
    };
    // Rerun effect only if the audio source changes
  }, [src, displayVolume, isMuted]); // Added displayVolume and isMuted dependencies

  // Effect for handling play/pause state changes
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.play().catch((error) => {
        console.error("Error playing audio:", error);
        setIsPlaying(false); // Reset state on error
      });
    } else {
      audio.pause();
    }
  }, [isPlaying]);

  // --- Control Functions ---

  const togglePlayPause = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const toggleMute = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const newMuted = !isMuted;
    audio.muted = newMuted; // Directly update the audio element
    setIsMuted(newMuted); // Update state
  }, [isMuted]);

  const handleTimeSliderChange = useCallback((value: Array<number>) => {
    const newTime = value[0];
    setCurrentTime(newTime);
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  }, []);

  const handleVolumeSliderChange = useCallback((value: Array<number>) => {
    const newVolumePercent = value[0];
    setDisplayVolume(newVolumePercent); // Update state
    if (audioRef.current) {
      audioRef.current.volume = newVolumePercent / 100; // Update audio element volume
      // If adjusting volume while muted, unmute
      if (newVolumePercent > 0 && audioRef.current.muted) {
        audioRef.current.muted = false;
        setIsMuted(false);
      }
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
    togglePlayPause,
    toggleMute,
    handleTimeSliderChange,
    handleVolumeSliderChange,
    formattedCurrentTime,
    formattedDuration,
  };
}
