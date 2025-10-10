import { cn } from '@/lib/utils';
import type { AudioMetrics } from '@/hooks/useAudioAnalyzer';

interface AudioLevelMeterProps {
  metrics: AudioMetrics;
  className?: string;
  showMaxIndicator?: boolean;
  showQualityText?: boolean;
  showNumericLevel?: boolean;
  vertical?: boolean;
  height?: number;
}

/**
 * Comprehensive audio level meter with quality indicators
 * Shows current level, peak level with decay, max level marker, and quality assessment
 */
export function AudioLevelMeter({
  metrics,
  className,
  showMaxIndicator = true,
  showQualityText = true,
  showNumericLevel = true,
  vertical = false,
  height = 120,
}: AudioLevelMeterProps) {
  const { currentLevel, peakLevel, maxLevel, quality, clipCount, silenceDetected } = metrics;

  // Color scheme based on level
  const getLevelColor = (level: number): string => {
    if (level < 15) return 'bg-gray-400'; // Too quiet
    if (level < 25) return 'bg-yellow-400'; // Fair
    if (level < 50) return 'bg-green-500'; // Good
    if (level < 75) return 'bg-green-400'; // Excellent
    return 'bg-red-500'; // Too loud / clipping
  };

  const getQualityConfig = (q: AudioMetrics['quality']) => {
    switch (q) {
      case 'excellent':
        return {
          text: 'Excellent',
          color: 'text-green-600',
          bgColor: 'bg-green-100',
          icon: '✓',
        };
      case 'good':
        return {
          text: 'Good',
          color: 'text-green-600',
          bgColor: 'bg-green-50',
          icon: '✓',
        };
      case 'fair':
        return {
          text: 'Fair',
          color: 'text-yellow-600',
          bgColor: 'bg-yellow-50',
          icon: '⚠',
        };
      case 'poor':
        return {
          text: 'Poor',
          color: 'text-red-600',
          bgColor: 'bg-red-50',
          icon: '✕',
        };
      case 'silent':
        return {
          text: 'Silent',
          color: 'text-gray-600',
          bgColor: 'bg-gray-50',
          icon: '○',
        };
    }
  };

  const qualityConfig = getQualityConfig(quality);
  const levelColor = getLevelColor(currentLevel);

  if (vertical) {
    return (
      <div className={cn('flex flex-col items-center gap-2', className)}>
        {/* Quality indicator */}
        {showQualityText && (
          <div
            className={cn(
              'px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5',
              qualityConfig.bgColor,
              qualityConfig.color
            )}
          >
            <span>{qualityConfig.icon}</span>
            <span>{qualityConfig.text}</span>
          </div>
        )}

        {/* Vertical meter */}
        <div className="relative w-12 rounded-lg bg-gray-200 dark:bg-gray-800 overflow-hidden shadow-inner"
          style={{ height: `${height}px` }}
        >
          {/* Current level bar */}
          <div
            className={cn(
              'absolute bottom-0 left-0 right-0 transition-all duration-75 ease-out',
              levelColor
            )}
            style={{
              height: `${currentLevel}%`,
            }}
          />

          {/* Peak level indicator (thin line) */}
          <div
            className="absolute left-0 right-0 h-0.5 bg-white shadow-md transition-all duration-100"
            style={{
              bottom: `${peakLevel}%`,
              opacity: peakLevel > 5 ? 1 : 0,
            }}
          />

          {/* Max level marker */}
          {showMaxIndicator && maxLevel > 10 && (
            <div
              className="absolute left-0 right-0 h-1 bg-blue-500 shadow-lg"
              style={{
                bottom: `${maxLevel}%`,
              }}
            >
              <div className="absolute -right-1 top-1/2 -translate-y-1/2 w-2 h-2 bg-blue-500 rounded-full" />
            </div>
          )}

          {/* Level markers */}
          <div className="absolute inset-0 pointer-events-none">
            {[25, 50, 75].map((mark) => (
              <div
                key={mark}
                className="absolute left-0 right-0 h-px bg-gray-400/30"
                style={{ bottom: `${mark}%` }}
              />
            ))}
          </div>
        </div>

        {/* Numeric level */}
        {showNumericLevel && (
          <div className="text-sm font-mono text-gray-700 dark:text-gray-300">
            {Math.round(currentLevel)}%
          </div>
        )}

        {/* Warnings */}
        {clipCount > 0 && (
          <div className="text-xs text-red-600 font-medium">
            Clipping detected
          </div>
        )}
        {silenceDetected && (
          <div className="text-xs text-gray-600 font-medium">
            No audio detected
          </div>
        )}
      </div>
    );
  }

  // Horizontal meter
  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Header with quality and level */}
      <div className="flex items-center justify-between">
        {showQualityText && (
          <div
            className={cn(
              'px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1.5',
              qualityConfig.bgColor,
              qualityConfig.color
            )}
          >
            <span>{qualityConfig.icon}</span>
            <span>{qualityConfig.text}</span>
          </div>
        )}

        {showNumericLevel && (
          <div className="text-sm font-mono text-gray-700 dark:text-gray-300">
            {Math.round(currentLevel)}%
          </div>
        )}
      </div>

      {/* Horizontal meter */}
      <div className="relative w-full h-8 rounded-lg bg-gray-200 dark:bg-gray-800 overflow-hidden shadow-inner">
        {/* Current level bar */}
        <div
          className={cn(
            'absolute left-0 top-0 bottom-0 transition-all duration-75 ease-out',
            levelColor
          )}
          style={{
            width: `${currentLevel}%`,
          }}
        />

        {/* Peak level indicator (thin line) */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-white shadow-md transition-all duration-100"
          style={{
            left: `${peakLevel}%`,
            opacity: peakLevel > 5 ? 1 : 0,
          }}
        />

        {/* Max level marker */}
        {showMaxIndicator && maxLevel > 10 && (
          <div
            className="absolute top-0 bottom-0 w-1 bg-blue-500 shadow-lg"
            style={{
              left: `${maxLevel}%`,
            }}
          >
            <div className="absolute left-1/2 -translate-x-1/2 -top-1 w-2 h-2 bg-blue-500 rounded-full" />
          </div>
        )}

        {/* Level markers */}
        <div className="absolute inset-0 pointer-events-none">
          {[25, 50, 75].map((mark) => (
            <div
              key={mark}
              className="absolute top-0 bottom-0 w-px bg-gray-400/30"
              style={{ left: `${mark}%` }}
            />
          ))}
        </div>

        {/* Percentage labels */}
        <div className="absolute inset-0 flex items-center justify-between px-2 text-xs text-gray-500 pointer-events-none">
          <span>0</span>
          <span>50</span>
          <span>100</span>
        </div>
      </div>

      {/* Warnings */}
      <div className="flex items-center gap-3 text-xs">
        {clipCount > 0 && (
          <div className="text-red-600 font-medium flex items-center gap-1">
            <span>⚠</span>
            <span>Clipping detected ({clipCount})</span>
          </div>
        )}
        {silenceDetected && (
          <div className="text-gray-600 font-medium flex items-center gap-1">
            <span>○</span>
            <span>No audio detected</span>
          </div>
        )}
        {showMaxIndicator && maxLevel > 10 && (
          <div className="text-blue-600 font-medium flex items-center gap-1">
            <span>▸</span>
            <span>Max: {Math.round(maxLevel)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}
