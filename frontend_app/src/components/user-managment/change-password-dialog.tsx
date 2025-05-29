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
import { KeyRound, Eye, EyeOff, AlertCircle } from "lucide-react";

interface ChangePasswordDialogProps {
  isOpen: boolean;
  onClose: () => void;
  userEmail: string;
  userId: string;
}

export function ChangePasswordDialog({ 
  isOpen, 
  onClose, 
  userEmail, 
  userId 
}: ChangePasswordDialogProps) {
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

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

  const handleSubmit = () => {
    const validationErrors = validatePassword(newPassword);
    
    if (newPassword !== confirmPassword) {
      validationErrors.push("Passwords do not match");
    }
    
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }
    
    // TODO: Implement actual password change API call
    console.log("Change password for user:", userId, "New password:", newPassword);
    
    // Reset form and close dialog
    setNewPassword("");
    setConfirmPassword("");
    setErrors([]);
    onClose();
  };

  const handleClose = () => {
    setNewPassword("");
    setConfirmPassword("");
    setErrors([]);
    onClose();
  };

  const isValid = newPassword.length > 0 && 
                  confirmPassword.length > 0 && 
                  errors.length === 0;

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <KeyRound className="h-5 w-5" />
            Change Password
          </DialogTitle>
          <DialogDescription>
            Set a new password for <strong>{userEmail}</strong>
          </DialogDescription>
        </DialogHeader>
        
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="new-password">New Password</Label>
            <div className="relative">
              <Input
                id="new-password"
                type={showPassword ? "text" : "password"}
                value={newPassword}
                onChange={(e) => handlePasswordChange(e.target.value)}
                placeholder="Enter new password"
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </div>
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="confirm-password">Confirm Password</Label>
            <div className="relative">
              <Input
                id="confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => handleConfirmPasswordChange(e.target.value)}
                placeholder="Confirm new password"
                className="pr-10"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
              >
                {showConfirmPassword ? (
                  <EyeOff className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <Eye className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </div>
          </div>
          
          {errors.length > 0 && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <ul className="mt-1 space-y-1">
                  {errors.map((error, index) => (
                    <li key={index} className="text-sm">• {error}</li>
                  ))}
                </ul>
              </AlertDescription>
            </Alert>
          )}
          
          <div className="text-xs text-muted-foreground">
            <p className="font-medium mb-1">Password requirements:</p>
            <ul className="space-y-1">
              <li>• At least 8 characters long</li>
              <li>• Contains uppercase and lowercase letters</li>
              <li>• Contains at least one number</li>
              <li>• Contains at least one special character (@$!%*?&)</li>
            </ul>
          </div>
        </div>
        
        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button 
            onClick={handleSubmit} 
            disabled={!isValid}
            className="min-w-[100px]"
          >
            Change Password
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
