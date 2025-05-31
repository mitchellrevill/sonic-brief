import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { 
  CheckCircle2, 
  Clock, 
  Upload, 
  AlertCircle, 
  XCircle,
  Loader2 
} from "lucide-react";

const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 font-medium transition-all duration-200 ease-in-out hover:shadow-md focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      status: {
        completed: "bg-emerald-100 text-emerald-700 border border-emerald-200 hover:bg-emerald-200 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800",
        processing: "bg-amber-100 text-amber-700 border border-amber-200 hover:bg-amber-200 dark:bg-amber-900/20 dark:text-amber-400 dark:border-amber-800",
        uploaded: "bg-blue-100 text-blue-700 border border-blue-200 hover:bg-blue-200 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800",
        failed: "bg-red-100 text-red-700 border border-red-200 hover:bg-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
        error: "bg-red-100 text-red-700 border border-red-200 hover:bg-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800",
        default: "bg-gray-100 text-gray-700 border border-gray-200 hover:bg-gray-200 dark:bg-gray-900/20 dark:text-gray-400 dark:border-gray-800",
      },
      size: {
        sm: "px-2 py-1 text-xs rounded-md",
        md: "px-3 py-1.5 text-sm rounded-lg",
        lg: "px-4 py-2 text-base rounded-xl",
      },
      variant: {
        default: "",
        subtle: "border-0 shadow-none",
        outline: "bg-transparent",
      },
    },
    defaultVariants: {
      status: "default",
      size: "md",
      variant: "default",
    },
  }
);

const statusIcons = {
  completed: CheckCircle2,
  processing: Loader2,
  uploaded: Upload,
  failed: XCircle,
  error: AlertCircle,
  default: Clock,
};

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof statusBadgeVariants> {
  status: "completed" | "processing" | "uploaded" | "failed" | "error" | "default";
  showIcon?: boolean;
  animate?: boolean;
}

const StatusBadge = React.forwardRef<HTMLDivElement, StatusBadgeProps>(
  ({ 
    className, 
    status, 
    size, 
    variant, 
    showIcon = true, 
    animate = false,
    children,
    ...props 
  }, ref) => {
    const Icon = statusIcons[status] || statusIcons.default;
    const displayText = children || status.charAt(0).toUpperCase() + status.slice(1);

    return (
      <div
        className={cn(statusBadgeVariants({ status, size, variant, className }))}
        ref={ref}
        role="status"
        aria-label={`Status: ${status}`}
        {...props}
      >
        {showIcon && (
          <Icon 
            className={cn(
              "flex-shrink-0",
              size === "sm" ? "h-3 w-3" : size === "lg" ? "h-5 w-5" : "h-4 w-4",
              status === "processing" && animate && "animate-spin"
            )} 
          />
        )}
        <span className="font-medium">
          {displayText}
        </span>
      </div>
    );
  }
);

StatusBadge.displayName = "StatusBadge";

export { StatusBadge, statusBadgeVariants };
