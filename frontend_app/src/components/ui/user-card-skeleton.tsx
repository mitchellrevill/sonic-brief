import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";

interface UserCardSkeletonProps {
  className?: string;
}

/**
 * Skeleton loader for user management cards
 */
export function UserCardSkeleton({ className }: UserCardSkeletonProps) {
  return (
    <Card className={cn("", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="space-y-2 flex-1">
            {/* User name */}
            <Skeleton className="h-5 w-48" />
            {/* Email */}
            <Skeleton className="h-4 w-56" />
          </div>
          {/* Permission badge */}
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Metadata */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Skeleton className="h-3 w-3 rounded-full" />
            <Skeleton className="h-3 w-32" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-3 w-3 rounded-full" />
            <Skeleton className="h-3 w-40" />
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Skeleton className="h-9 w-24" />
          <Skeleton className="h-9 w-24" />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Grid of user card skeletons
 */
export function UserCardSkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, index) => (
        <UserCardSkeleton key={`user-skeleton-${index}`} />
      ))}
    </div>
  );
}
