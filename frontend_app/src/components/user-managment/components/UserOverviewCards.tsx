import { Card, CardContent } from "@/components/ui/card";
import { Users, TrendingUp, BarChart3 } from "lucide-react";
import type { User, SystemAnalytics } from "@/lib/api";

interface UserOverviewCardsProps {
  users: User[];
  usersLoading: boolean;
  systemAnalytics: SystemAnalytics | null;
  analyticsLoading: boolean;
}

export function UserOverviewCards({ 
  users, 
  usersLoading, 
  systemAnalytics, 
  analyticsLoading 
}: UserOverviewCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Users</p>
              <p className="text-2xl font-bold">
                {usersLoading ? "..." : users.length}
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
                {analyticsLoading ? "..." : (
                  systemAnalytics?.active_users ??
                  systemAnalytics?.analytics?.active_users ??
                  systemAnalytics?.analytics?.overview?.active_users ??
                  "0"
                )}
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
                {analyticsLoading ? "..." : systemAnalytics?.analytics?.total_jobs || systemAnalytics?.analytics?.overview?.total_jobs || "0"}
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
                {analyticsLoading ? "..." : Math.round(systemAnalytics?.analytics?.total_minutes || systemAnalytics?.analytics?.overview?.total_transcription_minutes || 0)}
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
              <p className="text-sm font-medium text-muted-foreground">Peak Active Users</p>
              <p className="text-2xl font-bold">
                {analyticsLoading ? "..." : (
                  systemAnalytics?.peak_active_users ??
                  systemAnalytics?.analytics?.peak_active_users ??
                  systemAnalytics?.analytics?.overview?.peak_active_users ??
                  "0"
                )}
              </p>
            </div>
            <Users className="h-8 w-8 text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
