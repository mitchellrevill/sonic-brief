import { useEffect, useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { 
  DropdownMenu, 
  DropdownMenuContent, 
  DropdownMenuItem, 
  DropdownMenuTrigger,
  DropdownMenuSeparator 
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { 
  Edit2, 
  MoreVertical, 
  KeyRound, 
  Shield, 
  ShieldCheck, 
  Eye,
  User as UserIcon,
  Calendar,
  Mail,
  Check,
  X
} from "lucide-react";
import { fetchAllUsers } from "@/lib/api"; 
import type { User } from "@/lib/api";
import { updateUserPermission } from "@/lib/api";
import { ChangePasswordDialog } from "./change-password-dialog";

const initialUsers: User[] = [
  { id: "1", name: "", email: "", permission: "Admin" },
];

// Helper function to get user initials
const getUserInitials = (email: string, name?: string) => {
  if (name && name.trim()) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }
  return email.split('@')[0].slice(0, 2).toUpperCase();
};

// Helper function to get permission badge variant and icon
const getPermissionInfo = (permission: User["permission"]) => {
  switch (permission) {
    case "Admin":
      return { 
        variant: "default" as const, 
        icon: Shield, 
        color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200" 
      };
    case "User":
      return { 
        variant: "secondary" as const, 
        icon: ShieldCheck, 
        color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200" 
      };
    case "Viewer":
      return { 
        variant: "outline" as const, 
        icon: Eye, 
        color: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200" 
      };
    default:
      return { 
        variant: "outline" as const, 
        icon: UserIcon, 
        color: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200" 
      };
  }
};


export function UserManagementTable() {
  const [users, setUsers] = useState<User[]>(initialUsers);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editPermission, setEditPermission] = useState<Record<string, User["permission"]>>({});
  const [loading, setLoading] = useState(false);
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const fetchAllUsersApi = async () => {
    setLoading(true);
    try {
      const response: User[] | { users: User[] } = await fetchAllUsers();
      let apiUsers: User[];
      if (Array.isArray(response)) {
        apiUsers = response;
      } else if (response && typeof response === "object" && "users" in response && Array.isArray((response as any).users)) {
        apiUsers = (response as { users: User[] }).users;
      } else {
        apiUsers = [];
      }
      const mappedUsers = apiUsers.map((u: any, idx: number) => {
        let dateStr = "";
        if (u._ts) {
          const d = new Date(u._ts * 1000);
          const day = String(d.getDate()).padStart(2, "0");
          const month = String(d.getMonth() + 1).padStart(2, "0");
          const year = d.getFullYear();
          const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          dateStr = `${day}/${month}/${year} ${time}`;
        }
        return {
          id: u.id || idx,
          name: u.name || u.email || "",
          email: u.email,
          permission: (u.permission as "User" | "Admin" | "Viewer") || "Viewer",
          date: dateStr,
        };
      });
      setUsers(mappedUsers);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllUsersApi();
  }, []);
 
  const startEdit = (user: User) => {
    setEditingId(String(user.id));
    setEditPermission(prev => ({ ...prev, [String(user.id)]: user.permission }));
  };

  const saveEdit = async (id: string) => {
    try {
      const permission = editPermission[id];
      await updateUserPermission(id, permission);
      await fetchAllUsersApi();
    } catch (err) {
      console.error("Failed to update user permission:", err);
    } finally {
      setEditingId(null);
    }
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditPermission({});
  };
  const handleChangePassword = (user: User) => {
    setSelectedUser(user);
    setPasswordDialogOpen(true);
  };

  const handleClosePasswordDialog = () => {
    setPasswordDialogOpen(false);
    setSelectedUser(null);
  };

  const renderPermissionBadge = (permission: User["permission"]) => {
    const permissionInfo = getPermissionInfo(permission);
    const IconComponent = permissionInfo.icon;
    
    return (
      <Badge variant={permissionInfo.variant} className={`${permissionInfo.color} font-medium`}>
        <IconComponent className="w-3 h-3 mr-1" />
        {permission}
      </Badge>
    );
  };

  const renderLoadingSkeleton = () => (
    <div className="space-y-4">
      {[...Array(3)].map((_, i) => (
        <div key={i} className="flex items-center space-x-4 p-4">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-[200px]" />
            <Skeleton className="h-4 w-[150px]" />
          </div>
          <Skeleton className="h-8 w-[100px]" />
          <Skeleton className="h-8 w-8" />
        </div>
      ))}
    </div>
  );

  if (loading && users.length === 1 && users[0].email === "") {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserIcon className="h-5 w-5" />
            User Management
          </CardTitle>
        </CardHeader>
        <CardContent>
          {renderLoadingSkeleton()}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Mobile: Card Layout */}
      <div className="block lg:hidden space-y-4">
        {users.map(user => {
          const userId = String(user.id);
          const isEditing = editingId === userId;
          
          return (
            <Card key={user.id} className="transition-all hover:shadow-md border-l-4 border-l-primary/20">
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
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => startEdit(user)}>
                            <Edit2 className="mr-2 h-4 w-4" />
                            Edit Permissions
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />                          <DropdownMenuItem onClick={() => handleChangePassword(user)}>
                            <KeyRound className="mr-2 h-4 w-4" />
                            Change Password
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
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
                        {isEditing ? (
                          <div className="flex items-center gap-2">
                            <Select
                              value={editPermission[userId] ?? user.permission}
                              onValueChange={(value) =>
                                setEditPermission(prev => ({
                                  ...prev,
                                  [userId]: value as User["permission"],
                                }))
                              }
                            >
                              <SelectTrigger className="w-[120px] h-8">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Admin">
                                  <div className="flex items-center gap-2">
                                    <Shield className="h-3 w-3" />
                                    Admin
                                  </div>
                                </SelectItem>
                                <SelectItem value="User">
                                  <div className="flex items-center gap-2">
                                    <ShieldCheck className="h-3 w-3" />
                                    User
                                  </div>
                                </SelectItem>
                                <SelectItem value="Viewer">
                                  <div className="flex items-center gap-2">
                                    <Eye className="h-3 w-3" />
                                    Viewer
                                  </div>
                                </SelectItem>
                              </SelectContent>
                            </Select>
                            <Button size="sm" variant="ghost" onClick={() => saveEdit(userId)} className="h-8 w-8 p-0">
                              <Check className="h-4 w-4 text-green-600" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={cancelEdit} className="h-8 w-8 p-0">
                              <X className="h-4 w-4 text-red-600" />
                            </Button>
                          </div>
                        ) : (
                          renderPermissionBadge(user.permission)
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Desktop: Table Layout */}
      <div className="hidden lg:block">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <UserIcon className="h-5 w-5" />
              User Management
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow className="border-b">
                  <TableHead className="text-left font-semibold">User</TableHead>
                  <TableHead className="text-left font-semibold">Permission</TableHead>
                  <TableHead className="text-left font-semibold">Date Created</TableHead>
                  <TableHead className="text-right font-semibold">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map(user => {
                  const userId = String(user.id);
                  const isEditing = editingId === userId;
                  
                  return (
                    <TableRow key={user.id} className="hover:bg-muted/50 transition-colors">
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
                        {isEditing ? (
                          <div className="flex items-center gap-2">
                            <Select
                              value={editPermission[userId] ?? user.permission}
                              onValueChange={(value) =>
                                setEditPermission(prev => ({
                                  ...prev,
                                  [userId]: value as User["permission"],
                                }))
                              }
                            >
                              <SelectTrigger className="w-[140px]">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Admin">
                                  <div className="flex items-center gap-2">
                                    <Shield className="h-3 w-3" />
                                    Admin
                                  </div>
                                </SelectItem>
                                <SelectItem value="User">
                                  <div className="flex items-center gap-2">
                                    <ShieldCheck className="h-3 w-3" />
                                    User
                                  </div>
                                </SelectItem>
                                <SelectItem value="Viewer">
                                  <div className="flex items-center gap-2">
                                    <Eye className="h-3 w-3" />
                                    Viewer
                                  </div>
                                </SelectItem>
                              </SelectContent>
                            </Select>
                            <Button size="sm" variant="ghost" onClick={() => saveEdit(userId)}>
                              <Check className="h-4 w-4 text-green-600" />
                            </Button>
                            <Button size="sm" variant="ghost" onClick={cancelEdit}>
                              <X className="h-4 w-4 text-red-600" />
                            </Button>
                          </div>
                        ) : (
                          renderPermissionBadge(user.permission)
                        )}
                      </TableCell>
                      
                      <TableCell>
                        <div className="text-sm">{user.date || "—"}</div>
                      </TableCell>
                      
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleChangePassword(user)}
                            className="h-8"
                          >
                            <KeyRound className="mr-2 h-3 w-3" />
                            Change Password
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => startEdit(user)}
                            disabled={isEditing}
                            className="h-8"
                          >
                            <Edit2 className="mr-2 h-3 w-3" />
                            Edit
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>          </CardContent>
        </Card>
      </div>
      
      {/* Change Password Dialog */}
      {selectedUser && (
        <ChangePasswordDialog
          isOpen={passwordDialogOpen}
          onClose={handleClosePasswordDialog}
          userEmail={selectedUser.email}
          userId={String(selectedUser.id)}
        />
      )}
    </div>
  );
}