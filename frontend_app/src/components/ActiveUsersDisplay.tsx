/*
 * ActiveUsersDisplay Component
 * 
 * This component has been updated to use system analytics data instead of the 
 * dedicated active users API endpoint (/api/analytics/active-users) due to 
 * compatibility issues with the current API response structure.
 * 
 * Original implementation expected: response.data.active_users (array)
 * Current implementation uses: systemAnalytics.analytics.overview.active_users (number)
 * 
 * To revert to the original active users API, replace the queryFn with:
 * 
 * queryFn: async () => {
 *   const response = await getActiveUsers(5);
 *   return response?.data?.active_users?.length || 0;
 * }
 */

import { Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getSystemAnalytics } from '@/lib/api';

interface ActiveUsersProps {
  refreshInterval?: number; // in milliseconds
}

export function ActiveUsersDisplay({ refreshInterval = 300000 }: ActiveUsersProps) {
  const {
    data,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['systemAnalytics', 'activeUsers'],
    queryFn: async () => {
      try {
        const systemAnalytics = await getSystemAnalytics(7); // Last 7 days
        const activeUsers = systemAnalytics?.analytics?.overview?.active_users || 0;
        return activeUsers;
      } catch (error) {
        console.error('Failed to fetch active users from system analytics:', error);
        return 0;
      }
    },
    refetchInterval: refreshInterval,
    staleTime: refreshInterval,
    retry: 2,
    retryDelay: 1000,
  });

  const activeUsersCount = data || 0;

  const getStatusColor = () => {
    if (isError) return 'bg-red-500';
    if (isLoading) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="flex items-center gap-3">
      <div className="p-2 bg-purple-50 dark:bg-purple-950 rounded-lg">
        <Users className="h-4 w-4 text-purple-600 dark:text-purple-400" />
      </div>
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <p className="text-xs text-muted-foreground">Active Users</p>
          <div className={`h-1.5 w-1.5 rounded-full ${getStatusColor()}`} />
        </div>
        <div className="flex items-baseline gap-1">
          <p className="text-lg font-bold">{activeUsersCount}</p>
          <p className="text-xs text-muted-foreground">online</p>
        </div>
        {isError && (
          <p className="text-xs text-red-600 truncate">{(error as Error)?.message || 'Failed to load active users'}</p>
        )}
      </div>
    </div>
  );
}
