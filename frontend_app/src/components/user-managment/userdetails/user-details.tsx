import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { 
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from "recharts";
import { 
  ArrowLeft,
  User as UserIcon,
  Mail,
  Calendar,
  Shield,
  ShieldCheck,
  Activity,
  Clock,
  FileText,
  TrendingUp,
  Download,
  Edit,
  Key,
  Trash2,
  AlertTriangle
} from "lucide-react";
import { 
  fetchUserById, 
  getUserAnalytics, 
  exportUserDetailsPDF, 
  updateUserPermission, 
  changeUserPassword, 
  deleteUser,
  type UserAnalytics 
} from "@/lib/api";
import type { User } from "@/lib/api";
import { toast } from "sonner";

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
  const [newPermission, setNewPermission] = useState<"User" | "Admin" | "Editor">("User");
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
    return (
      <div className="container mx-auto py-6 space-y-6">
        <div className="flex items-center gap-4">
          <Skeleton className="h-10 w-10 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-8 w-[300px]" />
            <Skeleton className="h-4 w-[200px]" />
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i}>
              <CardContent className="p-6">
                <Skeleton className="h-4 w-[100px] mb-2" />
                <Skeleton className="h-8 w-[60px]" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="container mx-auto py-6">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <UserIcon className="h-12 w-12 text-muted-foreground mb-4" />
            <h2 className="text-xl font-semibold mb-2">User Not Found</h2>
            <p className="text-muted-foreground mb-4">The requested user could not be found.</p>
            <Button onClick={() => {
              window.location.href = '/admin/users';
            }}>
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to User Management
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const permissionInfo = getPermissionInfo(user.permission);
  const PermissionIcon = permissionInfo.icon;

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              window.location.href = '/admin/user-management';
            }}
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Users
          </Button>
          <div className="flex items-center gap-4">
            <Avatar className="h-12 w-12">
              <AvatarFallback className="bg-primary/10 text-primary font-semibold text-lg">
                {getUserInitials(user.email, user.name)}
              </AvatarFallback>
            </Avatar>
            <div>
              <h1 className="text-2xl font-bold">{user.name || user.email}</h1>
              <p className="text-muted-foreground">User Details & Analytics</p>
            </div>
          </div>
        </div>
        <Button
          onClick={handleExportPDF}
          disabled={exportLoading}
          variant="outline"
        >
          {exportLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary mr-2"></div>
              Exporting...
            </>
          ) : (
            <>
              <Download className="mr-2 h-4 w-4" />
              Export PDF
            </>
          )}
        </Button>
      </div>

      {/* User Information */}
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
          {user.date && (
            <div className="flex items-center gap-4">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="font-medium">Created:</span>
              <span>{user.date}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Analytics Cards */}
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Jobs</p>
                <p className="text-2xl font-bold">{analytics.analytics.transcription_stats.total_jobs}</p>
              </div>
              <FileText className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Minutes</p>
                <p className="text-2xl font-bold">{formatDuration(analytics.analytics.transcription_stats.total_minutes)}</p>
              </div>
              <Clock className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Average Job Duration</p>
                <p className="text-2xl font-bold">{formatDuration(analytics.analytics.transcription_stats.average_job_duration)}</p>
              </div>
              <Clock className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Login Count</p>
                <p className="text-2xl font-bold">{analytics.analytics.activity_stats.login_count}</p>
              </div>
              <Activity className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Activity className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Analytics Available</h3>
            <p className="text-muted-foreground">Analytics data is not available for this user.</p>
          </CardContent>
        </Card>      )}

      {/* Activity Summary */}
      {analytics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Activity Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Login Count</p>
                <p className="text-xl font-semibold">{analytics.analytics.activity_stats.login_count}</p>
              </div>
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">Jobs Created</p>
                <p className="text-xl font-semibold">{analytics.analytics.activity_stats.jobs_created}</p>
              </div>
              {analytics.analytics.activity_stats.last_activity && (
                <div className="space-y-2 md:col-span-2">
                  <p className="text-sm text-muted-foreground">Last Activity</p>
                  <p className="text-xl font-semibold">{analytics.analytics.activity_stats.last_activity}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

     

      {/* Usage Activity Graph */}
      {analytics && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Usage Activity Over Time
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Activity Timeline Chart */}
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-muted-foreground">Activity Distribution</h4>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart
                    data={[
                      { name: 'Jobs Created', value: analytics.analytics.activity_stats.jobs_created || 0, fill: '#4caf50' },
                      { name: 'Logins', value: analytics.analytics.activity_stats.login_count || 0, fill: '#2196f3' },
                      { name: 'File Uploads', value: analytics.analytics.usage_patterns.file_upload_count || 0, fill: '#ff9800' },
                      { name: 'Text Inputs', value: analytics.analytics.usage_patterns.text_input_count || 0, fill: '#9c27b0' }
                    ]}
                    margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="value" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Usage Summary Pie Chart */}
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-muted-foreground">Usage Breakdown</h4>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={[
                        { 
                          name: 'File Uploads', 
                          value: analytics.analytics.usage_patterns.file_upload_count || 0,
                          fill: '#ff9800'
                        },
                        { 
                          name: 'Text Inputs', 
                          value: analytics.analytics.usage_patterns.text_input_count || 0,
                          fill: '#9c27b0'
                        }
                      ].filter(item => item.value > 0)}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name}: ${((percent || 0) * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {[
                        { name: 'File Uploads', value: analytics.analytics.usage_patterns.file_upload_count || 0, fill: '#ff9800' },
                        { name: 'Text Inputs', value: analytics.analytics.usage_patterns.text_input_count || 0, fill: '#9c27b0' }
                      ].filter(item => item.value > 0).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Additional Metrics Summary */}
            <div className="mt-6 pt-6 border-t">
              <h4 className="text-lg font-semibold mb-4">Summary Metrics</h4>
              
              {/* Plain text totals as requested */}
              <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-center">
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Total Transcription Time (All Time)</div>
                    <div className="text-2xl font-bold text-green-600">{formatDuration(analytics.analytics.transcription_stats.total_minutes)}</div>
                    <div className="text-xs text-muted-foreground">({Math.floor(analytics.analytics.transcription_stats.total_minutes)} minutes)</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Total Transcription Time (Past 30 Days)</div>
                    <div className="text-2xl font-bold text-blue-600">{formatDuration(analytics.analytics.transcription_stats.total_minutes)}</div>
                    <div className="text-xs text-muted-foreground">({Math.floor(analytics.analytics.transcription_stats.total_minutes)} minutes)</div>
                  </div>
                </div>
              </div>

              {/* Detailed metrics grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{analytics.analytics.transcription_stats.total_jobs}</div>
                  <div className="text-sm text-muted-foreground">Total Jobs</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{formatDuration(analytics.analytics.transcription_stats.total_minutes)}</div>
                  <div className="text-sm text-muted-foreground">Total Minutes</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">{analytics.analytics.activity_stats.login_count}</div>
                  <div className="text-sm text-muted-foreground">Login Sessions</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
