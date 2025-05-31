import { Button } from "@/components/ui/button";
import { SmartBreadcrumb } from "@/components/ui/smart-breadcrumb";
import { Users, UserPlus, RefreshCw } from "lucide-react";

interface UserManagementHeaderProps {
  onRefresh?: () => void;
  onAddUser?: () => void;
  loading?: boolean;
}

export function UserManagementHeader({ 
  onRefresh, 
  onAddUser, 
  loading = false 
}: UserManagementHeaderProps) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between px-2 py-2 md:px-4 md:py-3 border-b bg-card/50">
      <div className="space-y-1 text-center md:text-left">
        <div className="flex items-center justify-center md:justify-start gap-2">
          <Users className="h-6 w-6 text-primary" />
          <h2 className="text-lg md:text-2xl font-semibold tracking-tight">
            User Management
          </h2>
        </div>        <SmartBreadcrumb
          items={[{ label: "User Management", isCurrentPage: true }]}
          className="justify-center md:justify-start"
        />
        <p className="text-muted-foreground text-xs md:text-sm max-w-2xl">
          Manage user accounts, permissions, and access controls. Monitor user activity and maintain system security.
        </p>
      </div>
      
      <div className="flex flex-col sm:flex-row gap-2 justify-center md:justify-end">
        {onRefresh && (
          <Button 
            variant="outline" 
            size="sm" 
            onClick={onRefresh}
            disabled={loading}
            className="px-3 py-2"
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </Button>
        )}
        {onAddUser && (
          <Button 
            size="sm" 
            onClick={onAddUser}
            className="px-3 py-2"
          >
            <UserPlus className="mr-2 h-4 w-4" />
            <span className="hidden sm:inline">Add User</span>
          </Button>
        )}
      </div>
    </div>
  );
}
