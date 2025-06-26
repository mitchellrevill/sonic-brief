import { Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { getActiveUsers } from '@/lib/api';

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
    queryKey: ['activeUsers', 5],
    queryFn: async () => {
      const response = await getActiveUsers(5); // Users active in last 5 minutes
      return response.data.active_users;
    },
    refetchInterval: refreshInterval,
    staleTime: refreshInterval,
  });

  const activeUsers = data ?? [];

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
          <p className="text-lg font-bold">{activeUsers.length}</p>
          <p className="text-xs text-muted-foreground">online</p>
        </div>
        {isError && (
          <p className="text-xs text-red-600 truncate">{(error as Error).message || 'Failed to load active users'}</p>
        )}
        {/* Optionally, show last updated time if needed using query data */}
      </div>
    </div>
  );
}
