import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Eye, Users } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { getUserInitials, getPermissionInfo } from "./helpers";
import type { User } from "@/lib/api";

interface UserTableProps {
  users: User[];
  onUserClick: (userId: string) => void;
  totalUsers: number;
}

export function UserTable({ users, onUserClick, totalUsers }: UserTableProps) {
  return (
    <div className="hidden lg:block">
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              All Users ({totalUsers})
            </CardTitle>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow className="border-b">
                <TableHead className="text-left font-semibold">User</TableHead>
                <TableHead className="text-left font-semibold">Permission</TableHead>
                <TableHead className="text-left font-semibold">Date Created</TableHead>
                <TableHead className="text-center font-semibold">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.map(user => {
                const permissionInfo = getPermissionInfo(user.permission);
                const IconComponent = permissionInfo.icon;
                return (
                  <TableRow
                    key={user.id}
                    className="hover:bg-muted/50 transition-colors cursor-pointer"
                    onClick={() => onUserClick(String(user.id))}
                  >
                    <TableCell className="py-4">
                      <div className="flex items-center gap-3">
                        <Avatar className="h-10 w-10">
                          <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                            {getUserInitials(user.email, user.name)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <div className="font-medium">{user.email}</div>
                          <div className="text-sm text-muted-foreground">ID: {user.id}</div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={permissionInfo.variant} className={`${permissionInfo.color} font-medium`}>
                        <IconComponent className="w-3 h-3 mr-1" />
                        {user.permission}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">{user.date || "—"}</div>
                    </TableCell>
                    <TableCell className="text-center">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={e => {
                          e.stopPropagation();
                          onUserClick(String(user.id));
                        }}
                        className="h-8"
                      >
                        <Eye className="mr-2 h-3 w-3" />
                        View Details
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
