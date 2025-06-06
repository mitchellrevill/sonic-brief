import { useState } from "react";
import { useUserPermissions } from "@/hooks/usePermissions";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { User, Shield, Lock } from "lucide-react";
import { TranscriptionMethodCard } from "@/components/user-profile/transcription-method-card";
import { SelfPasswordChangeDialog } from "@/components/user-profile/self-password-change-dialog";

export function UserProfile() {
  const { data: userPermissions, isLoading } = useUserPermissions();
  const [isPasswordDialogOpen, setIsPasswordDialogOpen] = useState(false);

  // Helper functions
  const getUserInitials = (email?: string) => {
    if (!email) return "U";
    return email.split('@')[0].slice(0, 2).toUpperCase();
  };

  const getPermissionColor = (permission?: string) => {
    switch (permission) {
      case "Admin":
        return "bg-red-100 text-red-800 border-red-200";
      case "User":
        return "bg-blue-100 text-blue-800 border-blue-200";
      case "Viewer":
        return "bg-gray-100 text-gray-800 border-gray-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <div className="space-y-6">
          <div className="flex items-center space-x-4">
            <div className="h-16 w-16 bg-gray-200 rounded-full animate-pulse" />
            <div className="space-y-2">
              <div className="h-6 w-48 bg-gray-200 rounded animate-pulse" />
              <div className="h-4 w-24 bg-gray-200 rounded animate-pulse" />
            </div>
          </div>
          <div className="grid gap-6 md:grid-cols-2">
            <div className="h-48 bg-gray-200 rounded-lg animate-pulse" />
            <div className="h-48 bg-gray-200 rounded-lg animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (!userPermissions) {
    return (
      <div className="container mx-auto p-6 max-w-4xl">
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-muted-foreground">
              Unable to load user profile. Please try refreshing the page.
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col space-y-4 md:flex-row md:items-center md:justify-between md:space-y-0">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Profile Settings</h1>
            <p className="text-muted-foreground">
              Manage your personal account settings and preferences
            </p>
          </div>
        </div>

        {/* User Info Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Account Information
            </CardTitle>
            <CardDescription>
              Your account details and permissions
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center space-x-4">
              <Avatar className="h-16 w-16">
                <AvatarFallback className="bg-primary/10 text-primary text-lg font-semibold">
                  {getUserInitials(userPermissions.email)}
                </AvatarFallback>
              </Avatar>
              <div className="space-y-2">
                <h3 className="text-xl font-semibold">{userPermissions.email}</h3>
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-muted-foreground" />
                  <Badge
                    variant="outline"
                    className={getPermissionColor(userPermissions.permission)}
                  >
                    {userPermissions.permission}
                  </Badge>
                </div>
              </div>
            </div>
            
            <Separator />
            
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">Email Address</h4>
                <p className="text-sm">{userPermissions.email}</p>
              </div>
              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">Permission Level</h4>
                <p className="text-sm">{userPermissions.permission}</p>
              </div>              <div>
                <h4 className="text-sm font-medium text-muted-foreground mb-2">User ID</h4>
                <p className="text-sm font-mono">{userPermissions.user_id}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Settings Grid */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* Transcription Method Settings */}
          <TranscriptionMethodCard user={userPermissions} />

          {/* Password Settings */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lock className="h-5 w-5" />
                Password & Security
              </CardTitle>
              <CardDescription>
                Update your password to keep your account secure
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Change your password to maintain account security. We recommend using a strong, unique password.
                </p>
              </div>
              <Button 
                onClick={() => setIsPasswordDialogOpen(true)}
                className="w-full"
              >
                <Lock className="mr-2 h-4 w-4" />
                Change Password
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Password Change Dialog */}        <SelfPasswordChangeDialog
          isOpen={isPasswordDialogOpen}
          onClose={() => setIsPasswordDialogOpen(false)}
          userEmail={userPermissions.email}
          userId={userPermissions.user_id}
        />
      </div>
    </div>
  );
}
