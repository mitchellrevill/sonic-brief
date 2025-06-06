import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { KeyRound, Eye, EyeOff, AlertCircle, Loader2 } from "lucide-react";
import { changeUserPassword } from "@/lib/api";
import { toast } from "sonner";

interface SelfPasswordChangeDialogProps {
  isOpen: boolean;
  onClose: () => void;
  userEmail: string;
  userId: string;
}

export function SelfPasswordChangeDialog({ 
  isOpen, 
  onClose, 
  userEmail, 
  userId 
}: SelfPasswordChangeDialogProps) {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validatePassword = (password: string): string[] => {
    const validationErrors: string[] = [];
    
    if (password.length < 8) {
      validationErrors.push("Password must be at least 8 characters long");
    }
    if (!/(?=.*[a-z])/.test(password)) {
      validationErrors.push("Password must contain at least one lowercase letter");
    }
    if (!/(?=.*[A-Z])/.test(password)) {
      validationErrors.push("Password must contain at least one uppercase letter");
    }
    if (!/(?=.*\d)/.test(password)) {
      validationErrors.push("Password must contain at least one number");
    }
    if (!/(?=.*[@$!%*?&])/.test(password)) {
      validationErrors.push("Password must contain at least one special character (@$!%*?&)");
    }
    
    return validationErrors;
  };

  const handlePasswordChange = (password: string) => {
    setNewPassword(password);
    const validationErrors = validatePassword(password);
    
    if (confirmPassword && password !== confirmPassword) {
      validationErrors.push("Passwords do not match");
    }
    
    setErrors(validationErrors);
  };

  const handleConfirmPasswordChange = (password: string) => {
    setConfirmPassword(password);
    const validationErrors = validatePassword(newPassword);
    
    if (password && newPassword !== password) {
      validationErrors.push("Passwords do not match");
    }
    
    setErrors(validationErrors);
  };

  const handleSubmit = async () => {
    const validationErrors = validatePassword(newPassword);
    
    if (newPassword !== confirmPassword) {
      validationErrors.push("Passwords do not match");
    }
    
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }
    
    setIsSubmitting(true);
    try {
      await changeUserPassword(userId, newPassword);
      
      toast.success(`Password changed successfully for ${userEmail}`);
      
      // Reset form
      setNewPassword("");
      setConfirmPassword("");
      setErrors([]);
      onClose();
    } catch (error) {
      console.error("Error changing password:", error);
      toast.error(error instanceof Error ? error.message : "Failed to change password");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!isSubmitting) {
      setNewPassword("");
      setConfirmPassword("");
      setErrors([]);
      onClose();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5 text-primary" />
            Change Your Password
          </DialogTitle>
          <DialogDescription>
            Update your password to keep your account secure. Your new password must meet security requirements.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* New Password Field */}
          <div className="space-y-2">
            <Label htmlFor="new-password">New Password</Label>
            <div className="relative">
              <Input
                id="new-password"
                type={showPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => handlePasswordChange(e.target.value)}
                placeholder="Enter new password"
                disabled={isSubmitting}
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowPassword(!showPassword)}
                disabled={isSubmitting}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Confirm Password Field */}
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm New Password</Label>
            <div className="relative">
              <Input
                id="confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => handleConfirmPasswordChange(e.target.value)}
                placeholder="Confirm new password"
                disabled={isSubmitting}
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                disabled={isSubmitting}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Password Requirements */}
          <div className="rounded-lg bg-muted/50 p-3 text-sm">
            <p className="font-medium mb-2">Password Requirements:</p>
            <ul className="space-y-1 text-muted-foreground">
              <li>• At least 8 characters long</li>
              <li>• Contains uppercase and lowercase letters</li>
              <li>• Contains at least one number</li>
              <li>• Contains at least one special character (@$!%*?&)</li>
            </ul>
          </div>

          {/* Error Messages */}
          {errors.length > 0 && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <ul className="list-disc list-inside space-y-1">
                  {errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button 
            variant="outline" 
            onClick={handleClose} 
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={isSubmitting || errors.length > 0 || !newPassword || !confirmPassword}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Changing Password...
              </>
            ) : (
              "Change Password"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
