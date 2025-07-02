# Analytics & System Health

## Overview
Sonic Brief features a modern analytics system for tracking user activity, job events, and system health, with real-time updates and dashboards.

### Key Features
- **Event Batching**: Reduces API load by batching analytics events.
- **Real-Time Updates**: WebSocket-based updates for dashboards and charts.
- **System Health Metrics**: API response time, error rates, and other health indicators surfaced in the UI.
- **Migration Plan**: Stepwise migration from legacy analytics to a new event-driven, batch-based system.
- **Integration**: Analytics hooks in all major frontend components and backend endpoints.

### Documentation
- See `frontend_app/src/lib/analytics_revamp.md` for refactor plan, migration checklist, and integration strategy.
