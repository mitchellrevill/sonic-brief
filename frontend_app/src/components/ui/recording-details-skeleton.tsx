import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

/**
 * Skeleton loader for recording details page
 * Shows while full recording data and transcription are loading
 */
export function RecordingDetailsSkeleton() {
  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-4 w-4" />
        <Skeleton className="h-4 w-32" />
      </div>

      {/* Header Card */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between gap-4">
            <div className="space-y-3 flex-1">
              <Skeleton className="h-8 w-3/4" />
              <div className="flex items-center gap-3">
                <Skeleton className="h-6 w-24 rounded-md" />
                <Skeleton className="h-4 w-40" />
              </div>
            </div>
            <div className="flex gap-2">
              <Skeleton className="h-9 w-9 rounded" />
              <Skeleton className="h-9 w-9 rounded" />
              <Skeleton className="h-9 w-9 rounded" />
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <Skeleton className="h-3 w-16" />
                <Skeleton className="h-4 w-full" />
              </div>
            ))}
          </div>

          <Separator />

          {/* Audio Player */}
          <div className="space-y-3">
            <Skeleton className="h-5 w-32" />
            <div className="flex items-center gap-4">
              <Skeleton className="h-10 w-10 rounded-full" />
              <Skeleton className="h-2 flex-1" />
              <Skeleton className="h-4 w-20" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs Section */}
      <Card>
        <CardHeader>
          <div className="flex gap-4 border-b">
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-32" />
            <Skeleton className="h-10 w-32" />
          </div>
        </CardHeader>
        <CardContent className="pt-6">
          {/* Transcription Content */}
          <div className="space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-4 w-full" style={{ width: `${Math.random() * 30 + 70}%` }} />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
