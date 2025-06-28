import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PermissionLevel } from "@/types/permissions";
import type { User } from "@/lib/api";

interface UserDistributionCardProps {
  users: User[];
}

export function UserDistributionCard({ users }: UserDistributionCardProps) {
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

  const permissionCounts = users.reduce((acc, user) => {
    acc[user.permission] = (acc[user.permission] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">User Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {Object.entries(permissionCounts).map(([permission, count]) => (
            <div key={permission} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Badge className={getPermissionBadgeColor(permission as PermissionLevel)}>
                  {permission}
                </Badge>
              </div>
              <span className="font-medium">{count} users</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
