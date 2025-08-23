import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDistanceToNow } from "date-fns";
import { CheckCircle, AlertCircle, Clock } from "lucide-react";
import type { SystemAnalytics } from "@/lib/api";

interface AnalyticsRecordsTableProps {
  systemAnalytics: SystemAnalytics | null;
  analyticsLoading: boolean;
}

export function AnalyticsRecordsTable({ systemAnalytics, analyticsLoading }: AnalyticsRecordsTableProps) {
  if (analyticsLoading) {
    return (
    <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
      <div className="text-center text-muted-foreground py-8">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  const records = systemAnalytics?.analytics?.records || [];

  if (records.length === 0) {
    return (
      <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center text-muted-foreground py-8">No activity records found for this period</div>
        </CardContent>
      </Card>
    );
  }

  // Sort records by timestamp (newest first) and take latest 10
  const sortedRecords = [...records]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, 10);

  // helpers
  const getStatusIcon = (status?: string) => {
    if (status === 'completed' || status === 'succeeded') return <CheckCircle className="h-4 w-4 text-green-500" aria-hidden />;
    if (status === 'failed' || status === 'error') return <AlertCircle className="h-4 w-4 text-red-500" aria-hidden />;
    return <Clock className="h-4 w-4 text-muted-foreground" aria-hidden />;
  };

  return (
    <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
        <p className="text-sm text-muted-foreground">
          Latest {sortedRecords.length} transcription jobs
        </p>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-muted-foreground/10">
          {sortedRecords.map((record: any) => {
            const key = record?.id || record?.job_id || `${record?.timestamp}-${record?.user_id}`;
            const status = record?.status || record?.job_status;
            const typeBadge = (record?.file_extension ? String(record.file_extension).toUpperCase() : (record?.type || 'JOB')) as string;
            const name = record?.file_name || record?.name || key;
            const minutes = typeof record?.audio_duration_minutes === 'number' && !isNaN(record.audio_duration_minutes)
              ? (record.audio_duration_minutes as number)
              : (typeof record?.duration_minutes === 'number' ? record.duration_minutes : 0);
            return (
              <div
                key={key}
                className="flex items-center justify-between py-3 px-1 hover:bg-muted/40 rounded transition-colors focus-within:bg-muted/40"
                tabIndex={0}
                aria-label={`Job ${String(name)}`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  {getStatusIcon(status)}
                  <Badge variant="outline" className="text-xs">{typeBadge}</Badge>
                  <span className="text-sm font-medium truncate max-w-[200px]" title={String(name)}>{String(name)}</span>
                </div>
                <div className="text-right min-w-[120px]">
                  <div className="text-xs text-muted-foreground">
                    {record?.timestamp ? formatDistanceToNow(new Date(record.timestamp), { addSuffix: true }) : ''}
                  </div>
                  <div className="text-sm font-medium">
                    {Math.max(0, Math.round(Number(minutes) * 10) / 10).toFixed(1)} min
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
