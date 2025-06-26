import { Card, CardContent } from "@/components/ui/card";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Eye, Mail, Calendar } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { getUserInitials, getPermissionInfo } from "./helpers";
import type { User } from "@/lib/api";

interface UserCardListProps {
  users: User[];
  onUserClick: (userId: string) => void;
}

export function UserCardList({ users, onUserClick }: UserCardListProps) {
  return (
    <div className="block lg:hidden space-y-4">
      {users.map(user => {
        const permissionInfo = getPermissionInfo(user.permission);
        const IconComponent = permissionInfo.icon;
        return (
          <Card 
            key={user.id} 
            className="transition-all hover:shadow-md border-l-4 border-l-primary/20 cursor-pointer"
            onClick={() => onUserClick(String(user.id))}
          >
            <CardContent className="p-4">
              <div className="flex items-start gap-3">
                <Avatar className="h-12 w-12">
                  <AvatarFallback className="bg-primary/10 text-primary font-semibold">
                    {getUserInitials(user.email, user.name)}
                  </AvatarFallback>
                </Avatar>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-sm truncate">{user.email}</h3>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0"
                      onClick={e => {
                        e.stopPropagation();
                        onUserClick(String(user.id));
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Mail className="h-3 w-3" />
                      ID: {user.id}
                    </div>
                    {user.date && (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Calendar className="h-3 w-3" />
                        {user.date}
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">Permission:</span>
                      <Badge variant={permissionInfo.variant} className={`${permissionInfo.color} font-medium`}>
                        <IconComponent className="w-3 h-3 mr-1" />
                        {user.permission}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
