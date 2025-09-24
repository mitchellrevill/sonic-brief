import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { AnalysisRefinementChat } from "./analysis-refinement-chat";
import { MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

interface FloatingAnalysisChatProps {
  jobId: string;
  hasAnalysis?: boolean;
  className?: string;
}

export function FloatingAnalysisChat({ 
  jobId, 
  hasAnalysis = true,
  className 
}: FloatingAnalysisChatProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!hasAnalysis) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      {/* Floating Trigger Button */}
      <DialogTrigger asChild>
        <Button
          size="icon"
          className={cn(
            "fixed bottom-6 right-4 z-50 h-14 w-14 rounded-full shadow-lg transition-all duration-300 hover:scale-110 bg-primary text-primary-foreground hover:bg-primary/90",
            "md:bottom-8 md:right-6",
            className
          )}
          aria-label="Open Analysis Refinement Chat"
        >
          <MessageSquare className="h-6 w-6" />
        </Button>
      </DialogTrigger>      {/* Chat Dialog */}
      <DialogContent className="sm:max-w-4xl max-h-[90vh] flex flex-col p-0 gap-0">
        <DialogHeader className="px-6 py-4 border-b bg-muted/30">
          <DialogTitle className="flex items-center gap-3">
            <span className="bg-primary/10 rounded-full p-2.5">
              <MessageSquare className="text-primary h-5 w-5" />
            </span>
            <div>
              <div className="text-lg font-semibold">Refine Your Analysis</div>
              <p className="text-sm text-muted-foreground font-normal mt-1">
                Chat with AI to refine and explore your analysis results
              </p>
            </div>
          </DialogTitle>
        </DialogHeader>
        
        <div className="flex-1 min-h-0">
          <AnalysisRefinementChat 
            jobId={jobId}
            className="border-0 bg-transparent h-full rounded-none"
          />
        </div>
      </DialogContent>
    </Dialog>
  );
}
