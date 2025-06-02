import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AlertCircle, ExternalLink } from "lucide-react";
import { getFileNameFromPath } from "@/lib/file-utils";

interface FormatWarningDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  filePath: string;
  onContinue: () => void;
}

export function FormatWarningDialog({
  isOpen,
  onOpenChange,
  filePath,
  onContinue,
}: FormatWarningDialogProps) {
  const fileName = getFileNameFromPath(filePath);
  
  const handleOpenInTab = () => {
    window.open(filePath, "_blank");
    onOpenChange(false);
  };
  
  const handleContinue = () => {
    onContinue();
    onOpenChange(false);
  };
  
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-amber-500" />
            Unsupported Format
          </DialogTitle>
          <DialogDescription>
            The file format may not be supported by the in-app audio player.
          </DialogDescription>
        </DialogHeader>
        
        <div className="py-4 space-y-3">
          <p className="text-sm">
            <span className="font-medium">Filename:</span>{" "}
            <span className="font-mono text-muted-foreground break-all">
              {fileName}
            </span>
          </p>
          <p className="text-sm">
            You can try playing it in the in-app player, but it may not work correctly.
            Alternatively, you can open it in a new browser tab.
          </p>
        </div>
        
        <DialogFooter className="flex flex-col sm:flex-row gap-2">
          <Button variant="outline" onClick={handleOpenInTab}>
            <ExternalLink className="mr-2 h-4 w-4" />
            Open in new tab
          </Button>
          <Button onClick={handleContinue}>
            Try in-app player
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
