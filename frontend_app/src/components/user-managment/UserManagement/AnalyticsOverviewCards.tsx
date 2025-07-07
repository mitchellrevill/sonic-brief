import { Card, CardContent } from "@/components/ui/card";
import { TrendingUp, Users } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ActiveUsersDisplay } from "@/components/ActiveUsersDisplay";
import type { SystemAnalytics } from "@/lib/api";

interface AnalyticsOverviewCardsProps {
  analyticsLoading: boolean;
  systemAnalytics: SystemAnalytics | null;
  analyticsData: { activeUsers: number }[];
  analyticsPeriod: 7 | 30 | 180 | 365 | 'total';
}

export function AnalyticsOverviewCards({ analyticsLoading, systemAnalytics, analyticsData, analyticsPeriod }: AnalyticsOverviewCardsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 gap-4">
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 dark:bg-blue-950 rounded-lg">
              <TrendingUp className="h-4 w-4 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Total Minutes ({
                analyticsPeriod === 'total' ? 'All Time' : 
                analyticsPeriod === 365 ? '12mo' :
                analyticsPeriod === 180 ? '6mo' :
                `${analyticsPeriod}d`
              })</p>
              <p className="text-lg font-bold">
                {analyticsLoading ? (
                  <Skeleton className="h-5 w-16" />
                ) : systemAnalytics && systemAnalytics.analytics.overview && typeof systemAnalytics.analytics.overview.total_transcription_minutes === 'number' ? (
                  `${systemAnalytics.analytics.overview.total_transcription_minutes.toFixed(1)}`
                ) : systemAnalytics && systemAnalytics.analytics.overview && systemAnalytics.analytics.overview.total_transcription_minutes ? (
                  `${Number(systemAnalytics.analytics.overview.total_transcription_minutes).toFixed(1)}`
                ) : (
                  "0"
                )}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-50 dark:bg-green-950 rounded-lg">
              <Users className="h-4 w-4 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Peak Active Users</p>
              <p className="text-lg font-bold">
                {analyticsLoading ? (
                  <Skeleton className="h-5 w-8" />
                ) : analyticsData.length > 0 ? (
                  Math.max(...analyticsData.map(day => day.activeUsers))
                ) : (
                  "0"
                )}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <ActiveUsersDisplay />
        </CardContent>
      </Card>
    </div>
  );
}
