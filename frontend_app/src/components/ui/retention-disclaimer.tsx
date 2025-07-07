import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Info } from "lucide-react";
import { useState, useEffect } from "react";

interface RetentionDisclaimerProps {
  className?: string;
  variant?: "default" | "destructive";
}

export function RetentionDisclaimer({
  className = "",
  variant = "default",
}: RetentionDisclaimerProps) {

  // Use localStorage to persist dismissal across refreshes
  const STORAGE_KEY = "retentionDisclaimerDismissed";
  const [isVisible, setIsVisible] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(STORAGE_KEY) !== "true";
    }
    return true;
  });

  useEffect(() => {
    if (!isVisible) {
      localStorage.setItem(STORAGE_KEY, "true");
    }
  }, [isVisible]);

  if (!isVisible) return null;

  return (
    <Alert
      variant={variant}
      className={`relative border-amber-200 bg-amber-50 text-amber-800 px-4 py-3 sm:px-6 sm:py-4 rounded-lg shadow-md flex flex-col sm:flex-row items-start gap-3 ${className}`}
      role="alert"
    >
      <div className="flex items-start flex-1 min-w-0">
        <Info
          className="h-5 w-5 text-amber-600 mt-0.5 mr-3 flex-shrink-0"
          aria-hidden="true"
        />
        <AlertDescription className="text-sm leading-relaxed break-words flex-1">
          <span className="font-medium">30-day retention:</span> All audio and content are deleted after 30 days.
        </AlertDescription>
        <Button
          variant="outline"
          size="default"
          aria-label="Acknowledge retention policy"
          className="ml-4 text-amber-800 border-amber-300 bg-amber-100 hover:bg-amber-200 hover:text-amber-900 font-semibold shadow-sm px-4 py-1.5 h-auto min-w-[110px]"
          onClick={() => setIsVisible(false)}
        >
          Acknowledge
        </Button>
      </div>
    </Alert>
  );
}
