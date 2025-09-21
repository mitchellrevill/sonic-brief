import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Shield, 
  User, 
  Upload, 
  Eye, 
  Settings, 
  FileText, 
  Search, 
  Filter,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Calendar,
  Globe,
  Monitor
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { getUserAuditLogs, type UserAuditLogsResponse, type UserAuditLogRecord } from '@/lib/api';
import { toast } from 'sonner';

interface UserAuditLogsProps {
  userId: string;
  days: number;
  onRefresh?: () => void;
}

export function UserAuditLogs({ userId, days }: UserAuditLogsProps) {
  const [auditLogs, setAuditLogs] = useState<UserAuditLogsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterEventType, setFilterEventType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');

  useEffect(() => {
    fetchAuditLogs();
  }, [userId, days]);

  const fetchAuditLogs = async () => {
    if (!userId) return;
    
    setLoading(true);
    setError(null);
    
    try {
      console.log(`🔍 Fetching audit logs for userId: "${userId}" (${typeof userId})`);
      const logs = await getUserAuditLogs(userId, days);
      console.log('📋 Audit logs response:', logs);
      setAuditLogs(logs);
    } catch (error: any) {
      console.error('❌ Failed to fetch audit logs:', error);
      setError(error.message || 'Failed to load audit logs');
      toast.error('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType.toLowerCase()) {
      case 'user_login':
      case 'user_logout':
        return <User className="h-4 w-4" />;
      case 'permission_change':
      case 'permission_grant':
      case 'permission_revoke':
        return <Shield className="h-4 w-4" />;
      case 'job_created':
      case 'job_uploaded':
        return <Upload className="h-4 w-4" />;
      case 'job_shared':
      case 'job_unshared':
        return <Eye className="h-4 w-4" />;
      case 'prompt_created':
      case 'prompt_modified':
        return <FileText className="h-4 w-4" />;
      case 'system_access':
      case 'admin_action':
        return <Settings className="h-4 w-4" />;
      default:
        return <Clock className="h-4 w-4" />;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType.toLowerCase()) {
      case 'user_login':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'user_logout':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'permission_change':
      case 'permission_grant':
      case 'permission_revoke':
        return 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200';
      case 'job_created':
      case 'job_uploaded':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'job_shared':
      case 'job_unshared':
        return 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200';
      case 'admin_action':
      case 'system_access':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'success':
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed':
      case 'error':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const formatEventDescription = (record: UserAuditLogRecord) => {
    const { event_type, metadata, resource_type, resource_id } = record;
    
    switch (event_type.toLowerCase()) {
      case 'user_login':
        return `User logged in ${metadata?.login_method ? `via ${metadata.login_method}` : ''}`;
      case 'user_logout':
        return 'User logged out';
      case 'permission_change':
        return `Permission changed ${metadata?.from ? `from ${metadata.from}` : ''} ${metadata?.to ? `to ${metadata.to}` : ''}`;
      case 'job_created':
        return `Created new job ${resource_id ? `(${resource_id.slice(0, 8)}...)` : ''}`;
      case 'job_shared':
        return `Shared job with ${metadata?.shared_with || 'another user'}`;
      case 'admin_action':
        return `Performed admin action: ${metadata?.action || 'unknown'}`;
      default:
        return `${event_type.replace('_', ' ')} ${resource_type ? `on ${resource_type}` : ''}`;
    }
  };

  const filteredLogs = auditLogs?.records.filter((record) => {
    const matchesSearch = searchTerm === '' || 
      record.event_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      formatEventDescription(record).toLowerCase().includes(searchTerm.toLowerCase()) ||
      (record.metadata?.ip_address && record.metadata.ip_address.includes(searchTerm));
    
    const matchesEventType = filterEventType === 'all' || record.event_type === filterEventType;
    
    const matchesStatus = filterStatus === 'all' || 
      (record.metadata?.status && record.metadata.status.toLowerCase() === filterStatus);
    
    return matchesSearch && matchesEventType && matchesStatus;
  }) || [];

  const uniqueEventTypes = Array.from(
    new Set(auditLogs?.records.map(r => r.event_type) || [])
  );

  if (loading) {
    return (
      <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Audit Logs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-3 p-3 rounded-lg border animate-pulse">
                <div className="h-8 w-8 bg-muted rounded-full" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-3/4 bg-muted rounded" />
                  <div className="h-3 w-1/2 bg-muted rounded" />
                </div>
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
            <Shield className="h-5 w-5" />
            Audit Logs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8">
            <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
            <p className="text-red-600 dark:text-red-400 mb-2">{error}</p>
            <Button onClick={fetchAuditLogs} variant="outline" size="sm">
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Audit Logs
            {auditLogs && (
              <Badge variant="secondary" className="ml-2">
                {filteredLogs.length} of {auditLogs.records.length}
              </Badge>
            )}
          </CardTitle>
          <Button onClick={fetchAuditLogs} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
        
        {/* Filters */}
        <div className="flex flex-wrap gap-2 pt-2">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search logs..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8"
            />
          </div>
          
          <Select value={filterEventType} onValueChange={setFilterEventType}>
            <SelectTrigger className="w-[180px]">
              <Filter className="h-4 w-4 mr-2" />
              <SelectValue placeholder="Event Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Events</SelectItem>
              {uniqueEventTypes.map((type) => (
                <SelectItem key={type} value={type}>
                  {type.replace('_', ' ')}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      
      <CardContent>
        {filteredLogs.length === 0 ? (
          <div className="text-center py-8">
            <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">
              {auditLogs?.records.length === 0 
                ? 'No audit logs found for this user in the selected period'
                : 'No logs match your current filters'
              }
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredLogs.slice(0, 50).map((record, index) => (
              <div
                key={`${record.timestamp}-${index}`}
                className="flex items-start gap-3 p-3 rounded-lg border hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center justify-center h-8 w-8 rounded-full bg-muted">
                  {getEventIcon(record.event_type)}
                </div>
                
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge className={getEventColor(record.event_type)}>
                      {record.event_type.replace('_', ' ')}
                    </Badge>
                    {record.metadata?.status && getStatusIcon(record.metadata.status)}
                  </div>
                  
                  <p className="text-sm font-medium text-foreground mb-1">
                    {formatEventDescription(record)}
                  </p>
                  
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {record.timestamp 
                        ? formatDistanceToNow(new Date(record.timestamp), { addSuffix: true })
                        : 'Unknown time'
                      }
                    </span>
                    
                    {record.metadata?.ip_address && (
                      <span className="flex items-center gap-1">
                        <Globe className="h-3 w-3" />
                        {record.metadata.ip_address}
                      </span>
                    )}
                    
                    {record.metadata?.user_agent && (
                      <span className="flex items-center gap-1">
                        <Monitor className="h-3 w-3" />
                        {record.metadata.user_agent.split(' ')[0]}
                      </span>
                    )}
                  </div>
                  
                  {/* Additional metadata */}
                  {record.metadata && Object.keys(record.metadata).length > 0 && (
                    <div className="mt-2 p-2 bg-muted/30 rounded text-xs">
                      <details>
                        <summary className="cursor-pointer text-muted-foreground hover:text-foreground">
                          View Details
                        </summary>
                        <pre className="mt-1 text-xs overflow-auto">
                          {JSON.stringify(record.metadata, null, 2)}
                        </pre>
                      </details>
                    </div>
                  )}
                </div>
              </div>
            ))}
            
            {filteredLogs.length > 50 && (
              <div className="text-center pt-4">
                <p className="text-sm text-muted-foreground">
                  Showing first 50 of {filteredLogs.length} logs. Use filters to refine results.
                </p>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
