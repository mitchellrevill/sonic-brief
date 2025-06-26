import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Download, ArrowLeft } from "lucide-react";
import type { User } from "@/lib/api";

interface UserDetailsHeaderProps {
  user: User;
  exportLoading: boolean;
  onExportPDF: () => void;
  getUserInitials: (email: string, name?: string | null) => string;
}

export function UserDetailsHeader({ user, exportLoading, onExportPDF, getUserInitials }: UserDetailsHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            window.location.href = '/admin/user-management';
          }}
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Users
        </Button>
        <div className="flex items-center gap-4">
          <Avatar className="h-12 w-12">
            <AvatarFallback className="bg-primary/10 text-primary font-semibold text-lg">
              {getUserInitials(user.email, user.name)}
            </AvatarFallback>
          </Avatar>
          <div>
            <h1 className="text-2xl font-bold">{user.name || user.email}</h1>
            <p className="text-muted-foreground">User Details & Analytics</p>
          </div>
        </div>
      </div>
      <Button
        onClick={onExportPDF}
        disabled={exportLoading}
        variant="outline"
      >
        {exportLoading ? (
          <>
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
            Exporting...
          </>
        ) : (
          <>
            <Download className="mr-2 h-4 w-4" />
            Export PDF
          </>
        )}
      </Button>
    </div>
  );
}
