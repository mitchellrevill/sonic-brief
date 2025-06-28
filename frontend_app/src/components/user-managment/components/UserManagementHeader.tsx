import { Button } from "@/components/ui/button";
import { UserPlus } from "lucide-react";
import { PermissionGuard } from "@/lib/permission";
import { Capability } from "@/types/permissions";

interface UserManagementHeaderProps {
  onAddUser?: () => void;
}

export function UserManagementHeader({ onAddUser }: UserManagementHeaderProps) {
  return (
    <div className="flex justify-between items-center">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">User Management</h1>
        <p className="text-muted-foreground">
          Monitor user activity, manage permissions, and track system analytics
        </p>
      </div>
      <PermissionGuard requiredCapability={Capability.CAN_CREATE_USERS}>
        <Button className="flex items-center gap-2" onClick={onAddUser}>
          <UserPlus className="h-4 w-4" />
          Add User
        </Button>
      </PermissionGuard>
    </div>
  );
}
