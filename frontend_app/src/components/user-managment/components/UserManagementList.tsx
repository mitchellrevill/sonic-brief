import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Users, Settings } from "lucide-react";
import { PermissionLevel } from "@/types/permissions";
import type { User } from "@/lib/api";

interface UserManagementListProps {
  users: User[];
  usersLoading: boolean;
  searchTerm: string;
  setSearchTerm: (term: string) => void;
  filterPermission: "All" | PermissionLevel;
  setFilterPermission: (filter: "All" | PermissionLevel) => void;
  filteredUsers: User[];
  onUserClick: (userId: string) => void;
}

export function UserManagementList({
  users,
  usersLoading,
  searchTerm,
  setSearchTerm,
  filterPermission,
  setFilterPermission,
  filteredUsers,
  onUserClick
}: UserManagementListProps) {
  const getPermissionBadgeColor = (permission: PermissionLevel) => {
    switch (permission) {
      case PermissionLevel.ADMIN:
        return "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200";
      case PermissionLevel.EDITOR:
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      case PermissionLevel.USER:
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      default:
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
    }
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="flex items-center gap-2">
          <Users className="h-5 w-5" />
          User Management
        </CardTitle>
        <div className="flex gap-2">
          <Select 
            value={filterPermission} 
            onValueChange={(value) => setFilterPermission(value as "All" | PermissionLevel)}
          >
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Filter by permission" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="All">All Permissions</SelectItem>
              <SelectItem value={PermissionLevel.ADMIN}>Admin</SelectItem>
              <SelectItem value={PermissionLevel.EDITOR}>Editor</SelectItem>
              <SelectItem value={PermissionLevel.USER}>User</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <Input
          placeholder="Search by email or name..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full"
        />
        <div className="text-sm text-muted-foreground mb-2">
          Showing {filteredUsers.length} of {users.length} users
        </div>
        {usersLoading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-muted rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredUsers.map(user => (
              <div
                key={user.id}
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 cursor-pointer"
                onClick={() => onUserClick(user.id)}
              >
                <div>
                  <div className="font-medium">{user.email}</div>
                  {user.name && (
                    <div className="text-sm text-muted-foreground">{user.name}</div>
                  )}
                  <div className="text-xs text-muted-foreground">
                    Created: {user.date ? new Date(user.date).toLocaleDateString() : 'N/A'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={getPermissionBadgeColor(user.permission)}>
                    {user.permission}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="p-2"
                    onClick={(e) => {
                      e.stopPropagation();
                      onUserClick(user.id);
                    }}
                  >
                    <Settings className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
