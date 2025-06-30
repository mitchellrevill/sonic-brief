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

  // Generate analytics data for chart with complete date range
  const analyticsData = useMemo(() => {
    // Generate complete date range for the selected period
    const generateDateRange = (days: number | 'total'): string[] => {
      if (days === 'total') days = 30; // Default to 30 days for 'total'
      
      const dates: string[] = [];
      const today = new Date();
      
      for (let i = days - 1; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(today.getDate() - i);
        dates.push(date.toISOString().split('T')[0]); // YYYY-MM-DD format
      }
      
      return dates;
    };

    // Helper to format date for chart
    const formatDate = (dateStr: string, period: number | string) => {
      const date = new Date(dateStr);
      if (period === 7) return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      if (period === 30) return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      if (period === 180 || period === 365) return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    };

    // Get data from system analytics or use empty defaults
    const dailyActivity = systemAnalytics?.analytics?.trends?.daily_activity || {};
    const dailyMinutes = systemAnalytics?.analytics?.trends?.daily_transcription_minutes || {};
    const dailyActiveUsers = systemAnalytics?.analytics?.trends?.daily_active_users || {};

    // Generate complete date range for the period
    const allDates = generateDateRange(analyticsPeriod);

    // Grouping logic with complete date ranges
    let chartData: any[] = [];
    if (analyticsPeriod === 7) {
      // Show each day for last 7 days - all 7 days
      chartData = allDates.map(date => ({
        date: formatDate(date, 7),
        totalJobs: Number(dailyActivity[date]) || 0,
        totalMinutes: Number(dailyMinutes[date]) || 0,
        activeUsers: Number(dailyActiveUsers[date]) || 0
      }));
    } else if (analyticsPeriod === 30) {
      // Group every 6 days for last 30 days (5 groups of 6 days each)
      const groups = [];
      for (let i = 0; i < allDates.length; i += 6) {
        const group = allDates.slice(i, i + 6);
        if (group.length) {
          const jobs = group.reduce((sum, d) => sum + (Number(dailyActivity[d]) || 0), 0);
          const minutes = group.reduce((sum, d) => sum + (Number(dailyMinutes[d]) || 0), 0);
          const users = group.reduce((sum, d) => sum + (Number(dailyActiveUsers[d]) || 0), 0);
          groups.push({
            date: formatDate(group[0], 30) + (group.length > 1 ? ' - ' + formatDate(group[group.length - 1], 30) : ''),
            totalJobs: jobs,
            totalMinutes: minutes,
            activeUsers: users
          });
        }
      }
      chartData = groups;
    } else if (analyticsPeriod === 180 || analyticsPeriod === 365) {
      // Group by month for 6 months or 12 months
      const months: Record<string, { jobs: number; minutes: number; users: number }> = {};
      
      // Generate complete months for the period
      const monthsCount = analyticsPeriod === 180 ? 6 : 12;
      const today = new Date();
      
      for (let i = monthsCount - 1; i >= 0; i--) {
        const date = new Date(today.getFullYear(), today.getMonth() - i, 1);
        const key = date.getFullYear() + '-' + (date.getMonth() + 1);
        months[key] = { jobs: 0, minutes: 0, users: 0 };
      }
      
      // Add actual data to months
      allDates.forEach(date => {
        const d = new Date(date);
        const key = d.getFullYear() + '-' + (d.getMonth() + 1);
        if (months[key]) {
          months[key].jobs += Number(dailyActivity[date]) || 0;
          months[key].minutes += Number(dailyMinutes[date]) || 0;
          months[key].users += Number(dailyActiveUsers[date]) || 0;
        }
      });
      
      chartData = Object.entries(months).map(([key, val]) => {
        const [year, month] = key.split('-');
        const date = new Date(Number(year), Number(month) - 1, 1);
        return {
          date: formatDate(date.toISOString().split('T')[0], analyticsPeriod),
          totalJobs: val.jobs,
          totalMinutes: val.minutes,
          activeUsers: val.users
        };
      });
    } else {
      // Default: show all days in period
      chartData = allDates.map(date => ({
        date: formatDate(date, analyticsPeriod),
        totalJobs: Number(dailyActivity[date]) || 0,
        totalMinutes: Number(dailyMinutes[date]) || 0,
        activeUsers: Number(dailyActiveUsers[date]) || 0
      }));
    }
    return chartData;
  }, [systemAnalytics, analyticsPeriod]);

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


