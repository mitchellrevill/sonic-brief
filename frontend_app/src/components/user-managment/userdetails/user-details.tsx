import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { 
  User as UserIcon,
  Shield,
  ShieldCheck
} from "lucide-react";
import { 
  fetchUserById, 
  getUserAnalytics, 
  getUserMinutes,
  exportUserDetailsPDF, 
  updateUserPermission, 
  changeUserPassword, 
  deleteUser,
  getUserAuditLogs,
  type UserAnalytics,
  type UserAuditLogsResponse
} from "@/lib/api";
import type { User } from "@/lib/api";
import { PermissionLevel } from "@/types/permissions";
import { toast } from "sonner";
import { UserDetailsHeader } from "./UserDetailsHeader";
import { UserInfoCard } from "./UserInfoCard";
import { UserAnalyticsOverview } from "./UserAnalyticsOverview";
import { UserAnalyticsSummary } from "./UserAnalyticsSummary";
import { UserNotFound } from "./UserNotFound";
import { UserDetailsSkeleton } from "./UserDetailsSkeleton";
import { Link } from "@tanstack/react-router";

export function UserDetailsPage() {
  // Extract userId from URL path
  const pathParts = window.location.pathname.split('/');
  const userId = pathParts[pathParts.length - 1];

  const [user, setUser] = useState<User | null>(null);
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(null);
  const [userMinutes, setUserMinutes] = useState<{ total_minutes: number; total_records: number } | null>(null);
  const [analyticsError, setAnalyticsError] = useState<string | null>(null);
  const reloadRef = useRef<HTMLButtonElement>(null);
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

  // Scope and audit log states
  const [scopeDays, setScopeDays] = useState<number>(30);
  const [auditLogs, setAuditLogs] = useState<UserAuditLogsResponse | null>(null);
  const [auditLoading, setAuditLoading] = useState<boolean>(false);

  const analyticsApiUrl = `${import.meta.env.VITE_API_URL}/api/analytics/users/${userId}/analytics?days=${scopeDays}`;

  useEffect(() => {
    if (userId) {
      fetchUserData();
    }
  }, [userId]);

  useEffect(() => {
    if (userId) {
      fetchUserAnalyticsData();
      fetchAuditLogs();
    }
  }, [userId, scopeDays]);

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
    setAnalyticsError(null);
    try {
      const analyticsData = await getUserAnalytics(userId, scopeDays);
      console.log("User analytics data received:", analyticsData);
      
      // Check if the response has an error in the analytics field
      if (analyticsData.analytics && 'error' in analyticsData.analytics) {
        const errorMsg = (analyticsData.analytics as any).error || 'Unknown analytics error';
        setAnalyticsError(`Analytics error: ${errorMsg}`);
        setAnalytics({
          ...analyticsData,
          analytics: {
            transcription_stats: {
              total_minutes: 0,
              total_jobs: 0,
              average_job_duration: 0
            },
            activity_stats: {
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
        setAnalytics(analyticsData as UserAnalytics);
      }

      // Fetch per-job minutes summary
      try {
        const minutes = await getUserMinutes(userId, scopeDays);
        setUserMinutes({ total_minutes: minutes.total_minutes, total_records: minutes.total_records });
      } catch (e) {
        console.debug('User minutes fetch failed:', e);
      }
    } catch (error: any) {
      console.error("Failed to fetch user analytics:", error);
      setAnalyticsError(error?.message || "Failed to load user analytics. Please ensure analytics containers are created.");
      toast.error("Failed to load user analytics. Please ensure analytics containers are created.");
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const fetchAuditLogs = async () => {
    if (!userId) return;
    setAuditLoading(true);
    try {
      const logs = await getUserAuditLogs(userId, scopeDays);
      setAuditLogs(logs);
    } catch (e) {
      console.debug('Audit logs fetch failed:', e);
      setAuditLogs(null);
    } finally {
      setAuditLoading(false);
    }
  };

  const handleExportPDF = async () => {
    if (!userId) return;
    
    setExportLoading(true);
    try {
  const blob = await exportUserDetailsPDF(userId, true, scopeDays);
      
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
    if (!minutes || isNaN(minutes) || minutes === 0) return `0m`;
    // Show seconds for durations under 1 minute
    if (minutes < 1) {
      const secs = Math.round(minutes * 60);
      return `${secs}s`;
    }
    const roundedMinutes = Math.floor(minutes);
    if (roundedMinutes < 60) {
      return `${roundedMinutes}m`;
    }
    const hours = Math.floor(roundedMinutes / 60);
    const remainingMinutes = roundedMinutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  // Derived analytics values: prefer explicit analytics fields, fall back to userMinutes records
  const derivedTotalMinutes = userMinutes?.total_minutes ?? analytics?.analytics?.transcription_stats?.total_minutes ?? 0;
  const derivedTotalJobs = analytics?.analytics?.transcription_stats?.total_jobs ?? userMinutes?.total_records ?? analytics?.analytics?.activity_stats?.jobs_created ?? 0;
  const derivedAvgJobDuration = analytics?.analytics?.transcription_stats?.average_job_duration ?? (userMinutes && userMinutes.total_records > 0 ? (userMinutes.total_minutes / userMinutes.total_records) : 0);
  const derivedJobsCreated = analytics?.analytics?.activity_stats?.jobs_created ?? derivedTotalJobs;

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
      {/* Scope Controls */}
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Scope:</span>
        {[1, 7, 30, 180].map((d) => (
          <Button key={d} variant={scopeDays === d ? "default" : "outline"} size="sm" onClick={() => setScopeDays(d)}>
            {d === 1 ? '1d' : d === 7 ? '7d' : d === 30 ? '30d' : '6mo'}
          </Button>
        ))}
      </div>
      
      {/* Combined Analytics Overview & Activity Section */}
      {analyticsLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
              <CardContent className="p-6">
                <div className="h-4 w-24 bg-muted rounded mb-2 animate-pulse" />
                <div className="h-8 w-16 bg-muted rounded animate-pulse" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : analyticsError ? (
        <div className="text-center text-red-600 dark:text-red-400 my-4">
          <div className="mb-2 font-semibold">Failed to load analytics data.</div>
          <div className="mb-2">{analyticsError}</div>
          <div className="mb-2 text-xs text-muted-foreground break-all">API: <code>{analyticsApiUrl}</code></div>
          <Button ref={reloadRef} variant="outline" size="sm" onClick={fetchUserAnalyticsData}>
            Reload Analytics
          </Button>
        </div>
      ) : analytics ? (
        <>
          <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg font-semibold">
                User Analytics & Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <UserAnalyticsOverview
                totalJobs={derivedTotalJobs}
                totalMinutes={formatDuration(derivedTotalMinutes)}
                avgJobDuration={formatDuration(derivedAvgJobDuration)}
              />

              <UserAnalyticsSummary
                lastActivity={analytics.analytics.activity_stats?.last_activity ?? null}
                jobsCreated={derivedJobsCreated}
              />
            </CardContent>
          </Card>
        </>
      ) : (
        <div className="text-center text-muted-foreground">No analytics data available for this user.</div>
      )}
      
      {/* Audit Logs Section */}
      {auditLoading ? (
        <div className="text-sm text-muted-foreground">Loading audit logs…</div>
      ) : auditLogs && auditLogs.records && auditLogs.records.length > 0 ? (
        <div className="mt-6">
          <h3 className="text-base font-semibold mb-2">Audit Log</h3>
          <div className="space-y-2">
            {auditLogs.records.slice(0, 50).map((r) => (
              <div key={r.id} className="text-sm p-2 border rounded-md flex items-center justify-between">
                <div>
                  <div className="font-medium">{r.event_type}</div>
                  <div className="text-xs text-muted-foreground">{r.timestamp ? new Date(r.timestamp).toLocaleString() : ''}</div>
                </div>
                {r.resource_type === 'job' && r.resource_id ? (
                  <Link to="/audio-recordings/$id" params={{ id: r.resource_id as string }} className="text-primary underline text-xs">View job</Link>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-sm text-muted-foreground mt-6">No audit records in this period.</div>
      )}
      
      {/* User Capability Management */}
      {user && (
        <div className="space-y-6">
        </div>
      )}
    </div>
  );
}
