import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Server, Database, Cpu } from "lucide-react";
import type { SystemHealthResponse } from "@/lib/api";

interface SystemHealthMetricsProps {
  systemHealth: SystemHealthResponse | undefined;
  healthLoading: boolean;
}

export function SystemHealthMetrics({ systemHealth, healthLoading }: SystemHealthMetricsProps) {
  return (
  <Card className="bg-card/80 border border-muted-foreground/10 rounded-xl shadow-sm">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Activity className="h-5 w-5" />
          System Health
          <Badge variant="outline" className="text-xs">
            Real-time Metrics
          </Badge>
        </CardTitle>
        <p className="text-sm text-muted-foreground">
      Live system performance metrics — API, Database, and Memory
        </p>
      </CardHeader>
      <CardContent>
        {healthLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-muted rounded animate-pulse" />
                <div className="h-6 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : systemHealth ? (
          <>
            {/* Real Metrics - Only 3 meaningful ones */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
              <div className="space-y-2 p-4 border rounded-lg">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Server className="h-4 w-4" />
                  API Response Time
                </div>
                <div className="text-2xl font-bold">
                  {systemHealth.metrics.api_response_time_ms > 0 ? 
                    `${systemHealth.metrics.api_response_time_ms.toFixed(1)}ms` : 
                    'N/A'
                  }
                </div>
                <div className="text-xs text-muted-foreground">
                  {systemHealth.metrics.api_response_time_ms > 0 && 
                    (systemHealth.metrics.api_response_time_ms < 100 ? 'Excellent' :
                     systemHealth.metrics.api_response_time_ms < 500 ? 'Good' :
                     systemHealth.metrics.api_response_time_ms < 1000 ? 'Slow' : 'Very Slow')
                  }
                </div>
              </div>
              
              <div className="space-y-2 p-4 border rounded-lg">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Database className="h-4 w-4" />
                  Database Response
                </div>
                <div className="text-2xl font-bold">
                  {systemHealth.metrics.database_response_time_ms > 0 ? 
                    `${systemHealth.metrics.database_response_time_ms.toFixed(1)}ms` : 
                    systemHealth.metrics.database_response_time_ms === -1 ? 'Unavailable' : 'N/A'
                  }
                </div>
                <div className="text-xs text-muted-foreground">
                  {systemHealth.metrics.database_response_time_ms > 0 && 
                    (systemHealth.metrics.database_response_time_ms < 200 ? 'Excellent' :
                     systemHealth.metrics.database_response_time_ms < 500 ? 'Good' :
                     systemHealth.metrics.database_response_time_ms < 1000 ? 'Slow' : 'Very Slow')
                  }
                </div>
              </div>
              
              <div className="space-y-2 p-4 border rounded-lg">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Cpu className="h-4 w-4" />
                  Memory Usage
                </div>
                <div className="text-2xl font-bold">
                  {systemHealth.metrics.memory_usage_percentage > 0 ? 
                    `${systemHealth.metrics.memory_usage_percentage.toFixed(1)}%` : 
                    'N/A'
                  }
                </div>
                {systemHealth.metrics.memory_usage_percentage > 0 && (
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-muted rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full transition-all ${
                          systemHealth.metrics.memory_usage_percentage > 90 ? 'bg-red-500' :
                          systemHealth.metrics.memory_usage_percentage > 70 ? 'bg-yellow-500' :
                          'bg-green-500'
                        }`}
                        style={{ width: `${Math.min(systemHealth.metrics.memory_usage_percentage, 100)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* Service Status */}
            <div className="pt-4 border-t">
              <h4 className="text-sm font-medium text-muted-foreground mb-3">Service Status</h4>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {Object.entries(systemHealth.services)
                  .filter(([service]) => !service.includes('error')) // Filter out error messages
                  .map(([service, status]) => (
                  <div key={service} className="flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${
                      status === 'healthy' ? 'bg-green-500' : 
                      status === 'degraded' ? 'bg-yellow-500' : 
                      status === 'unavailable' ? 'bg-gray-500' :
                      'bg-red-500'
                    }`} />
                    <span className="text-xs capitalize">{service.replace('_', ' ')}</span>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Overall Status */}
            <div className="mt-4 p-3 bg-muted/30 rounded-lg">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${
                  systemHealth.status === 'healthy' ? 'bg-green-500' :
                  systemHealth.status === 'degraded' ? 'bg-yellow-500' :
                  'bg-red-500'
                }`} />
                <span className="font-medium">Overall Status: </span>
                <span className="capitalize">{systemHealth.status}</span>
              </div>
            </div>
            
            <div className="mt-4 text-xs text-muted-foreground">
              Last updated: {new Date(systemHealth.timestamp).toLocaleString()}
              <br />
              <span className="text-xs text-muted-foreground/80">
                Note: Only API, Database, and Memory metrics provide real data. Other metrics are not monitored.
              </span>
            </div>
          </>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <Server className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p>System health data unavailable</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
