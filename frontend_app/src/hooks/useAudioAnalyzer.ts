import { useEffect, useRef, useState } from 'react';

export interface AudioMetrics {
  currentLevel: number;      // Current instantaneous level (0-100)
  maxLevel: number;          // Maximum level reached (0-100)
  peakLevel: number;         // Peak with slow decay for visual reference
  averageLevel: number;      // Running average for smoothing
  clipCount: number;         // Number of times signal clipped
  silenceDetected: boolean;  // True if below threshold for extended period
  quality: 'excellent' | 'good' | 'fair' | 'poor' | 'silent'; // Overall quality assessment
}

interface UseAudioAnalyzerOptions {
  fftSize?: number;          // FFT size for frequency analysis (default: 2048)
  smoothingTimeConstant?: number; // 0-1, higher = smoother (default: 0.8)
  minDecibels?: number;      // Minimum power value (default: -90)
  maxDecibels?: number;      // Maximum power value (default: -10)
  updateInterval?: number;   // MS between updates (default: 50ms = 20fps)
  peakDecayRate?: number;    // How fast peak indicator decays (default: 0.98)
  silenceThreshold?: number; // Level below which is considered silence (default: 5)
  silenceDuration?: number;  // MS of silence before flagging (default: 2000)
}

const DEFAULT_OPTIONS: Required<UseAudioAnalyzerOptions> = {
  fftSize: 2048,
  smoothingTimeConstant: 0.8,
  minDecibels: -90,
  maxDecibels: -10,
  updateInterval: 50,
  peakDecayRate: 0.98,
  silenceThreshold: 5,
  silenceDuration: 2000,
};

/**
 * Hook for real-time audio analysis during recording
 * Provides comprehensive audio metrics including levels, peaks, and quality assessment
 */
export function useAudioAnalyzer(
  stream: MediaStream | null,
  options: UseAudioAnalyzerOptions = {}
) {
  const [metrics, setMetrics] = useState<AudioMetrics>({
    currentLevel: 0,
    maxLevel: 0,
    peakLevel: 0,
    averageLevel: 0,
    clipCount: 0,
    silenceDetected: false,
    quality: 'silent',
  });

  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const dataArrayRef = useRef<Uint8Array | null>(null);
  const metricsRef = useRef<AudioMetrics>(metrics);
  const lastUpdateRef = useRef<number>(0);
  const silenceStartRef = useRef<number | null>(null);
  const levelHistoryRef = useRef<number[]>([]);

  // Merge options with defaults
  const opts = { ...DEFAULT_OPTIONS, ...options };

  useEffect(() => {
    if (!stream) {
      // Cleanup when stream is removed
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      analyserRef.current = null;
      audioContextRef.current = null;
      dataArrayRef.current = null;
      
      // Reset metrics
      setMetrics({
        currentLevel: 0,
        maxLevel: 0,
        peakLevel: 0,
        averageLevel: 0,
        clipCount: 0,
        silenceDetected: false,
        quality: 'silent',
      });
      
      return;
    }

    // Create audio context and analyser
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);

    // Configure analyser
    analyser.fftSize = opts.fftSize;
    analyser.smoothingTimeConstant = opts.smoothingTimeConstant;
    analyser.minDecibels = opts.minDecibels;
    analyser.maxDecibels = opts.maxDecibels;

    // Connect nodes
    source.connect(analyser);

    // Create data array for time domain data
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    // Store refs
    analyserRef.current = analyser;
    audioContextRef.current = audioContext;
    dataArrayRef.current = dataArray;

    // Analysis loop
    const analyze = () => {
      const now = Date.now();
      
      // Throttle updates based on updateInterval
      if (now - lastUpdateRef.current < opts.updateInterval) {
        animationFrameRef.current = requestAnimationFrame(analyze);
        return;
      }
      lastUpdateRef.current = now;

      if (!analyserRef.current || !dataArrayRef.current) {
        return;
      }

      // Get time domain data (waveform)
      // Use 'any' cast to avoid TypeScript's ArrayBuffer vs SharedArrayBuffer generic mismatch
      analyserRef.current.getByteTimeDomainData(dataArrayRef.current as any);

      // Calculate RMS (root mean square) level
      let sum = 0;
      let max = 0;
      let clipping = false;

      for (let i = 0; i < dataArrayRef.current.length; i++) {
        // Convert from 0-255 to -1 to 1
        const normalized = (dataArrayRef.current[i] - 128) / 128;
        const absolute = Math.abs(normalized);
        
        sum += absolute * absolute;
        max = Math.max(max, absolute);

        // Detect clipping (values at extremes)
        if (dataArrayRef.current[i] <= 1 || dataArrayRef.current[i] >= 254) {
          clipping = true;
        }
      }

      // Calculate RMS and convert to percentage (no aggressive scaling)
      const rms = Math.sqrt(sum / dataArrayRef.current.length);
      const currentLevel = Math.min(100, rms * 200); // Gentle scaling for normal speech
      const instantMax = Math.min(100, max * 150); // Peak level

      // Update metrics
      const newMetrics = { ...metricsRef.current };

      // Current level (instantaneous)
      newMetrics.currentLevel = currentLevel;

      // Update max level (never decreases)
      newMetrics.maxLevel = Math.max(newMetrics.maxLevel, instantMax);

      // Update peak level (slow decay)
      if (instantMax > newMetrics.peakLevel) {
        newMetrics.peakLevel = instantMax;
      } else {
        newMetrics.peakLevel *= opts.peakDecayRate;
      }

      // Update level history for averaging (keep last 20 samples)
      levelHistoryRef.current.push(currentLevel);
      if (levelHistoryRef.current.length > 20) {
        levelHistoryRef.current.shift();
      }

      // Calculate running average
      const sum_avg = levelHistoryRef.current.reduce((a, b) => a + b, 0);
      newMetrics.averageLevel = sum_avg / levelHistoryRef.current.length;

      // Track clipping
      if (clipping) {
        newMetrics.clipCount++;
      }

      // Silence detection
      if (currentLevel < opts.silenceThreshold) {
        if (silenceStartRef.current === null) {
          silenceStartRef.current = now;
        } else if (now - silenceStartRef.current > opts.silenceDuration) {
          newMetrics.silenceDetected = true;
        }
      } else {
        silenceStartRef.current = null;
        newMetrics.silenceDetected = false;
      }

      // Quality assessment
      if (newMetrics.silenceDetected || newMetrics.averageLevel < 5) {
        newMetrics.quality = 'silent';
      } else if (newMetrics.clipCount > 10 || newMetrics.averageLevel > 80) {
        newMetrics.quality = 'poor'; // Too loud, likely clipping
      } else if (newMetrics.averageLevel < 15) {
        newMetrics.quality = 'poor'; // Too quiet
      } else if (newMetrics.averageLevel < 25) {
        newMetrics.quality = 'fair';
      } else if (newMetrics.averageLevel < 50) {
        newMetrics.quality = 'good';
      } else {
        newMetrics.quality = 'excellent';
      }

      // Update state
      metricsRef.current = newMetrics;
      setMetrics(newMetrics);

      animationFrameRef.current = requestAnimationFrame(analyze);
    };

    // Start analysis
    animationFrameRef.current = requestAnimationFrame(analyze);

    // Cleanup
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, opts.fftSize, opts.smoothingTimeConstant, opts.minDecibels, opts.maxDecibels, opts.updateInterval, opts.peakDecayRate, opts.silenceThreshold, opts.silenceDuration]);

  return metrics;
}
