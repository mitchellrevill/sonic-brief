import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { User as UserIcon, Mail, Calendar, Shield, Edit, Key, Trash2, AlertTriangle } from "lucide-react";
import type { User } from "@/lib/api";

interface UserInfoCardProps {
  user: User;
  userDate?: string;
  permissionInfo: any;
  PermissionIcon: any;
  newPermission: "User" | "Admin" | "Editor";
  setNewPermission: (p: "User" | "Admin" | "Editor") => void;
  newPassword: string;
  setNewPassword: (p: string) => void;
  showPermissionDialog: boolean;
  setShowPermissionDialog: (b: boolean) => void;
  showPasswordDialog: boolean;
  setShowPasswordDialog: (b: boolean) => void;
  showDeleteDialog: boolean;
  setShowDeleteDialog: (b: boolean) => void;
  permissionUpdateLoading: boolean;
  handleUpdatePermission: () => void;
  passwordChangeLoading: boolean;
  handleChangePassword: () => void;
  deleteLoading: boolean;
  handleDeleteUser: () => void;
}

export function UserInfoCard(props: UserInfoCardProps) {
  const {
    user, userDate, permissionInfo, PermissionIcon,
    newPermission, setNewPermission, newPassword, setNewPassword,
    showPermissionDialog, setShowPermissionDialog,
    showPasswordDialog, setShowPasswordDialog,
    showDeleteDialog, setShowDeleteDialog,
    permissionUpdateLoading, handleUpdatePermission,
    passwordChangeLoading, handleChangePassword,
    deleteLoading, handleDeleteUser
  } = props;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <UserIcon className="h-5 w-5" />
            User Information
          </div>
          <div className="flex items-center gap-2">
            {/* Permission Update */}
            <Dialog open={showPermissionDialog} onOpenChange={setShowPermissionDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" onClick={() => setNewPermission(user.permission)}>
                  <Edit className="h-4 w-4 mr-2" />
                  Change Permission
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Update User Permission</DialogTitle>
                  <DialogDescription>
                    Change the permission level for {user.email}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="permission">Permission Level</Label>
                    <Select value={newPermission} onValueChange={(value: "User" | "Admin" | "Editor") => setNewPermission(value)}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="User">User</SelectItem>
                        <SelectItem value="Editor">Editor</SelectItem>
                        <SelectItem value="Admin">Admin</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowPermissionDialog(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleUpdatePermission} disabled={permissionUpdateLoading}>
                    {permissionUpdateLoading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Updating...
                      </>
                    ) : (
                      "Update Permission"
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            {/* Password Change */}
            <Dialog open={showPasswordDialog} onOpenChange={setShowPasswordDialog}>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm">
                  <Key className="h-4 w-4 mr-2" />
                  Change Password
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Change User Password</DialogTitle>
                  <DialogDescription>
                    Set a new password for {user.email}
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div>
                    <Label htmlFor="password">New Password</Label>
                    <Input
                      id="password"
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder="Enter new password"
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => {
                    setShowPasswordDialog(false);
                    setNewPassword("");
                  }}>
                    Cancel
                  </Button>
                  <Button onClick={handleChangePassword} disabled={passwordChangeLoading || !newPassword.trim()}>
                    {passwordChangeLoading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Changing...
                      </>
                    ) : (
                      "Change Password"
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            {/* Delete User */}
            <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
              <DialogTrigger asChild>
                <Button variant="destructive" size="sm">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete User
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-destructive" />
                    Delete User Account
                  </DialogTitle>
                  <DialogDescription>
                    This action cannot be undone. This will permanently delete the user account for{" "}
                    <span className="font-semibold">{user.email}</span> and remove all associated data.
                  </DialogDescription>
                </DialogHeader>
                <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                  <p className="text-sm text-destructive">
                    <strong>Warning:</strong> All user data, transcription history, and analytics will be permanently removed.
                  </p>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
                    Cancel
                  </Button>
                  <Button variant="destructive" onClick={handleDeleteUser} disabled={deleteLoading}>
                    {deleteLoading ? (
                      <>
                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                        Deleting...
                      </>
                    ) : (
                      <>
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete User
                      </>
                    )}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-4">
          <Mail className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">Email:</span>
          <span>{user.email}</span>
        </div>
        <div className="flex items-center gap-4">
          <Shield className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">Permission:</span>
          <Badge variant={permissionInfo.variant} className={`${permissionInfo.color} font-medium`}>
            <PermissionIcon className="w-3 h-3 mr-1" />
            {user.permission}
          </Badge>
        </div>
        <div className="flex items-center gap-4">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <span className="font-medium">User ID:</span>
          <span className="font-mono text-sm">{user.id}</span>
        </div>
        {userDate && (
          <div className="flex items-center gap-4">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">Created:</span>
            <span>{userDate}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
