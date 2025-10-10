import { cn } from "@/lib/utils";

function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "bg-muted rounded-md",
        // Only animate if user hasn't requested reduced motion
        "motion-safe:animate-pulse",
        // Static shimmer effect for reduced motion
        "motion-reduce:bg-gradient-to-r motion-reduce:from-muted motion-reduce:via-muted/50 motion-reduce:to-muted",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };
