# Analytics System Refactoring Plan

## Current State Analysis

After examining the codebase, I've identified several issues with the current analytics implementation:

### Problems Identified

1. **Multiple Tracking Systems**: 
   - `sessionTracker.ts` - Session tracking with heartbeats
   - `analyticsService.ts` - Event tracking service  
   - Direct API calls in `api.ts` - Individual tracking calls
   - Backend has separate session and event endpoints

2. **Excessive API Requests**:
   - Each event triggers immediate API call
   - Session heartbeats every 5 minutes
   - Login/logout events as separate requests
   - Job events as separate requests

3. **Inconsistent Implementation**:
   - Some components track events, others don't
   - Different tracking patterns across the app
   - No standardized event schema

4. **Data Quality Issues**:
   - Backend shows sample data when analytics container is empty
   - Events may not be properly aggregated
   - Inconsistent metadata across events

5. **Performance Impact**:
   - No batching of events
   - No offline queue
   - No retry mechanism for failed events

## Proposed Solution: Piggyback Analytics

### Core Concept
Instead of separate analytics API calls, embed analytics data in existing requests and responses. This reduces server load and ensures analytics data is always captured when users perform actions.

### Implementation Strategy

#### 1. Frontend: Unified Analytics Manager

```typescript
// lib/analytics/AnalyticsManager.ts
interface AnalyticsEvent {
  type: 'session_start' | 'session_end' | 'page_view' | 'job_created' | 'job_completed' | 'user_action';
  timestamp: string;
  metadata?: Record<string, any>;
}

interface AnalyticsContext {
  sessionId: string;
  userId?: string;
  currentPage: string;
  userAgent: string;
  timeZone: string;
}

class AnalyticsManager {
  private events: AnalyticsEvent[] = [];
  private context: AnalyticsContext;
  private isOnline: boolean = navigator.onLine;
  
  // Attach analytics to existing API requests
  public attachToRequest(requestData: any): any {
    return {
      ...requestData,
      _analytics: {
        context: this.context,
        pendingEvents: this.flushPendingEvents()
      }
    };
  }
  
  // Process analytics from API responses
  public processResponse(response: any): void {
    if (response._analytics_ack) {
      // Server confirmed receipt of analytics
      this.clearProcessedEvents(response._analytics_ack.processedEventIds);
    }
  }
}
```

#### 2. API Request Enhancement

```typescript
// Enhanced API calls with embedded analytics
export async function uploadFile(
  file: File,
  prompt_category_id: string,
  prompt_subcategory_id: string,
  token?: string,
): Promise<UploadResponse> {
  const analyticsManager = AnalyticsManager.getInstance();
  
  // Add job creation event to queue
  analyticsManager.queueEvent('job_created', {
    file_name: file.name,
    file_size: file.size,
    file_type: file.type,
    category_id: prompt_category_id,
    subcategory_id: prompt_subcategory_id
  });
  
  const formData = new FormData();
  formData.append("file", file);
  formData.append("prompt_category_id", prompt_category_id);
  formData.append("prompt_subcategory_id", prompt_subcategory_id);
  
  // Attach analytics to the request
  const requestWithAnalytics = analyticsManager.attachToRequest({
    file: file,
    prompt_category_id,
    prompt_subcategory_id
  });
  
  // Add analytics data as form fields
  formData.append("_analytics", JSON.stringify(requestWithAnalytics._analytics));
  
  const response = await fetch(UPLOAD_API, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  
  const data = await response.json();
  
  // Process analytics acknowledgment
  analyticsManager.processResponse(data);
  
  return data;
}
```

#### 3. Session Management Integration

```typescript
// Integrate session tracking with regular API calls
export async function fetchJobs(): Promise<Job[]> {
  const analyticsManager = AnalyticsManager.getInstance();
  
  // Queue page view event
  analyticsManager.queueEvent('page_view', {
    page: window.location.pathname,
    referrer: document.referrer
  });
  
  const requestData = analyticsManager.attachToRequest({});
  
  const response = await fetch(`${JOBS_API}?_analytics=${encodeURIComponent(JSON.stringify(requestData._analytics))}`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  const data = await response.json();
  analyticsManager.processResponse(data);
  
  return data.jobs;
}
```

#### 4. Backend: Middleware-Based Analytics Processing

```python
# backend/app/middleware/analytics_middleware.py
from fastapi import Request, Response
import json
from typing import Dict, Any, Optional

class AnalyticsMiddleware:
    def __init__(self, analytics_service: AnalyticsService):
        self.analytics_service = analytics_service
    
    async def process_request_analytics(self, request: Request, user_id: str) -> Optional[str]:
        """Extract and process analytics from request"""
        analytics_data = None
        
        # Check for analytics in form data
        if hasattr(request, 'form'):
            form = await request.form()
            if '_analytics' in form:
                analytics_data = json.loads(form['_analytics'])
        
        # Check for analytics in query params
        elif '_analytics' in request.query_params:
            analytics_data = json.loads(request.query_params['_analytics'])
        
        # Check for analytics in JSON body
        elif request.headers.get('content-type') == 'application/json':
            body = await request.json()
            if '_analytics' in body:
                analytics_data = body['_analytics']
        
        if analytics_data:
            return await self.process_analytics_events(
                analytics_data, 
                user_id, 
                request.url.path
            )
        
        return None
    
    async def process_analytics_events(
        self, 
        analytics_data: Dict[str, Any], 
        user_id: str,
        endpoint: str
    ) -> str:
        """Process analytics events and return acknowledgment ID"""
        processed_events = []
        
        for event in analytics_data.get('pendingEvents', []):
            event_id = await self.analytics_service.track_event(
                event_type=event['type'],
                user_id=user_id,
                metadata={
                    **event.get('metadata', {}),
                    'endpoint': endpoint,
                    'context': analytics_data.get('context', {})
                }
            )
            processed_events.append(event_id)
        
        return json.dumps({'processedEventIds': processed_events})
```

#### 5. Enhanced Job Tracking

```typescript
// Job completion tracking integrated with status polling
export async function pollJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${JOBS_API}/${jobId}/status`);
  const data = await response.json();
  
  // Automatically track job completion
  if (data.status === 'completed' && !data.completion_tracked) {
    const analyticsManager = AnalyticsManager.getInstance();
    analyticsManager.queueEvent('job_completed', {
      job_id: jobId,
      processing_time: data.processing_time,
      audio_duration: data.audio_duration,
      transcription_method: data.transcription_method,
      success: true
    });
    
    // Mark as tracked to avoid duplicate events
    data.completion_tracked = true;
  }
  
  return data;
}
```

#### 6. Real-time Analytics Dashboard Updates

```typescript
// WebSocket integration for real-time analytics
class AnalyticsDashboard {
  private websocket: WebSocket;
  
  connectRealTimeUpdates() {
    this.websocket = new WebSocket(`${WS_URL}/analytics/live`);
    
    this.websocket.onmessage = (event) => {
      const update = JSON.parse(event.data);
      
      if (update.type === 'analytics_update') {
        // Update dashboard with real-time data
        this.updateCharts(update.data);
      }
    };
  }
  
  updateCharts(newData: AnalyticsUpdate) {
    // Update React state to trigger re-render
    setAnalyticsData(prevData => ({
      ...prevData,
      daily_activity: {
        ...prevData.daily_activity,
        [newData.date]: newData.job_count
      }
    }));
  }
}
```

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
1. Create `AnalyticsManager` class with event queuing
2. Implement request/response enhancement utilities
3. Create analytics middleware for backend
4. Set up event batching and offline storage

### Phase 2: API Integration (Week 2)
1. Modify all API functions to include analytics
2. Update backend endpoints to process embedded analytics
3. Implement analytics acknowledgment system
4. Add job lifecycle tracking

### Phase 3: Real-time Features (Week 3)
1. Implement WebSocket analytics updates
2. Create real-time dashboard components
3. Add performance monitoring
4. Implement analytics health checks

### Phase 4: Data Quality & Cleanup (Week 4)
1. Remove old analytics systems
2. Migrate existing analytics data
3. Implement data validation
4. Add comprehensive testing

## Benefits of This Approach

### Reduced Server Load
- Single API call serves dual purpose (business logic + analytics)
- Batched event processing
- Automatic retry for failed requests

### Improved Data Quality
- Analytics always captured with business actions
- Consistent metadata across events
- No lost events due to separate API failures

### Better Performance
- Fewer HTTP requests
- Offline event queuing
- Real-time dashboard updates

### Simplified Maintenance
- Single analytics system to maintain
- Consistent tracking patterns
- Centralized configuration

## Critical Analysis: Is This the Best Practice?

### Re-evaluating the Piggyback Approach

After further consideration, the piggyback analytics approach has some significant drawbacks that may not make it the best practice for all scenarios:

#### Concerns with Piggyback Analytics

1. **Tight Coupling**: 
   - Business logic becomes tightly coupled with analytics
   - Makes API contracts more complex
   - Harder to A/B test analytics without affecting core functionality

2. **Request Payload Bloat**:
   - Adds overhead to every API request
   - May impact performance on mobile/slow connections
   - Complicates request debugging and logging

3. **Failure Propagation**:
   - Analytics processing errors could affect business operations
   - Harder to isolate analytics issues from core functionality
   - May require complex error handling to prevent cascading failures

4. **Compliance and Privacy**:
   - Harder to implement granular privacy controls
   - GDPR/privacy requirements may need separate handling
   - Audit trails become more complex

## Better Practice: Hybrid Event-Driven Architecture

### Recommended Approach: Asynchronous Event Streaming

```typescript
// lib/analytics/EventBus.ts
interface AnalyticsEvent {
  id: string;
  type: string;
  timestamp: string;
  userId?: string;
  sessionId: string;
  payload: Record<string, any>;
  metadata: {
    source: string;
    version: string;
    retryCount: number;
  };
}

class AnalyticsEventBus {
  private queue: AnalyticsEvent[] = [];
  private isProcessing = false;
  private batchSize = 10;
  private batchTimeout = 5000; // 5 seconds
  private retryAttempts = 3;
  
  // Emit events without blocking business logic
  emit(eventType: string, payload: Record<string, any>): void {
    const event: AnalyticsEvent = {
      id: crypto.randomUUID(),
      type: eventType,
      timestamp: new Date().toISOString(),
      userId: this.getCurrentUserId(),
      sessionId: this.getSessionId(),
      payload,
      metadata: {
        source: window.location.pathname,
        version: '1.0',
        retryCount: 0
      }
    };
    
    this.queue.push(event);
    this.scheduleProcessing();
  }
  
  private async scheduleProcessing(): Promise<void> {
    if (this.isProcessing) return;
    
    // Process immediately if queue is full, otherwise wait for timeout
    const shouldProcessNow = this.queue.length >= this.batchSize;
    
    if (shouldProcessNow) {
      await this.processQueue();
    } else {
      setTimeout(() => this.processQueue(), this.batchTimeout);
    }
  }
  
  private async processQueue(): Promise<void> {
    if (this.isProcessing || this.queue.length === 0) return;
    
    this.isProcessing = true;
    const batch = this.queue.splice(0, this.batchSize);
    
    try {
      await this.sendBatch(batch);
    } catch (error) {
      // Retry failed events
      const retriableEvents = batch
        .filter(event => event.metadata.retryCount < this.retryAttempts)
        .map(event => ({
          ...event,
          metadata: {
            ...event.metadata,
            retryCount: event.metadata.retryCount + 1
          }
        }));
      
      this.queue.unshift(...retriableEvents);
    } finally {
      this.isProcessing = false;
      
      // Continue processing if more events exist
      if (this.queue.length > 0) {
        setTimeout(() => this.processQueue(), 1000);
      }
    }
  }
  
  private async sendBatch(events: AnalyticsEvent[]): Promise<void> {
    const response = await fetch('/api/analytics/batch', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.getAuthToken()}`
      },
      body: JSON.stringify({ events })
    });
    
    if (!response.ok) {
      throw new Error(`Analytics batch failed: ${response.status}`);
    }
  }
}
```

### Event-Driven Job Tracking

```typescript
// lib/analytics/JobAnalytics.ts
class JobAnalytics {
  private eventBus: AnalyticsEventBus;
  
  constructor(eventBus: AnalyticsEventBus) {
    this.eventBus = eventBus;
  }
  
  trackJobCreated(jobData: {
    jobId: string;
    fileName: string;
    fileSize: number;
    fileType: string;
    category: string;
    subcategory: string;
  }): void {
    this.eventBus.emit('job_created', {
      job_id: jobData.jobId,
      file_name: jobData.fileName,
      file_size: jobData.fileSize,
      file_type: jobData.fileType,
      category: jobData.category,
      subcategory: jobData.subcategory,
      estimated_duration: this.estimateProcessingTime(jobData)
    });
  }
  
  trackJobProgress(jobId: string, progress: number): void {
    this.eventBus.emit('job_progress', {
      job_id: jobId,
      progress_percentage: progress,
      timestamp: new Date().toISOString()
    });
  }
  
  trackJobCompleted(jobData: {
    jobId: string;
    actualDuration: number;
    transcriptionMethod: string;
    wordCount: number;
    accuracy?: number;
  }): void {
    this.eventBus.emit('job_completed', {
      job_id: jobData.jobId,
      actual_duration: jobData.actualDuration,
      transcription_method: jobData.transcriptionMethod,
      word_count: jobData.wordCount,
      accuracy_score: jobData.accuracy,
      completion_time: new Date().toISOString()
    });
  }
}
```

### React Hook Integration

```typescript
// hooks/useAnalytics.ts
import { useCallback, useEffect } from 'react';
import { AnalyticsEventBus } from '@/lib/analytics/EventBus';
import { JobAnalytics } from '@/lib/analytics/JobAnalytics';

const eventBus = new AnalyticsEventBus();
const jobAnalytics = new JobAnalytics(eventBus);

export function useAnalytics() {
  const trackPageView = useCallback((page: string, additionalData?: Record<string, any>) => {
    eventBus.emit('page_view', {
      page,
      referrer: document.referrer,
      viewport: {
        width: window.innerWidth,
        height: window.innerHeight
      },
      ...additionalData
    });
  }, []);
  
  const trackUserAction = useCallback((action: string, data?: Record<string, any>) => {
    eventBus.emit('user_action', {
      action,
      timestamp: new Date().toISOString(),
      ...data
    });
  }, []);
  
  const trackError = useCallback((error: Error, context?: Record<string, any>) => {
    eventBus.emit('error_occurred', {
      error_message: error.message,
      error_stack: error.stack,
      error_name: error.name,
      context: context || {},
      url: window.location.href
    });
  }, []);
  
  // Auto-track page views on mount
  useEffect(() => {
    trackPageView(window.location.pathname);
  }, [trackPageView]);
  
  return {
    trackPageView,
    trackUserAction,
    trackError,
    jobAnalytics
  };
}
```

### Backend: Dedicated Analytics Service

```python
# backend/app/services/analytics_ingestion_service.py
from typing import List, Dict, Any
import asyncio
from datetime import datetime
import logging

class AnalyticsIngestionService:
    def __init__(self, cosmos_db, event_store):
        self.cosmos_db = cosmos_db
        self.event_store = event_store
        self.logger = logging.getLogger(__name__)
    
    async def ingest_event_batch(self, events: List[Dict[str, Any]], user_id: str) -> Dict[str, Any]:
        """Process a batch of analytics events"""
        try:
            # Validate events
            validated_events = [self.validate_event(event, user_id) for event in events]
            
            # Store raw events for replay/debugging
            await self.store_raw_events(validated_events)
            
            # Process events asynchronously
            processing_tasks = [
                self.process_single_event(event) for event in validated_events
            ]
            
            results = await asyncio.gather(*processing_tasks, return_exceptions=True)
            
            # Update real-time aggregations
            await self.update_real_time_metrics(validated_events)
            
            return {
                'status': 'success',
                'processed_count': len([r for r in results if not isinstance(r, Exception)]),
                'failed_count': len([r for r in results if isinstance(r, Exception)]),
                'ingestion_time': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Batch ingestion failed: {str(e)}")
            raise
    
    async def process_single_event(self, event: Dict[str, Any]) -> str:
        """Process individual event and update relevant aggregations"""
        event_type = event.get('type')
        
        # Route to specific processors
        if event_type == 'job_created':
            await self.process_job_created(event)
        elif event_type == 'job_completed':
            await self.process_job_completed(event)
        elif event_type == 'page_view':
            await self.process_page_view(event)
        elif event_type == 'user_action':
            await self.process_user_action(event)
        
        # Always update general metrics
        await self.update_user_activity(event)
        await self.update_session_metrics(event)
        
        return event['id']
    
    async def update_real_time_metrics(self, events: List[Dict[str, Any]]) -> None:
        """Update real-time dashboard metrics"""
        # Calculate metrics for this batch
        job_events = [e for e in events if e['type'].startswith('job_')]
        page_views = [e for e in events if e['type'] == 'page_view']
        
        if job_events or page_views:
            # Publish to WebSocket for real-time updates
            await self.publish_real_time_update({
                'timestamp': datetime.utcnow().isoformat(),
                'job_events': len(job_events),
                'page_views': len(page_views),
                'active_users': len(set(e['userId'] for e in events if e.get('userId')))
            })
```

### WebSocket Real-time Updates

```python
# backend/app/websocket/analytics_ws.py
from fastapi import WebSocket
import json
from typing import Dict, Any

class AnalyticsWebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast_analytics_update(self, data: Dict[str, Any]):
        """Broadcast analytics updates to all connected dashboards"""
        message = {
            'type': 'analytics_update',
            'data': data
        }
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)
```

## Current System Integration Points

### Frontend Files to Migrate/Replace

#### Core Analytics Files
- `frontend_app/src/lib/sessionTracker.ts` - Session tracking with heartbeats (REPLACE)
- `frontend_app/src/lib/analyticsService.ts` - Event tracking service (REPLACE)
- `frontend_app/src/components/SessionProvider.tsx` - Session management component (REFACTOR)

#### API Integration Files
- `frontend_app/src/lib/api.ts` - Contains direct analytics calls and tracking (REFACTOR)
- `frontend_app/src/lib/apiConstants.ts` - Analytics API endpoints (UPDATE)

#### Dashboard Components
- `frontend_app/src/components/user-managment/UserManagementDashboard.tsx` - Main analytics dashboard (INTEGRATE)
- `frontend_app/src/components/user-managment/UserManagement/AnalyticsChart.tsx` - Chart component (INTEGRATE)
- `frontend_app/src/components/user-managment/UserManagement/AnalyticsOverviewCards.tsx` - Overview cards (INTEGRATE)
- `frontend_app/src/components/user-managment/components/SystemAnalyticsTab.tsx` - System analytics tab (INTEGRATE)
- `frontend_app/src/components/user-managment/components/SystemHealthMetrics.tsx` - Health metrics (INTEGRATE)

#### Route Files
- `frontend_app/src/routes/_layout.tsx` - Main layout with SessionProvider (UPDATE)

### Backend Files to Update

#### Analytics Services
- `backend_app/app/services/analytics_service.py` - Main analytics service (REFACTOR)
- `backend_app/app/routers/analytics.py` - Analytics API endpoints (UPDATE)

#### Models
- `backend_app/app/models/analytics_models.py` - Analytics data models (UPDATE)

#### Configuration
- `backend_app/app/core/config.py` - Database configuration (UPDATE if needed)

## Integration Strategy for Current Components

### 1. UserManagementDashboard Integration

```typescript
// Updated UserManagementDashboard.tsx
import { useState, useMemo, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useAnalytics } from "@/hooks/useAnalytics";
import { AnalyticsEventBus } from "@/lib/analytics/EventBus";

export function UserManagementDashboard() {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterPermission, setFilterPermission] = useState<"All" | PermissionLevel>("All");
  const [analyticsPeriod, setAnalyticsPeriod] = useState<7 | 30 | 180 | 365 | 'total'>(30);
  
  const guard = useCapabilityGuard();
  const navigate = useNavigate();
  const { trackPageView, trackUserAction } = useAnalytics();

  // Track dashboard access
  useEffect(() => {
    trackPageView('/admin/users', {
      section: 'user_management',
      permission_level: guard.currentPermission
    });
  }, [trackPageView, guard.currentPermission]);

  // Enhanced analytics query with real-time updates
  const { data: systemAnalytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ['systemAnalytics', analyticsPeriod],
    queryFn: () => getSystemAnalytics(analyticsPeriod),
    enabled: guard.canViewAnalytics,
    refetchInterval: 30000, // Refresh every 30 seconds for real-time feel
    onSuccess: (data) => {
      // Track analytics data access
      trackUserAction('analytics_viewed', {
        period: analyticsPeriod,
        data_points: Object.keys(data.analytics?.trends?.daily_activity || {}).length
      });
    }
  });

  // Real-time analytics updates via WebSocket
  useEffect(() => {
    if (guard.canViewAnalytics) {
      const eventBus = AnalyticsEventBus.getInstance();
      eventBus.subscribeToRealTimeUpdates((update) => {
        // Update analytics data in real-time
        if (update.type === 'analytics_update') {
          // Trigger query invalidation to refresh data
          queryClient.invalidateQueries(['systemAnalytics']);
        }
      });
    }
  }, [guard.canViewAnalytics]);

  // Track user interactions
  const handlePeriodChange = (newPeriod: typeof analyticsPeriod) => {
    setAnalyticsPeriod(newPeriod);
    trackUserAction('analytics_period_changed', {
      from: analyticsPeriod,
      to: newPeriod
    });
  };

  const handleUserSearch = (term: string) => {
    setSearchTerm(term);
    if (term.length > 2) {
      trackUserAction('user_search', {
        search_term_length: term.length,
        results_count: filteredUsers.length
      });
    }
  };

  // ...existing code...
}
```

### 2. Enhanced SessionProvider Integration

```typescript
// Updated SessionProvider.tsx
import { useEffect, useRef } from 'react';
import { useRouter } from '@tanstack/react-router';
import { AnalyticsEventBus } from '@/lib/analytics/EventBus';
import { useAnalytics } from '@/hooks/useAnalytics';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const startedRef = useRef(false);
  const { trackPageView } = useAnalytics();
  const eventBus = AnalyticsEventBus.getInstance();

  useEffect(() => {
    // Initialize analytics event bus
    if (!startedRef.current) {
      eventBus.initialize();
      
      // Track session start
      eventBus.emit('session_start', {
        user_agent: navigator.userAgent,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        },
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        referrer: document.referrer
      });
      
      startedRef.current = true;
    }

    // Track page navigation
    const unsubscribe = router.subscribe('onLoad', ({ toLocation, fromLocation }) => {
      trackPageView(toLocation.pathname, {
        from_page: fromLocation?.pathname,
        navigation_type: fromLocation ? 'navigation' : 'initial_load'
      });
    });

    // Track page visibility changes
    const handleVisibilityChange = () => {
      eventBus.emit('page_visibility_change', {
        visibility_state: document.visibilityState,
        page: window.location.pathname
      });
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup function
    return () => {
      unsubscribe();
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      
      // Track session end
      eventBus.emit('session_end', {
        session_duration: Date.now() - eventBus.getSessionStartTime(),
        pages_visited: eventBus.getPagesVisited(),
        final_page: window.location.pathname
      });
      
      // Flush any pending events before cleanup
      eventBus.flush();
      startedRef.current = false;
    };
  }, [router, trackPageView, eventBus]);

  return <>{children}</>;
}
```

### 3. API Integration with Event Tracking

```typescript
// Enhanced API functions in api.ts
import { AnalyticsEventBus } from '@/lib/analytics/EventBus';

const eventBus = AnalyticsEventBus.getInstance();

// Enhanced upload function with comprehensive tracking
export async function uploadFile(
  file: File,
  prompt_category_id: string,
  prompt_subcategory_id: string,
  token?: string,
): Promise<UploadResponse> {
  const startTime = Date.now();
  
  // Track upload initiation
  eventBus.emit('job_upload_started', {
    file_name: file.name,
    file_size: file.size,
    file_type: file.type,
    category_id: prompt_category_id,
    subcategory_id: prompt_subcategory_id
  });

  if (!token) {
    token = localStorage.getItem("token") || undefined;
    if (!token) throw new Error("No authentication token found. Please log in again.");
  }

  const formData = new FormData();
  formData.append("file", file);
  formData.append("prompt_category_id", prompt_category_id);
  formData.append("prompt_subcategory_id", prompt_subcategory_id);

  try {
    const response = await fetch(UPLOAD_API, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const data: UploadResponse = await response.json();
    
    if (!response.ok) {
      // Track upload failure
      eventBus.emit('job_upload_failed', {
        file_name: file.name,
        file_size: file.size,
        error_status: response.status,
        error_message: data.message,
        upload_duration: Date.now() - startTime
      });
      throw new Error(data.message || `HTTP error! status: ${response.status}`);
    }

    // Track successful upload
    eventBus.emit('job_upload_completed', {
      job_id: data.job_id,
      file_name: file.name,
      file_size: file.size,
      file_type: file.type,
      category_id: prompt_category_id,
      subcategory_id: prompt_subcategory_id,
      upload_duration: Date.now() - startTime
    });

    return data;
  } catch (error) {
    // Track network or other errors
    eventBus.emit('job_upload_error', {
      file_name: file.name,
      error_type: error instanceof Error ? error.name : 'Unknown',
      error_message: error instanceof Error ? error.message : String(error),
      upload_duration: Date.now() - startTime
    });
    throw error;
  }
}

// Enhanced login with analytics
export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const startTime = Date.now();
  
  // Track login attempt
  eventBus.emit('login_attempted', {
    login_method: 'email_password',
    email_domain: email.split('@')[1]
  });

  try {
    const response = await fetch(LOGIN_API, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data: LoginResponse = await response.json();

    if (!response.ok) {
      // Track login failure
      eventBus.emit('login_failed', {
        error_status: response.status,
        error_message: data.message,
        login_duration: Date.now() - startTime,
        email_domain: email.split('@')[1]
      });
      
      return {
        status: response.status,
        message: data.message || "An error occurred during login",
        access_token: "",
        token_type: "",
      };
    }

    // Track successful login
    if (data.access_token) {
      eventBus.emit('login_successful', {
        login_duration: Date.now() - startTime,
        permission_level: data.permission,
        email_domain: email.split('@')[1]
      });
    }

    return data;
  } catch (error) {
    // Track network errors
    eventBus.emit('login_error', {
      error_type: error instanceof Error ? error.name : 'Unknown',
      error_message: error instanceof Error ? error.message : String(error),
      login_duration: Date.now() - startTime
    });
    throw error;
  }
}

// Job status polling with progress tracking
export async function pollJobStatus(jobId: string): Promise<JobStatus> {
  const response = await fetch(`${JOBS_API}/${jobId}/status`);
  const data = await response.json();
  
  // Track job progress
  if (data.progress !== undefined) {
    eventBus.emit('job_progress_update', {
      job_id: jobId,
      progress_percentage: data.progress,
      status: data.status,
      estimated_completion: data.estimated_completion
    });
  }
  
  // Track job completion
  if (data.status === 'completed' && !data._completion_tracked) {
    eventBus.emit('job_completed', {
      job_id: jobId,
      processing_time: data.processing_time,
      audio_duration: data.audio_duration,
      transcription_method: data.transcription_method,
      word_count: data.word_count,
      file_size: data.file_size,
      success: true
    });
    
    // Mark as tracked to avoid duplicates
    data._completion_tracked = true;
  }
  
  // Track job failures
  if (data.status === 'failed') {
    eventBus.emit('job_failed', {
      job_id: jobId,
      error_message: data.error_message,
      processing_time: data.processing_time,
      failure_stage: data.failure_stage
    });
  }
  
  return data;
}
```

### 4. Real-time Dashboard Updates

```typescript
// Enhanced AnalyticsChart.tsx with real-time updates
import { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import { ResponsiveContainer, LineChart, CartesianGrid, XAxis, YAxis, Tooltip, Line } from "recharts";
import { AnalyticsEventBus } from '@/lib/analytics/EventBus';

interface AnalyticsChartProps {
  analyticsLoading: boolean;
  analyticsData: { 
    date: string; 
    totalMinutes: number; 
    activeUsers: number;
    totalJobs?: number; 
  }[];
  analyticsPeriod: 7 | 30 | 180 | 365 | 'total';
}

export function AnalyticsChart({ analyticsLoading, analyticsData, analyticsPeriod }: AnalyticsChartProps) {
  const [realtimeData, setRealtimeData] = useState(analyticsData);
  const [isConnected, setIsConnected] = useState(false);

  // Subscribe to real-time updates
  useEffect(() => {
    const eventBus = AnalyticsEventBus.getInstance();
    
    const unsubscribe = eventBus.subscribeToRealTimeUpdates((update) => {
      if (update.type === 'job_completed' || update.type === 'job_created') {
        // Update today's data point
        const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        setRealtimeData(prevData => {
          const updatedData = [...prevData];
          const todayIndex = updatedData.findIndex(item => item.date === today);
          
          if (todayIndex >= 0) {
            if (update.type === 'job_completed') {
              updatedData[todayIndex] = {
                ...updatedData[todayIndex],
                totalJobs: (updatedData[todayIndex].totalJobs || 0) + 1
              };
            }
          } else {
            // Add today's data if it doesn't exist
            updatedData.push({
              date: today,
              totalMinutes: update.type === 'job_completed' ? 1 : 0,
              activeUsers: 1,
              totalJobs: 1
            });
          }
          
          return updatedData;
        });
      }
    });

    eventBus.onConnectionStateChange((connected) => {
      setIsConnected(connected);
    });

    return unsubscribe;
  }, []);

  // Update local state when props change
  useEffect(() => {
    setRealtimeData(analyticsData);
  }, [analyticsData]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          System Usage Analytics
          {isConnected && (
            <span className="ml-2 h-2 w-2 bg-green-500 rounded-full animate-pulse" 
                  title="Real-time updates enabled" />
          )}
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Daily transcription activity and user engagement over the {
            analyticsPeriod === 'total' ? 'entire system history' : 
            analyticsPeriod === 365 ? 'last 12 months' :
            analyticsPeriod === 180 ? 'last 6 months' :
            `last ${analyticsPeriod} days`
          }. Shows daily job counts and active users.
          {isConnected && " (Live updates enabled)"}
        </p>
      </CardHeader>
      <CardContent>
        {analyticsLoading ? (
          <div className="h-[300px] flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={realtimeData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip 
                formatter={(value, name) => {
                  if (name === 'totalMinutes') return [`${value} jobs`, 'Daily Jobs'];
                  if (name === 'activeUsers') return [`${value} users`, 'Active Users'];
                  if (name === 'totalJobs') return [`${value} jobs`, 'Daily Jobs'];
                  return [value, name];
                }}
                labelFormatter={(label) => `Date: ${label}`}
              />
              <Line 
                type="monotone" 
                dataKey="totalMinutes" 
                stroke="#3b82f6" 
                strokeWidth={2}
                dot={{ fill: '#3b82f6' }}
                name="totalMinutes"
              />
              <Line 
                type="monotone" 
                dataKey="activeUsers" 
                stroke="#10b981" 
                strokeWidth={2}
                dot={{ fill: '#10b981' }}
                name="activeUsers"
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
```

### 5. File Upload Component Integration

```typescript
// Example integration in upload components
import { useAnalytics } from '@/hooks/useAnalytics';

export function FileUploadComponent() {
  const { jobAnalytics, trackUserAction } = useAnalytics();
  
  const handleFileSelect = (file: File) => {
    trackUserAction('file_selected', {
      file_size: file.size,
      file_type: file.type,
      file_name_length: file.name.length
    });
  };
  
  const handleUploadStart = (file: File, category: string, subcategory: string) => {
    jobAnalytics.trackJobCreated({
      jobId: '', // Will be set after API response
      fileName: file.name,
      fileSize: file.size,
      fileType: file.type,
      category,
      subcategory
    });
  };
  
  const handleUploadProgress = (jobId: string, progress: number) => {
    jobAnalytics.trackJobProgress(jobId, progress);
  };
  
  const handleUploadComplete = (jobData: any) => {
    jobAnalytics.trackJobCompleted({
      jobId: jobData.job_id,
      actualDuration: jobData.processing_time,
      transcriptionMethod: jobData.transcription_method,
      wordCount: jobData.word_count,
      accuracy: jobData.accuracy_score
    });
  };
  
  // ...component logic...
}
```

## Migration Checklist

### Frontend Migration Steps

1. **Phase 1: Core Infrastructure**
   - [ ] Create `lib/analytics/EventBus.ts`
   - [ ] Create `lib/analytics/JobAnalytics.ts`
   - [ ] Create `hooks/useAnalytics.ts`
   - [ ] Update `lib/apiConstants.ts` with new batch endpoint

2. **Phase 2: Component Integration**
   - [ ] Refactor `SessionProvider.tsx` to use EventBus
   - [ ] Update `UserManagementDashboard.tsx` with analytics hooks
   - [ ] Enhance `AnalyticsChart.tsx` with real-time updates
   - [ ] Update all upload components to use analytics hooks

3. **Phase 3: API Integration**
   - [ ] Update `api.ts` functions to emit events
   - [ ] Remove direct analytics API calls
   - [ ] Implement batch analytics endpoint client

4. **Phase 4: Cleanup**
   - [ ] Remove `sessionTracker.ts`
   - [ ] Remove `analyticsService.ts`
   - [ ] Clean up unused API endpoints
   - [ ] Update types and interfaces

### Backend Migration Steps

1. **Phase 1: New Analytics Infrastructure**
   - [ ] Create batch analytics ingestion endpoint
   - [ ] Update analytics models for new event schema
   - [ ] Implement WebSocket real-time updates

2. **Phase 2: Data Processing**
   - [ ] Refactor analytics aggregation logic
   - [ ] Implement real-time metric updates
   - [ ] Create event validation and processing

3. **Phase 3: Migration**
   - [ ] Migrate existing analytics data
   - [ ] Remove old analytics endpoints
   - [ ] Update API documentation

This integration strategy maintains backward compatibility while gradually moving to the new event-driven system, ensuring a smooth transition without disrupting the current user experience.