import { cn } from '@/lib/utils';
import type { AudioMetrics } from '@/hooks/useAudioAnalyzer';

interface MinimalAudioIndicatorProps {
  metrics: AudioMetrics;
  className?: string;
}

/**
 * Minimal audio level indicator - single green bar that lights up when speaking
 * Subtly shows the user their voice is being picked up without overwhelming the UI
 */
export function MinimalAudioIndicator({
  metrics,
  className,
}: MinimalAudioIndicatorProps) {
  const { currentLevel, maxLevel } = metrics;

  // Determine if actively speaking (above threshold)
  const isSpeaking = currentLevel > 5;
  
  // Calculate opacity based on current level (0.2 to 1.0)
  const opacity = isSpeaking 
    ? Math.max(0.2, Math.min(1.0, currentLevel / 60)) 
    : 0.1;

  // Calculate width based on current level (10% to 100%)
  const width = Math.max(10, Math.min(100, currentLevel));

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Main level bar */}
      <div className="relative flex-1 h-1.5 rounded-full bg-gray-200 dark:bg-gray-800 overflow-hidden">
        {/* Active speaking indicator */}
        <div
          className={cn(
            'absolute left-0 top-0 bottom-0 rounded-full transition-all duration-100 ease-out',
            isSpeaking 
              ? 'bg-green-500' 
              : 'bg-gray-400'
          )}
          style={{
            width: `${width}%`,
            opacity: opacity,
          }}
        />

        {/* Max level marker (subtle dot) */}
        {maxLevel > 10 && (
          <div
            className="absolute top-1/2 -translate-y-1/2 w-1 h-1 bg-green-600 rounded-full transition-all duration-300"
            style={{
              left: `${maxLevel}%`,
              opacity: 0.6,
            }}
          />
        )}
      </div>

      {/* Simple speaking indicator dot */}
      <div
        className={cn(
          'w-2 h-2 rounded-full transition-all duration-200',
          isSpeaking 
            ? 'bg-green-500 shadow-sm shadow-green-500/50' 
            : 'bg-gray-300'
        )}
        style={{
          opacity: isSpeaking ? opacity : 0.3,
        }}
      />
    </div>
  );
}
