import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { 
  Activity, 
  Monitor, 
  Clock, 
  RefreshCw,
  Calendar,
  BarChart3,
  Eye
} from 'lucide-react';
import { getUserSessionSummary, getUserActivityPatterns, type UserSessionSummaryResponse, type UserActivityPatternsResponse } from '@/lib/api';
import { toast } from 'sonner';

interface UserActiveSessionsProps {
  userId: string;
  days: number;
}

export function UserActiveSessions({ userId, days }: UserActiveSessionsProps) {
  const [sessionSummary, setSessionSummary] = useState<UserSessionSummaryResponse | null>(null);
  const [activityPatterns, setActivityPatterns] = useState<UserActivityPatternsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSessionData();
  }, [userId, days]);

  const fetchSessionData = async () => {
    if (!userId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log(`🔍 Fetching session data for userId: "${userId}" (${typeof userId})`);
      
      const [summaryData, patternsData] = await Promise.all([
        getUserSessionSummary(userId, days),
        getUserActivityPatterns(userId, days)
      ]);
      
      console.log('📊 Session summary response:', summaryData);
      console.log('📊 Activity patterns response:', patternsData);
      
      setSessionSummary(summaryData);
      setActivityPatterns(patternsData);
    } catch (error: any) {
      console.error('❌ Failed to fetch session data:', error);
      setError(error.message || 'Failed to load session data');
      toast.error('Failed to load session data');
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (minutes: number) => {
    if (minutes < 60) {
      return `${Math.round(minutes)}m`;
    }
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = Math.round(minutes % 60);
    return `${hours}h ${remainingMinutes}m`;
  };

  const getSessionDurationCategory = (minutes: number) => {
    if (minutes < 5) return { label: 'Quick', color: 'bg-blue-500' };
    if (minutes < 30) return { label: 'Medium', color: 'bg-green-500' };
    return { label: 'Extended', color: 'bg-purple-500' };
  };

  const getPeakHour = () => {
    if (!activityPatterns?.activity_patterns.peak_hours) return null;
    
    const hours = activityPatterns.activity_patterns.peak_hours;
    const peakHour = Object.entries(hours).reduce((max, [hour, count]) => 
      count > max.count ? { hour: parseInt(hour), count } : max, 
      { hour: 0, count: 0 }
    );
    
    return peakHour.count > 0 ? peakHour.hour : null;
  };

  if (loading) {
    return (
      <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Session Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="space-y-2 animate-pulse">
                <div className="h-4 w-24 bg-muted rounded" />
                <div className="h-8 w-16 bg-muted rounded" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Session Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <Activity className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600 dark:text-red-400 mb-2">{error}</p>
            <Button onClick={fetchSessionData} variant="outline" size="sm">
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const peakHour = getPeakHour();

  return (
    <div className="space-y-6">
      {/* Session Overview */}
      <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Session Overview
              <Badge variant="outline" className="ml-2">
                {days} days
              </Badge>
            </CardTitle>
            <Button onClick={fetchSessionData} variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </CardHeader>
        
        <CardContent>
          {sessionSummary ? (
            <div className="space-y-6">
              {/* Debug Info */}
              <div className="p-3 bg-muted/30 rounded-lg border border-dashed">
                <p className="text-xs font-mono text-muted-foreground">
                  Debug: Querying for userId: "{sessionSummary.user_id}" | 
                  Total Sessions: {sessionSummary?.session_summary?.total_sessions ?? 0} | 
                  Duration: {sessionSummary?.session_summary?.total_duration_minutes ?? 0}min
                </p>
              </div>
              
              {sessionSummary?.session_summary?.total_sessions > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                  {/* Total Sessions */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      Total Sessions
                    </div>
                    <div className="text-2xl font-bold">
                      {sessionSummary?.session_summary?.total_sessions ?? 0}
                    </div>
                  </div>

                  {/* Total Duration */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <BarChart3 className="h-4 w-4" />
                      Total Duration
                    </div>
                    <div className="text-2xl font-bold">
                      {formatDuration(sessionSummary?.session_summary?.total_duration_minutes ?? 0)}
                    </div>
                  </div>

                  {/* Average Session */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4" />
                      Avg Session
                    </div>
                    <div className="text-2xl font-bold">
                      {formatDuration(sessionSummary?.session_summary?.average_session_duration ?? 0)}
                    </div>
                  </div>

                  {/* Unique Endpoints */}
                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Eye className="h-4 w-4" />
                      Unique Pages
                    </div>
                    <div className="text-2xl font-bold">
                      {sessionSummary?.session_summary?.unique_endpoints ?? 0}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                  <p className="text-muted-foreground mb-2">No session activity found</p>
                  <p className="text-xs text-muted-foreground">
                    User ID "{sessionSummary.user_id}" returned empty results
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <Activity className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">No session data available</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Browser & Platform Usage */}
      {sessionSummary && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Browser Preferences */}
          <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Monitor className="h-5 w-5" />
                Browser Usage
              </CardTitle>
            </CardHeader>
            <CardContent>
              {(() => {
                const browserUsage = sessionSummary?.session_summary?.browser_usage ?? {};
                if (Object.keys(browserUsage).length === 0) {
                  return <p className="text-center text-muted-foreground py-4">No browser data available</p>;
                }

                return (
                  <div className="space-y-3">
                    {Object.entries(browserUsage)
                      .sort(([,a], [,b]) => b - a)
                      .map(([browser, count]) => {
                        const total = Object.values(browserUsage as Record<string, number>).reduce((sum, c) => sum + c, 0);
                        const percentage = total > 0 ? (Number(count) / total) * 100 : 0;

                        return (
                          <div key={browser} className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium flex items-center gap-2">
                                <Monitor className="h-4 w-4" />
                                {browser}
                              </span>
                              <span className="text-sm text-muted-foreground">
                                {count} ({percentage.toFixed(1)}%)
                              </span>
                            </div>
                            <Progress value={percentage} className="h-2" />
                          </div>
                        );
                      })}
                  </div>
                );
              })()}
            </CardContent>
          </Card>

          {/* Activity Patterns */}
          <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Activity Patterns
              </CardTitle>
            </CardHeader>
            <CardContent>
              {activityPatterns ? (
                <div className="space-y-4">
                  {/* Peak Hour */}
                  {peakHour !== null && (
                    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                      <span className="text-sm font-medium">Peak Activity Hour</span>
                      <Badge variant="secondary">
                        {peakHour}:00 - {peakHour + 1}:00
                      </Badge>
                    </div>
                  )}

                  {/* Session Duration Distribution */}
                  {(() => {
                    const sessionPatterns = activityPatterns?.activity_patterns?.session_patterns ?? {};
                    if (!sessionPatterns || Object.keys(sessionPatterns).length === 0) {
                      return null;
                    }

                    return (
                      <div className="space-y-2">
                        <h4 className="text-sm font-medium">Session Duration Distribution</h4>
                        {Object.entries(sessionPatterns).map(([category, count]) => {
                          const total = Object.values(sessionPatterns as Record<string, number>).reduce((sum, c) => sum + c, 0);
                          const percentage = total > 0 ? (Number(count) / total) * 100 : 0;
                          const { label, color } = getSessionDurationCategory(
                            category === 'short_sessions' ? 2 : 
                            category === 'medium_sessions' ? 15 : 45
                          );
                          
                          return (
                            <div key={category} className="flex items-center gap-2">
                              <div className={`w-3 h-3 rounded-full ${color}`} />
                              <span className="text-sm flex-1">
                                {label} ({category.replace('_sessions', '')})
                              </span>
                              <span className="text-sm text-muted-foreground">
                                {count} ({percentage.toFixed(1)}%)
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}

                  {/* Most Active Day */}
                  {sessionSummary?.session_summary?.most_active_day && (
                    <div className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                      <span className="text-sm font-medium">Most Active Day</span>
                      <Badge variant="outline">
                        {new Date(sessionSummary.session_summary.most_active_day).toLocaleDateString()}
                      </Badge>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-4">No activity pattern data available</p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Daily Activity Chart */}
      {(() => {
        const dailyActivity = sessionSummary?.session_summary?.daily_activity ?? {};
        return Object.keys(dailyActivity).length > 0 ? (
        <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Daily Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(dailyActivity)
                .sort(([a], [b]) => new Date(b).getTime() - new Date(a).getTime())
                .slice(0, 14) // Show last 14 days
                .map(([date, count]) => {
                  const maxCount = Math.max(...Object.values(dailyActivity));
                  const percentage = maxCount > 0 ? (Number(count) / maxCount) * 100 : 0;
                  
                  return (
                    <div key={date} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">
                          {new Date(date).toLocaleDateString(undefined, { 
                            weekday: 'short', 
                            month: 'short', 
                            day: 'numeric' 
                          })}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {count} sessions
                        </span>
                      </div>
                      <Progress value={percentage} className="h-2" />
                    </div>
                  );
                })}
            </div>
          </CardContent>
        </Card>
        ) : null;
      })()}
    </div>
  );
}
