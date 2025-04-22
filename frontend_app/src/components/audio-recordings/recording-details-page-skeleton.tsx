import { Skeleton } from "@/components/ui/skeleton";

export function RecordingDetailsSkeleton() {
  return (
    <div className="relative container mx-auto px-4 py-6">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Skeleton className="h-9 w-9" />
          <div>
            <Skeleton className="h-9 w-48" />
            <Skeleton className="mt-1 h-4 w-32" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="space-y-6 lg:col-span-3">
          <div className="bg-card rounded-lg border p-6">
            <div className="pb-3">
              <Skeleton className="h-8 w-32" />
            </div>

            {/* Audio player skeleton */}
            <div className="bg-secondary/30 mb-4 rounded-lg p-4">
              <div className="mb-3 flex items-center gap-4">
                <Skeleton className="h-10 w-10 rounded-full" />
                <div className="flex flex-1 items-center gap-3">
                  <Skeleton className="h-4 w-12" />
                  <Skeleton className="h-2 flex-1" />
                  <Skeleton className="h-4 w-12" />
                </div>
                <div className="flex items-center gap-2">
                  <Skeleton className="h-9 w-9" />
                  <Skeleton className="h-2 w-20" />
                </div>
              </div>
              <div className="flex justify-center">
                <Skeleton className="h-9 w-40" />
              </div>
            </div>

            {/* Recording details skeleton */}
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                ))}
              </div>
              <div className="space-y-3">
                {[1, 2].map((i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-4 w-32" />
                  </div>
                ))}
              </div>
            </div>

            {/* Category info skeleton */}
            <div className="mt-4 space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="flex items-start gap-2">
                  <Skeleton className="h-4 w-4" />
                  <div className="flex items-center">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="ml-1 h-6 w-32" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tabs skeleton */}
          <div>
            <div className="mb-4 flex gap-1">
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-10 w-32" />
            </div>
            <div className="bg-card rounded-lg border p-6">
              <div className="pb-3">
                <Skeleton className="h-8 w-32" />
              </div>
              <div className="space-y-4">
                <Skeleton className="h-32 w-full" />
                <Skeleton className="mx-auto h-9 w-48" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
