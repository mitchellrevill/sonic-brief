import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface RecordingCardSkeletonProps {
  className?: string;
}

/**
 * Skeleton loader for AudioRecordingCard component
 * Matches the layout of the actual recording card for consistent loading experience
 */
export function RecordingCardSkeleton({ className }: RecordingCardSkeletonProps) {
  return (
    <Card className={cn("p-4", className)}>
      <div className="space-y-3">
        {/* Header: Title and Status Badge */}
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-2 flex-1 min-w-0">
            {/* Title */}
            <Skeleton className="h-5 w-3/4" />
            {/* Subtitle/Date */}
            <Skeleton className="h-3 w-1/2" />
          </div>
          {/* Status Badge */}
          <Skeleton className="h-6 w-20 rounded-md flex-shrink-0" />
        </div>

        {/* Metadata section */}
        <div className="space-y-2 pt-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-3 w-3 rounded-full" />
            <Skeleton className="h-3 w-24" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-3 w-3 rounded-full" />
            <Skeleton className="h-3 w-32" />
          </div>
        </div>

        {/* Actions Footer */}
        <div className="flex items-center justify-between pt-3 border-t">
          <div className="flex gap-2">
            <Skeleton className="h-9 w-20" />
            <Skeleton className="h-9 w-16" />
          </div>
          <Skeleton className="h-9 w-9 rounded" />
        </div>
      </div>
    </Card>
  );
}

/**
 * Grid of recording card skeletons
 */
export function RecordingCardSkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, index) => (
        <RecordingCardSkeleton key={`skeleton-${index}`} />
      ))}
    </div>
  );
}
