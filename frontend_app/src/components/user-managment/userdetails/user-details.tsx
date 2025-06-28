import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { 
  User as UserIcon,
  Shield,
  ShieldCheck,
  Activity,
  Settings,
  UserPlus
} from "lucide-react";
import { 
  fetchUserById, 
  getUserAnalytics, 
  exportUserDetailsPDF, 
  updateUserPermission, 
  changeUserPassword, 
  deleteUser,
  updateUserCapabilities,
  type UserAnalytics 
} from "@/lib/api";
import type { User } from "@/lib/api";
import { PermissionLevel, type UserCapabilities } from "@/types/permissions";
import { UserCapabilityManager } from "../UserManagement/UserCapabilityManager";
import { toast } from "sonner";
import { UserDetailsHeader } from "./UserDetailsHeader";
import { UserInfoCard } from "./UserInfoCard";
import { UserAnalyticsOverview } from "./UserAnalyticsOverview";
import { UserAnalyticsCharts } from "./UserAnalyticsCharts";
import { UserAnalyticsSummary } from "./UserAnalyticsSummary";
import { UserNotFound } from "./UserNotFound";
import { UserDetailsSkeleton } from "./UserDetailsSkeleton";

export function UserDetailsPage() {
  // Extract userId from URL path
  const pathParts = window.location.pathname.split('/');
  const userId = pathParts[pathParts.length - 1];

  const [user, setUser] = useState<User | null>(null);
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [analyticsLoading, setAnalyticsLoading] = useState(true);
  const [exportLoading, setExportLoading] = useState(false);
  
  // User management states
  const [permissionUpdateLoading, setPermissionUpdateLoading] = useState(false);
  const [passwordChangeLoading, setPasswordChangeLoading] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [showPermissionDialog, setShowPermissionDialog] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [newPermission, setNewPermission] = useState<PermissionLevel>(PermissionLevel.USER);
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    if (userId) {
      fetchUserData();
      fetchUserAnalyticsData();
    }
  }, [userId]);

  const fetchUserData = async () => {
    if (!userId) return;
    
    console.log("Fetching user data for userId:", userId);
    setLoading(true);
    try {
      const userData = await fetchUserById(userId);
      console.log("User data received:", userData);
      setUser(userData);
    } catch (error) {
      console.error("Failed to fetch user:", error);
      toast.error("Failed to load user details");
    } finally {
      setLoading(false);
    }
  };

  const fetchUserAnalyticsData = async () => {
    if (!userId) return;
    
    setAnalyticsLoading(true);
    try {
      const analyticsData = await getUserAnalytics(userId);
      console.log("User analytics data received:", analyticsData);
      
      // Check if the response has an error in the analytics field
      if (analyticsData.analytics && 'error' in analyticsData.analytics) {
        console.warn("Analytics data has error:", (analyticsData.analytics as any).error);
        // Set analytics to null or create a default structure
        setAnalytics({
          ...analyticsData,            analytics: {
              transcription_stats: {
                total_minutes: 0,
                total_jobs: 0,
                average_job_duration: 0
              },
              activity_stats: {
                login_count: 0,
                jobs_created: 0,
                last_activity: null
              },
              usage_patterns: {
                most_active_hours: [],
                most_used_transcription_method: null,
                file_upload_count: 0,
                text_input_count: 0
              }
            }
        });
      } else {
        console.log("Analytics total minutes:", analyticsData.analytics?.transcription_stats?.total_minutes);
        setAnalytics(analyticsData as UserAnalytics);
      }
    } catch (error) {
      console.error("Failed to fetch user analytics:", error);
      toast.error("Failed to load user analytics. Please ensure analytics containers are created.");
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!userId) return;
    
    setExportLoading(true);
    try {
      const blob = await exportUserDetailsPDF(userId, true);
      
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `user-${user?.email || userId}-details.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success("User details exported successfully");
    } catch (error) {
      console.error("Failed to export user details:", error);
      toast.error("Failed to export user details");
    } finally {
      setExportLoading(false);
    }
  };

  const handleUpdatePermission = async () => {
    if (!userId || !user) return;
    
    setPermissionUpdateLoading(true);
    try {
      await updateUserPermission(userId, newPermission);
      
      // Refresh user data
      const updatedUser = await fetchUserById(userId);
      setUser(updatedUser);
      
      setShowPermissionDialog(false);
      toast.success(`Permission updated to ${newPermission}`);
    } catch (error: any) {
      console.error("Failed to update permission:", error);
      toast.error(error.message || "Failed to update permission");
    } finally {
      setPermissionUpdateLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!userId || !newPassword.trim()) return;
    
    setPasswordChangeLoading(true);
    try {
      await changeUserPassword(userId, newPassword);
      
      setShowPasswordDialog(false);
      setNewPassword("");
      toast.success("Password changed successfully");
    } catch (error: any) {
      console.error("Failed to change password:", error);
      toast.error(error.message || "Failed to change password");
    } finally {
      setPasswordChangeLoading(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!userId || !user) return;
    
    setDeleteLoading(true);
    try {
      await deleteUser(userId);
      
      setShowDeleteDialog(false);
      toast.success(`User ${user.email} has been deleted`);
      
      // Navigate back to user management
      window.location.href = '/admin/user-management';
    } catch (error: any) {
      console.error("Failed to delete user:", error);
      toast.error(error.message || "Failed to delete user");
    } finally {
      setDeleteLoading(false);
    }
  };

  const getUserInitials = (email: string, name?: string | null) => {
    if (name && typeof name === 'string' && name.trim()) {
      return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
    }
    if (email && typeof email === 'string') {
      return email.split('@')[0].slice(0, 2).toUpperCase();
    }
    return 'U'; // fallback
  };

  const getPermissionInfo = (permission: User["permission"]) => {
    switch (permission) {
      case "Admin":
        return {
          variant: "default" as const,
          icon: Shield,
          color: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200"
        };
      case "Editor":
        return {
          variant: "secondary" as const,
          icon: ShieldCheck,
          color: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
        };
      case "User":
        return {
          variant: "outline" as const,
          icon: UserIcon,
          color: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
        };
      default:
        return {
          variant: "outline" as const,
          icon: UserIcon,
          color: "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200"
        };
    }
  };

  const formatDuration = (minutes: number) => {
    const roundedMinutes = Math.floor(minutes);
    if (roundedMinutes < 60) {
      return `${roundedMinutes}m`;
    }
    const hours = Math.floor(roundedMinutes / 60);
    const remainingMinutes = roundedMinutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  if (loading) {
    return <UserDetailsSkeleton />;
  }

  if (!user) {
    return <UserNotFound />;
  }

  const permissionInfo = getPermissionInfo(user.permission);
  const PermissionIcon = permissionInfo.icon;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <UserDetailsHeader
        user={user}
        exportLoading={exportLoading}
        onExportPDF={handleExportPDF}
        getUserInitials={getUserInitials}
      />
      {/* User Information */}
      <UserInfoCard
        user={user}
        userDate={user.date}
        permissionInfo={permissionInfo}
        PermissionIcon={PermissionIcon}
        newPermission={newPermission}
        setNewPermission={setNewPermission}
        newPassword={newPassword}
        setNewPassword={setNewPassword}
        showPermissionDialog={showPermissionDialog}
        setShowPermissionDialog={setShowPermissionDialog}
        showPasswordDialog={showPasswordDialog}
        setShowPasswordDialog={setShowPasswordDialog}
        showDeleteDialog={showDeleteDialog}
        setShowDeleteDialog={setShowDeleteDialog}
        permissionUpdateLoading={permissionUpdateLoading}
        handleUpdatePermission={handleUpdatePermission}
        passwordChangeLoading={passwordChangeLoading}
        handleChangePassword={handleChangePassword}
        deleteLoading={deleteLoading}
        handleDeleteUser={handleDeleteUser}
      />
      {/* Combined Analytics Overview & Activity Section */}
      {analyticsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-4 w-[100px] mb-2" />
                <Skeleton className="h-8 w-[60px]" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : analytics ? (
        <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg font-semibold">
              <Activity className="h-5 w-5" />
              User Analytics & Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <UserAnalyticsOverview
              totalJobs={analytics.analytics.transcription_stats.total_jobs}
              totalMinutes={formatDuration(analytics.analytics.transcription_stats.total_minutes)}
              avgJobDuration={formatDuration(analytics.analytics.transcription_stats.average_job_duration)}
              loginCount={analytics.analytics.activity_stats.login_count}
            />
            <UserAnalyticsCharts
              barData={[
                { name: 'Jobs Created', value: analytics.analytics.activity_stats.jobs_created || 0, fill: '#4caf50' },
                { name: 'Logins', value: analytics.analytics.activity_stats.login_count || 0, fill: '#2196f3' },
                { name: 'File Uploads', value: analytics.analytics.usage_patterns.file_upload_count || 0, fill: '#ff9800' },
                { name: 'Text Inputs', value: analytics.analytics.usage_patterns.text_input_count || 0, fill: '#9c27b0' }
              ]}
              pieData={[
                { name: 'File Uploads', value: analytics.analytics.usage_patterns.file_upload_count || 0, fill: '#ff9800' },
                { name: 'Text Inputs', value: analytics.analytics.usage_patterns.text_input_count || 0, fill: '#9c27b0' }
              ].filter(item => item.value > 0)}
            />
            <UserAnalyticsSummary
              lastActivity={analytics.analytics.activity_stats.last_activity}
              jobsCreated={analytics.analytics.activity_stats.jobs_created}
            />
          </CardContent>
        </Card>
      ) : (
        <div className="text-center text-muted-foreground">
          No analytics data available for this user.
        </div>
      )}
      
      {/* User Capability Management */}
      {user && (
        <div className="space-y-6">
          {/* Permission Overview */}
          <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                <Shield className="h-5 w-5" />
                Permission Overview
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-lg font-semibold">{user.permission}</div>
                  <div className="text-sm text-muted-foreground">Current Level</div>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-lg font-semibold">
                    {user.custom_capabilities ? Object.values(user.custom_capabilities).filter(Boolean).length : 0}
                  </div>
                  <div className="text-sm text-muted-foreground">Custom Capabilities</div>
                </div>
                <div className="text-center p-4 border rounded-lg">
                  <div className="text-lg font-semibold">
                    {user.date ? new Date(user.date).toLocaleDateString() : 'N/A'}
                  </div>
                  <div className="text-sm text-muted-foreground">Permission Set Date</div>
                </div>
              </div>
              
              {/* Quick Actions */}
              <div className="flex flex-wrap gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setShowPermissionDialog(true)}
                  className="flex items-center gap-2"
                >
                  <Settings className="h-4 w-4" />
                  Change Permission Level
                </Button>
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => setShowPasswordDialog(true)}
                  className="flex items-center gap-2"
                >
                  <Shield className="h-4 w-4" />
                  Reset Password
                </Button>
                <Button 
                  variant="destructive" 
                  size="sm" 
                  onClick={() => setShowDeleteDialog(true)}
                  className="flex items-center gap-2"
                >
                  <UserPlus className="h-4 w-4" />
                  Delete User
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Detailed Capability Management */}
          <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                <Shield className="h-5 w-5" />
                Detailed Permission Capabilities
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Manage granular permissions and capabilities for this user
              </p>
            </CardHeader>
            <CardContent>
              <UserCapabilityManager
                user={{
                  id: user.id,
                  email: user.email,
                  permission: user.permission,
                  custom_capabilities: user.custom_capabilities,
                  created_at: user.date || new Date().toISOString(),
                  updated_at: new Date().toISOString(),
                }}
                onUpdateCapabilities={async (userId: string, capabilities: UserCapabilities) => {
                  try {
                    await updateUserCapabilities(userId, { custom_capabilities: capabilities });
                    // Refresh user data
                    const updatedUser = await fetchUserById(userId);
                    setUser(updatedUser);
                  } catch (error: any) {
                    throw new Error(error.message || "Failed to update capabilities");
                  }
                }}
              />
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
