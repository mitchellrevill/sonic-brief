import { TableCell, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Skeleton loader for table row in audio recordings table view
 */
export function RecordingTableRowSkeleton() {
  return (
    <TableRow>
      {/* Display Name / Title */}
      <TableCell>
        <div className="space-y-1">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-3 w-32" />
        </div>
      </TableCell>

      {/* Status */}
      <TableCell>
        <Skeleton className="h-6 w-24 rounded-md" />
      </TableCell>

      {/* Date */}
      <TableCell>
        <Skeleton className="h-4 w-28" />
      </TableCell>

      {/* Owner */}
      <TableCell className="hidden md:table-cell">
        <Skeleton className="h-4 w-36" />
      </TableCell>

      {/* Actions */}
      <TableCell>
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-8 w-8 rounded" />
          <Skeleton className="h-8 w-8 rounded" />
        </div>
      </TableCell>
    </TableRow>
  );
}

/**
 * Multiple table row skeletons
 */
export function RecordingTableSkeletonRows({ count = 10 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <RecordingTableRowSkeleton key={`table-skeleton-${index}`} />
      ))}
    </>
  );
}
