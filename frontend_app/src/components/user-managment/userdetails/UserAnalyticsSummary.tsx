interface UserAnalyticsSummaryProps {
  lastActivity: string | null;
  jobsCreated: number;
}

export function UserAnalyticsSummary({ lastActivity, jobsCreated }: UserAnalyticsSummaryProps) {
  return (
    <div className="mt-6 pt-6 border-t border-muted-foreground/10 grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="flex flex-col items-center">
        <span className="text-sm text-muted-foreground mb-1">Last Activity</span>
        <span className="text-lg font-semibold">{lastActivity || 'N/A'}</span>
      </div>
      <div className="flex flex-col items-center">
        <span className="text-sm text-muted-foreground mb-1">Jobs Created</span>
        <span className="text-lg font-semibold">{jobsCreated}</span>
      </div>
    </div>
  );
}
