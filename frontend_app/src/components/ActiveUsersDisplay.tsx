import { useEffect, useState } from 'react';
import { Users } from 'lucide-react';
import { getActiveUsers } from '@/lib/api';

interface ActiveUsersProps {
  refreshInterval?: number; // in milliseconds
}

export function ActiveUsersDisplay({ refreshInterval = 300000 }: ActiveUsersProps) {
  const [activeUsers, setActiveUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchActiveUsers = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getActiveUsers(5); // Users active in last 5 minutes
      setActiveUsers(response.data.active_users);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch active users:', err);
      setError('Failed to load active users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial fetch
    fetchActiveUsers();

    // Set up refresh interval
    const interval = setInterval(fetchActiveUsers, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval]);

  const getStatusColor = () => {
    if (error) return 'bg-red-500';
    if (loading) return 'bg-yellow-500';
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
        {error && (
          <p className="text-xs text-red-600 truncate">{error}</p>
        )}
        {!error && lastUpdated && (
          <p className="text-xs text-muted-foreground">
            Updated {lastUpdated.toLocaleTimeString([], { 
              hour: '2-digit', 
              minute: '2-digit'
            })}
          </p>
        )}
      </div>
    </div>
  );
}
