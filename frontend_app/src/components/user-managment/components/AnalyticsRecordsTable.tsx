import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";
import type { SystemAnalytics } from "@/lib/api";

interface AnalyticsRecordsTableProps {
  systemAnalytics: SystemAnalytics | null;
  analyticsLoading: boolean;
}

export function AnalyticsRecordsTable({ systemAnalytics, analyticsLoading }: AnalyticsRecordsTableProps) {
  if (analyticsLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  const records = systemAnalytics?.analytics?.records || [];

  if (records.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground">No activity records found for this period</div>
        </CardContent>
      </Card>
    );
  }

  // Sort records by timestamp (newest first) and take latest 10
  const sortedRecords = [...records]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <p className="text-sm text-muted-foreground">
          Latest {sortedRecords.length} transcription jobs
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {sortedRecords.map((record) => (
            <div key={record.id} className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="outline" className="text-xs">
                    {record.file_extension.toUpperCase()}
                  </Badge>
                  <span className="text-sm font-medium truncate">{record.file_name}</span>
                </div>
                <div className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(record.timestamp), { addSuffix: true })}
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm font-medium">
                  {record.audio_duration_minutes.toFixed(1)} min
                </div>
                <div className="text-xs text-muted-foreground">
                  {record.audio_duration_seconds.toFixed(0)}s
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
