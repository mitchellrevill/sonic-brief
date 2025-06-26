import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import { ResponsiveContainer, LineChart, CartesianGrid, XAxis, YAxis, Tooltip, Line } from "recharts";

interface AnalyticsChartProps {
  analyticsLoading: boolean;
  analyticsData: { date: string; totalMinutes: number; activeUsers: number }[];
}

export function AnalyticsChart({ analyticsLoading, analyticsData }: AnalyticsChartProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          System Usage Analytics
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Daily transcription activity and user engagement over the last 7 days
        </p>
      </CardHeader>
      <CardContent>
        {analyticsLoading ? (
          <div className="h-[300px] flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={analyticsData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip 
                formatter={(value, name) => {
                  if (name === 'totalMinutes') return [`${value} min`, 'Daily Minutes'];
                  if (name === 'activeUsers') return [`${value} users`, 'Active Users'];
                  return [value, name];
                }}
              />
              <Line 
                type="monotone" 
                dataKey="totalMinutes" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={{ fill: '#3b82f6' }}
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
