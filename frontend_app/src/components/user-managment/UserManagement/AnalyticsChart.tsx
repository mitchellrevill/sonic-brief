import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import { ResponsiveContainer, LineChart, CartesianGrid, XAxis, YAxis, Tooltip, Line } from "recharts";

interface AnalyticsChartProps {
  analyticsLoading: boolean;
  analyticsData: { 
    date: string; 
    totalMinutes: number; 
    activeUsers: number;
    totalJobs?: number; 
  }[];
  analyticsPeriod: 7 | 30 | 180 | 365 | 'total';
}

export function AnalyticsChart({ analyticsLoading, analyticsData, analyticsPeriod }: AnalyticsChartProps) {
  return (
  <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          System Usage Analytics
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Daily transcription activity and user engagement over the {
            analyticsPeriod === 'total' ? 'entire system history' : 
            analyticsPeriod === 365 ? 'last 12 months' :
            analyticsPeriod === 180 ? 'last 6 months' :
            `last ${analyticsPeriod} days`
          }. Shows daily job counts and active users.
        </p>
      </CardHeader>
      <CardContent>
        {analyticsLoading ? (
          <div className="h-[300px] flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : analyticsData.length === 0 ? (
          <div className="h-[300px] flex items-center justify-center text-muted-foreground">No data in selected period</div>
        ) : (
          <ResponsiveContainer width="100%" height={300} aria-label="System usage analytics chart">
            <LineChart data={analyticsData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                fontSize={12}
                tick={{ fontSize: 12 }}
                interval={analyticsPeriod === 7 ? 0 : 'preserveStartEnd'}
              />
              <YAxis fontSize={12} />
              <Tooltip 
                formatter={(value, name) => {
                  if (name === 'totalMinutes') return [`${value} min`, 'Transcription Minutes'];
                  if (name === 'activeUsers') return [`${value} users`, 'Active Users'];
                  if (name === 'totalJobs') return [`${value} jobs`, 'Daily Jobs'];
                  return [value, name];
                }}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="totalJobs" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={{ fill: '#3b82f6' }}
                name="totalJobs"
              />
              <Line 
                type="monotone" 
                dataKey="totalMinutes" 
                stroke="#6366f1" 
                strokeWidth={2}
                dot={{ fill: '#6366f1' }}
                name="totalMinutes"
              />
              <Line 
                type="monotone" 
                dataKey="activeUsers" 
                stroke="#10b981" 
                strokeWidth={2}
                dot={{ fill: '#10b981' }}
                name="activeUsers"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
