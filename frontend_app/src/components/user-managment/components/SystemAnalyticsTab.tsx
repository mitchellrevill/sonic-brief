import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Users, TrendingUp, BarChart3, AlertTriangle } from "lucide-react";
import { AnalyticsChart } from "../UserManagement/AnalyticsChart";
import { AnalyticsOverviewCards } from "../UserManagement/AnalyticsOverviewCards";
// System health metrics removed per request
import { UserDistributionCard } from "./UserDistributionCard";
import { AnalyticsRecordsTable } from "./AnalyticsRecordsTable";
import { EXPORT_SYSTEM_CSV_API } from "@/lib/apiConstants";
import type { User, SystemAnalytics } from "@/lib/api";

interface SystemAnalyticsTabProps {
  analyticsPeriod: 7 | 30 | 180 | 365 | 'total';
  setAnalyticsPeriod: (period: 7 | 30 | 180 | 365 | 'total') => void;
  users: User[];
  usersLoading: boolean;
  systemAnalytics: SystemAnalytics | null;
  analyticsLoading: boolean;
  analyticsData: { date: string; totalMinutes: number; activeUsers: number }[];
}

export function SystemAnalyticsTab({
  analyticsPeriod,
  setAnalyticsPeriod,
  users,
  usersLoading,
  systemAnalytics,
  analyticsLoading,
  analyticsData,
}: SystemAnalyticsTabProps) {
  // Check if data is mock data
  const isMockData = systemAnalytics?.analytics?._is_mock_data === true;
  
  return (
    <div className="space-y-6">
      {isMockData && (
        <Alert>
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            <strong>Demo Data:</strong> The analytics shown are sample data because no real analytics events or job data were found. 
            {systemAnalytics?.analytics?._mock_reason && ` Reason: ${systemAnalytics.analytics._mock_reason}`}
          </AlertDescription>
        </Alert>
      )}
      
      {/* Show summary of actual data when available */}
      {systemAnalytics?.analytics?.records && systemAnalytics.analytics.records.length > 0 && (
        <Alert>
          <BarChart3 className="h-4 w-4" />
          <AlertDescription>
            <strong>Live Data:</strong> Showing real analytics from {systemAnalytics.analytics.records.length} activity records 
            from {systemAnalytics.start_date.split('T')[0]} to {systemAnalytics.end_date.split('T')[0]}.
          </AlertDescription>
        </Alert>
      )}
      
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold">System Analytics</h2>
          <p className="text-muted-foreground">
            Comprehensive overview of system usage and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select 
            value={analyticsPeriod.toString()} 
            onValueChange={(value) => setAnalyticsPeriod(value === 'total' ? 'total' : parseInt(value) as 7 | 30 | 180 | 365)}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7 days</SelectItem>
              <SelectItem value="30">30 days</SelectItem>
              <SelectItem value="180">6 months</SelectItem>
              <SelectItem value="365">12 months</SelectItem>
              <SelectItem value="total">All time</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              const period = analyticsPeriod === 'total' ? 30 : analyticsPeriod;
              const resp = await fetch(`${EXPORT_SYSTEM_CSV_API}?days=${period}`, {
                headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` },
              });
              if (!resp.ok) {
                console.error('Failed to export system analytics CSV');
                return;
              }
              const blob = await resp.blob();
              const url = URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `system_analytics_${period}d.csv`;
              document.body.appendChild(a);
              a.click();
              setTimeout(() => {
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
              }, 0);
            }}
          >
            Export CSV
          </Button>
        </div>
      </div>

      {/* Enhanced Analytics Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Users</p>
                <p className="text-2xl font-bold">
                  {usersLoading ? "..." : users.length}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  +{users.filter(u => u.date && analyticsPeriod !== 'total' && new Date(u.date) > new Date(Date.now() - (analyticsPeriod as number) * 24 * 60 * 60 * 1000)).length} this period
                </p>
              </div>
              <Users className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Users</p>
                <p className="text-2xl font-bold">
                  {analyticsLoading ? "..." : systemAnalytics?.analytics?.overview?.active_users || "0"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Last {
                    analyticsPeriod === 'total' ? 'All Time' : 
                    analyticsPeriod === 365 ? '12 months' :
                    analyticsPeriod === 180 ? '6 months' :
                    `${analyticsPeriod} days`
                  }
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Jobs</p>
                <p className="text-2xl font-bold">
                  {analyticsLoading ? "..." : systemAnalytics?.analytics?.overview?.total_jobs || "0"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Transcription jobs
                </p>
              </div>
              <BarChart3 className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Minutes</p>
                <p className="text-2xl font-bold">
                  {analyticsLoading ? "..." : Math.round(systemAnalytics?.analytics?.overview?.total_transcription_minutes || 0)}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Audio processed
                </p>
              </div>
              <TrendingUp className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Analytics Charts and Detailed Info */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <AnalyticsChart
            analyticsLoading={analyticsLoading}
            analyticsData={analyticsData}
            analyticsPeriod={analyticsPeriod}
          />
        </div>
        <div>
          <AnalyticsOverviewCards
            analyticsLoading={analyticsLoading}
            systemAnalytics={systemAnalytics || null}
            analyticsData={analyticsData}
            analyticsPeriod={analyticsPeriod}
          />
        </div>
      </div>

      {/* System Health metric removed */}

      {/* User Distribution and Activity Records */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <UserDistributionCard users={users} />
        <AnalyticsRecordsTable 
          systemAnalytics={systemAnalytics} 
          analyticsLoading={analyticsLoading} 
        />
      </div>
    </div>
  );
}
