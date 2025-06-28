import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Users, BarChart3 } from "lucide-react";
import { Capability, PermissionLevel } from "@/types/permissions";
import { useCapabilityGuard } from "@/hooks/usePermissions";
import { PermissionGuard } from "@/lib/permission";
import { 
  fetchAllUsers, 
  getSystemAnalytics,
  getSystemHealth,
  type User
} from "@/lib/api";
import { UserManagementHeader } from "./components/UserManagementHeader";
import { UserOverviewCards } from "./components/UserOverviewCards";
import { UserManagementList } from "./components/UserManagementList";
import { SystemAnalyticsTab } from "./components/SystemAnalyticsTab";

export function UserManagementDashboard() {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterPermission, setFilterPermission] = useState<"All" | PermissionLevel>("All");
  const [analyticsPeriod, setAnalyticsPeriod] = useState<7 | 30 | 180 | 365 | 'total'>(30);
  
  const guard = useCapabilityGuard();
  const navigate = useNavigate();

  // Fetch users
  const { data: users = [], isLoading: usersLoading, error: usersError } = useQuery({
    queryKey: ['users'],
    queryFn: async (): Promise<User[]> => {
      const backendUsers = await fetchAllUsers();
      // Ensure we have an array
      if (!Array.isArray(backendUsers)) {
        console.error('Expected array of users, got:', backendUsers);
        return [];
      }
      return backendUsers;
    },
    enabled: guard.canViewUsers
  });

  // Fetch system analytics
  const { data: systemAnalytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['systemAnalytics', analyticsPeriod],
    queryFn: () => getSystemAnalytics(analyticsPeriod),
    enabled: guard.canViewAnalytics
  });

  // Fetch system health metrics
  const { data: systemHealth, isLoading: healthLoading } = useQuery({
    queryKey: ['systemHealth'],
    queryFn: getSystemHealth,
    enabled: guard.canViewAnalytics,
    refetchInterval: 30000, // Refresh every 30 seconds
    staleTime: 25000 // Consider data stale after 25 seconds
  });

  // Generate analytics data for chart
  const analyticsData = useMemo(() => {
    if (!systemAnalytics?.analytics?.trends?.daily_activity) {
      return [];
    }
    
    const dailyActivity = systemAnalytics.analytics.trends.daily_activity;
    const dailyActiveUsers = systemAnalytics.analytics.trends.daily_active_users || {};
    
    // Convert daily activity (job counts) to chart data
    // Sort by date to ensure proper chronological order
    const sortedEntries = Object.entries(dailyActivity).sort(([a], [b]) => new Date(a).getTime() - new Date(b).getTime());
    
    const chartData = sortedEntries.map(([date, jobCount]) => {
      return {
        date: new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        totalMinutes: Number(jobCount) || 0, // Show job count instead of estimated minutes
        activeUsers: Number(dailyActiveUsers[date]) || 0,
        totalJobs: Number(jobCount) || 0
      };
    });
    
    return chartData;
  }, [systemAnalytics]);

  // Filter users
  const filteredUsers = useMemo(() => {
    if (!Array.isArray(users)) return [];
    return users.filter(user => {
      const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                          (user.name?.toLowerCase().includes(searchTerm.toLowerCase()) ?? false);
      const matchesPermission = filterPermission === "All" || user.permission === filterPermission;
      return matchesSearch && matchesPermission;
    });
  }, [users, searchTerm, filterPermission]);

  const navigateToUserDetails = (userId: string) => {
    navigate({ to: '/admin/users/$userId', params: { userId } });
  };

  if (usersError) {
    return <div className="p-6 text-red-600">Error loading users: {usersError.message}</div>;
  }

  return (
    <PermissionGuard requiredCapability={Capability.CAN_VIEW_USERS}>
      <div className="p-6 space-y-6">
        <UserManagementHeader />

        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="overview" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Overview
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              System Analytics
            </TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="space-y-6">
            {/* System Overview Cards */}
            <UserOverviewCards
              users={users}
              usersLoading={usersLoading}
              systemAnalytics={systemAnalytics || null}
              analyticsLoading={analyticsLoading}
            />

            {/* User Management List */}
            <UserManagementList
              users={users}
              usersLoading={usersLoading}
              searchTerm={searchTerm}
              setSearchTerm={setSearchTerm}
              filterPermission={filterPermission}
              setFilterPermission={setFilterPermission}
              filteredUsers={filteredUsers}
              onUserClick={navigateToUserDetails}
            />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-6">
            <SystemAnalyticsTab
              analyticsPeriod={analyticsPeriod}
              setAnalyticsPeriod={setAnalyticsPeriod}
              users={users}
              usersLoading={usersLoading}
              systemAnalytics={systemAnalytics || null}
              analyticsLoading={analyticsLoading}
              analyticsData={analyticsData}
              systemHealth={systemHealth}
              healthLoading={healthLoading}
            />
          </TabsContent>
        </Tabs>
      </div>
    </PermissionGuard>
  );
}

// Export both named and default for compatibility
export default UserManagementDashboard;


