import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { User as UserIcon, XCircle, CheckCircle2, Plus } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { registerUser } from "@/lib/api";

interface RegisterUserDialogProps {
  open: boolean;
  setOpen: (open: boolean) => void;
  onRegisterSuccess: () => void;
}

export function RegisterUserDialog({ open, setOpen, onRegisterSuccess }: RegisterUserDialogProps) {
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerLoading, setRegisterLoading] = useState(false);
  const [registerError, setRegisterError] = useState("");
  const [registerSuccess, setRegisterSuccess] = useState("");

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegisterLoading(true);
    setRegisterError("");
    setRegisterSuccess("");
    try {
      const result = await registerUser(registerEmail, registerPassword);
      if (result.status === 201) {
        setRegisterSuccess("User registered successfully!");
        setRegisterEmail("");
        setRegisterPassword("");
        setOpen(false);
        onRegisterSuccess();
        toast.success("User registered successfully!");
      } else {
        setRegisterError(result.message || "Registration failed");
      }
    } catch (error) {
      setRegisterError(error instanceof Error ? error.message : "Registration failed");
    } finally {
      setRegisterLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Register User
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserIcon className="h-5 w-5" />
            Register New User
          </DialogTitle>
          <DialogDescription>
            Create a new user account for the system.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleRegister} className="space-y-4">
          <div>
            <Label htmlFor="register-email">Email</Label>
            <Input
              id="register-email"
              type="email"
              value={registerEmail}
              onChange={e => setRegisterEmail(e.target.value)}
              required
              autoComplete="off"
              placeholder="user@email.com"
            />
          </div>
          <div>
            <Label htmlFor="register-password">Password</Label>
            <Input
              id="register-password"
              type="password"
              value={registerPassword}
              onChange={e => setRegisterPassword(e.target.value)}
              required
              autoComplete="new-password"
              placeholder="Password"
            />
          </div>
          {registerError && (
            <div className="flex items-center gap-2 text-red-600 text-sm">
              <XCircle className="h-4 w-4" />
              {registerError}
            </div>
          )}
          {registerSuccess && (
            <div className="flex items-center gap-2 text-green-600 text-sm">
              <CheckCircle2 className="h-4 w-4" />
              {registerSuccess}
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={registerLoading}>
              {registerLoading ? "Registering..." : "Register User"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
