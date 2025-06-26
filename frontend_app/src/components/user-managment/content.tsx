import { useEffect, useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchAllUsers, getSystemAnalytics } from "@/lib/api";
import type { User, SystemAnalytics } from "@/lib/api";
import { toast } from "sonner";
import { RegisterUserDialog } from "./UserManagement/RegisterUserDialog";
import { ExportCSVButton } from "./UserManagement/ExportCSVButton";
import { AnalyticsOverviewCards } from "./UserManagement/AnalyticsOverviewCards";
import { AnalyticsChart } from "./UserManagement/AnalyticsChart";
import { SearchFilterControls } from "./UserManagement/SearchFilterControls";
import { PaginationControls } from "./UserManagement/PaginationControls";
import { UserCardList } from "./UserManagement/UserCardList";
import { UserTable } from "./UserManagement/UserTable";
import { Button } from "@/components/ui/button";

export function UserManagementTable() {
  // --- State ---
  const [searchTerm, setSearchTerm] = useState("");
  const [filterPermission, setFilterPermission] = useState<"All" | "Admin" | "Editor" | "User">("All");
  const [currentPage, setCurrentPage] = useState(1);
  const [usersPerPage] = useState(10);
  const [showRegisterDialog, setShowRegisterDialog] = useState(false);
  const [analyticsPeriod, setAnalyticsPeriod] = useState<7 | 30>(30);

  // --- React Query for Users ---
  const {
    data: usersData,
    isLoading: usersLoading,
    isError: usersError,
    refetch: refetchUsers,
  } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const response: User[] | { users: User[] } = await fetchAllUsers();
      let apiUsers: User[];
      if (Array.isArray(response)) {
        apiUsers = response;
      } else if (response && typeof response === "object" && "users" in response && Array.isArray((response as any).users)) {
        apiUsers = (response as { users: User[] }).users;
      } else {
        apiUsers = [];
      }
      return apiUsers.map((u: any, idx: number) => {
        let dateStr = "";
        if (u._ts) {
          const d = new Date(u._ts * 1000);
          const day = String(d.getDate()).padStart(2, "0");
          const month = String(d.getMonth() + 1).padStart(2, "0");
          const year = d.getFullYear();
          const time = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
          dateStr = `${day}/${month}/${year} ${time}`;
        }
        let permission: "Admin" | "Editor" | "User" =
          u.permission === "Admin" ? "Admin" :
          u.permission === "Editor" ? "Editor" :
          "User";
        return {
          id: u.id || idx,
          name: u.name || u.email || "",
          email: u.email,
          permission: permission as "Admin" | "Editor" | "User",
          date: dateStr,
        };
      });
    },
    staleTime: 60000, // 1 minute
  });

  // --- React Query for Analytics ---
  const {
    data: analyticsRawData,
    isLoading: analyticsLoading,
    isError: analyticsError,
  } = useQuery({
    queryKey: ["systemAnalytics", analyticsPeriod],
    queryFn: async () => {
      try {
        const systemAnalyticsData = await getSystemAnalytics(analyticsPeriod);
        return systemAnalyticsData;
      } catch (err) {
        throw err;
      }
    },
    staleTime: 60000, // 1 minute
  });

  // --- Analytics Data Transformation ---
  let analyticsData: any[] = [];
  let systemAnalytics: SystemAnalytics | null = null;
  const generateSampleAnalyticsData = () => {
    const days = analyticsPeriod;
    const lastNDays = [];
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      lastNDays.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        totalMinutes: Math.floor(Math.random() * 1000) + 200,
        activeUsers: Math.floor(Math.random() * 50) + 10
      });
    }
    return lastNDays;
  };
  const transformAnalyticsData = (systemAnalytics: SystemAnalytics) => {
    const days = analyticsPeriod;
    const dailyActiveUsers = systemAnalytics.analytics.trends.daily_active_users || {};
    const dailyActivity = systemAnalytics.analytics.trends.daily_activity || {};
    const transformedData = [];
    const totalMinutes = systemAnalytics.analytics.overview.total_transcription_minutes || 0;
    const today = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(today.getDate() - i);
      const dateKey = date.toISOString().split('T')[0];
      const displayDate = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      const activeUsersCount = dailyActiveUsers[dateKey] || 0;
      const dailyActivityCount = dailyActivity[dateKey] || 0;
      let dailyMinutes = 0;
      if (dailyActivityCount > 0 && totalMinutes > 0) {
        const totalActivity = Object.values(dailyActivity).reduce((sum, count) => sum + count, 0);
        dailyMinutes = totalActivity > 0 ? (dailyActivityCount / totalActivity) * totalMinutes : 0;
      } else if (totalMinutes > 0) {
        dailyMinutes = totalMinutes / systemAnalytics.period_days;
      }
      transformedData.push({
        date: displayDate,
        totalMinutes: Math.round(dailyMinutes * 10) / 10,
        activeUsers: activeUsersCount
      });
    }
    return transformedData;
  };
  if (analyticsRawData && typeof analyticsRawData === "object" && "analytics" in analyticsRawData) {
    try {
      analyticsData = transformAnalyticsData(analyticsRawData as SystemAnalytics);
      systemAnalytics = analyticsRawData as SystemAnalytics;
    } catch {
      analyticsData = generateSampleAnalyticsData();
      systemAnalytics = null;
    }
  } else if (analyticsError) {
    analyticsData = generateSampleAnalyticsData();
    systemAnalytics = null;
  }

  // --- Derived State ---
  const users: User[] = Array.isArray(usersData) ? usersData : [];
  const filteredUsers: User[] = useMemo(() => {
    let filtered = Array.isArray(users) ? users : [];
    if (searchTerm) {
      filtered = filtered.filter(user =>
        user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (user.name && user.name.toLowerCase().includes(searchTerm.toLowerCase())) ||
        user.id.toString().includes(searchTerm)
      );
    }
    if (filterPermission !== "All") {
      filtered = filtered.filter(user => user.permission === filterPermission);
    }
    return filtered;
  }, [users, searchTerm, filterPermission]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm, filterPermission]);

  const indexOfLastUser = currentPage * usersPerPage;
  const indexOfFirstUser = indexOfLastUser - usersPerPage;
  const currentUsers = filteredUsers.slice(indexOfFirstUser, indexOfLastUser);
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage);

  // --- Error Toasts ---
  useEffect(() => {
    if (usersError) toast.error("Failed to fetch users");
  }, [usersError]);
  useEffect(() => {
    if (analyticsError) toast.error("Failed to load analytics data, showing sample data");
  }, [analyticsError]);

  const handleUserRowClick = (userId: string) => {
    window.location.href = `/admin/users/${userId}`;
  };

  const handleRegisterSuccess = async () => {
    await refetchUsers();
  };

  if (usersLoading && users.length === 0) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            User Management
          </CardTitle>
        </CardHeader>
        <CardContent>
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
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-2xl font-bold">User Management</h1>
        <div className="flex items-center gap-2">
          <RegisterUserDialog open={showRegisterDialog} setOpen={setShowRegisterDialog} onRegisterSuccess={handleRegisterSuccess} />
          <ExportCSVButton />
        </div>
      </div>
      {/* Toggle for analytics period */}
      <div className="flex gap-2 items-center mb-2">
        <span className="text-sm font-medium">Analytics Period:</span>
        <Button
          variant={analyticsPeriod === 7 ? "default" : "outline"}
          size="sm"
          onClick={() => setAnalyticsPeriod(7)}
        >
          7 days
        </Button>
        <Button
          variant={analyticsPeriod === 30 ? "default" : "outline"}
          size="sm"
          onClick={() => setAnalyticsPeriod(30)}
        >
          30 days
        </Button>
      </div>
      {/* Chart and Overview Cards side by side */}
      <div className="flex flex-col lg:flex-row gap-4">
        <div className="flex-1 min-w-0">
          <AnalyticsChart analyticsLoading={analyticsLoading} analyticsData={analyticsData} analyticsPeriod={analyticsPeriod} />
        </div>
        <div className="w-full lg:w-[350px] flex-shrink-0">
          <AnalyticsOverviewCards analyticsLoading={analyticsLoading} systemAnalytics={systemAnalytics} analyticsData={analyticsData} analyticsPeriod={analyticsPeriod} />
        </div>
      </div>
      {/* Consolidated User Table and Filter/Search */}
      <div className="bg-card rounded-xl shadow-sm">
        <div className="pt-6 px-6">
          <div className="mb-4">
            <SearchFilterControls 
              searchTerm={searchTerm} 
              setSearchTerm={setSearchTerm} 
              filterPermission={filterPermission} 
              setFilterPermission={setFilterPermission} 
            />
          </div>
          <div className="border-t border-muted-foreground/10 mb-4" />
          <UserTable users={currentUsers} onUserClick={handleUserRowClick} totalUsers={filteredUsers.length} />
          {totalPages > 1 && (
            <div className="pt-4">
              <PaginationControls
                indexOfFirstUser={indexOfFirstUser}
                indexOfLastUser={indexOfLastUser}
                filteredUsersLength={filteredUsers.length}
                currentPage={currentPage}
                totalPages={totalPages}
                setCurrentPage={setCurrentPage}
              />
            </div>
          )}
        </div>
      </div>
      {/* Optionally keep UserCardList for mobile/alt view */}
      <UserCardList users={currentUsers} onUserClick={handleUserRowClick} />
    </div>
  );
}