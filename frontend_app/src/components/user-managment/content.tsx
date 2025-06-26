import { useEffect, useState } from "react";
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

export function UserManagementTable() {
  const [users, setUsers] = useState<User[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyticsData, setAnalyticsData] = useState<any[]>([]);
  const [systemAnalytics, setSystemAnalytics] = useState<SystemAnalytics | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);
  const [showRegisterDialog, setShowRegisterDialog] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [usersPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterPermission, setFilterPermission] = useState<"All" | "Admin" | "Editor" | "User">("All");

  const indexOfLastUser = currentPage * usersPerPage;
  const indexOfFirstUser = indexOfLastUser - usersPerPage;
  const currentUsers = filteredUsers.slice(indexOfFirstUser, indexOfLastUser);
  const totalPages = Math.ceil(filteredUsers.length / usersPerPage);

  // Generate sample analytics data for fallback
  const generateSampleAnalyticsData = () => {
    const last7Days = [];
    for (let i = 6; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - i);
      last7Days.push({
        date: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        totalMinutes: Math.floor(Math.random() * 1000) + 200,
        activeUsers: Math.floor(Math.random() * 50) + 10
      });
    }
    return last7Days;
  };

  // Transform real analytics data for chart display
  const transformAnalyticsData = (systemAnalytics: SystemAnalytics) => {
    const dailyActiveUsers = systemAnalytics.analytics.trends.daily_active_users || {};
    const dailyActivity = systemAnalytics.analytics.trends.daily_activity || {};
    const transformedData = [];
    const totalMinutes = systemAnalytics.analytics.overview.total_transcription_minutes || 0;
    const today = new Date();
    for (let i = 6; i >= 0; i--) {
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
      setUsers(mappedUsers);
      setFilteredUsers(mappedUsers);
    } catch (err) {
      console.error(err);
      toast.error("Failed to fetch users");
    } finally {
      setLoading(false);
    }
  };

  const fetchAnalyticsData = async () => {
    setAnalyticsLoading(true);
    try {
      const systemAnalyticsData = await getSystemAnalytics(7);
      setSystemAnalytics(systemAnalyticsData);
      const transformedData = transformAnalyticsData(systemAnalyticsData);
      setAnalyticsData(transformedData);
    } catch (err) {
      const sampleData = generateSampleAnalyticsData();
      setAnalyticsData(sampleData);
      setSystemAnalytics(null);
      toast.error("Failed to load analytics data, showing sample data");
    } finally {
      setAnalyticsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllUsersApi();
    fetchAnalyticsData();
  }, []);

  useEffect(() => {
    let filtered = users;
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
    setFilteredUsers(filtered);
    setCurrentPage(1);
  }, [users, searchTerm, filterPermission]);

  const handleUserRowClick = (userId: string) => {
    window.location.href = `/admin/users/${userId}`;
  };

  const handleRegisterSuccess = async () => {
    await fetchAllUsersApi();
  };

  if (loading && users.length === 0) {
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
      <AnalyticsOverviewCards analyticsLoading={analyticsLoading} systemAnalytics={systemAnalytics} analyticsData={analyticsData} />
      <AnalyticsChart analyticsLoading={analyticsLoading} analyticsData={analyticsData} />
      <Card>
        <CardContent className="pt-6">
          <SearchFilterControls 
            searchTerm={searchTerm} 
            setSearchTerm={setSearchTerm} 
            filterPermission={filterPermission} 
            setFilterPermission={setFilterPermission} 
          />
        </CardContent>
      </Card>
      <UserCardList users={currentUsers} onUserClick={handleUserRowClick} />
      {totalPages > 1 && (
        <Card className="block lg:hidden">
          <CardContent className="p-4">
            <PaginationControls
              indexOfFirstUser={indexOfFirstUser}
              indexOfLastUser={indexOfLastUser}
              filteredUsersLength={filteredUsers.length}
              currentPage={currentPage}
              totalPages={totalPages}
              setCurrentPage={setCurrentPage}
            />
          </CardContent>
        </Card>
      )}
      <UserTable users={currentUsers} onUserClick={handleUserRowClick} totalUsers={filteredUsers.length} />
      {totalPages > 1 && (
        <div className="hidden lg:block">
          <div className="p-4 border-t">
            <PaginationControls
              indexOfFirstUser={indexOfFirstUser}
              indexOfLastUser={indexOfLastUser}
              filteredUsersLength={filteredUsers.length}
              currentPage={currentPage}
              totalPages={totalPages}
              setCurrentPage={setCurrentPage}
            />
          </div>
        </div>
      )}
    </div>
  );
}