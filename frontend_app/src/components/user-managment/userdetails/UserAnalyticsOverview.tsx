import { Card } from "@/components/ui/card";
import { FileText, Clock, Activity } from "lucide-react";

interface UserAnalyticsOverviewProps {
  totalJobs: number;
  totalMinutes: string;
  avgJobDuration: string;
  loginCount: number;
}

export function UserAnalyticsOverview({ totalJobs, totalMinutes, avgJobDuration, loginCount }: UserAnalyticsOverviewProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      <Card className="shadow-none border border-muted-foreground/10">
        <div className="p-4 flex items-center gap-3">
          <div className="p-2 bg-blue-50 dark:bg-blue-950 rounded-lg">
            <FileText className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Total Jobs</p>
            <p className="text-lg font-bold">{totalJobs}</p>
          </div>
        </div>
      </Card>
      <Card className="shadow-none border border-muted-foreground/10">
        <div className="p-4 flex items-center gap-3">
          <div className="p-2 bg-green-50 dark:bg-green-950 rounded-lg">
            <Clock className="h-5 w-5 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Total Minutes</p>
            <p className="text-lg font-bold">{totalMinutes}</p>
          </div>
        </div>
      </Card>
      <Card className="shadow-none border border-muted-foreground/10">
        <div className="p-4 flex items-center gap-3">
          <div className="p-2 bg-purple-50 dark:bg-purple-950 rounded-lg">
            <Clock className="h-5 w-5 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Avg. Job Duration</p>
            <p className="text-lg font-bold">{avgJobDuration}</p>
          </div>
        </div>
      </Card>
      <Card className="shadow-none border border-muted-foreground/10">
        <div className="p-4 flex items-center gap-3">
          <div className="p-2 bg-orange-50 dark:bg-orange-950 rounded-lg">
            <Activity className="h-5 w-5 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground mb-1">Login Count</p>
            <p className="text-lg font-bold">{loginCount}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
