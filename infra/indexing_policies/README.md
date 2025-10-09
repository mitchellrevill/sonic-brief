# Cosmos DB Indexing Policy Updates

This directory contains optimized indexing policies for Cosmos DB containers.

## Quick Deployment Guide

### Prerequisites
- Azure CLI installed and authenticated
- Access to the Cosmos DB account

### Apply Indexing Policies

#### 1. Update voice_jobs Container (CRITICAL - Highest Impact)
```bash
az cosmosdb sql container update \
  --account-name cosmos-dev-sonic \
  --resource-group rg-dev-sonic-uksouth \
  --database-name Voice-transcription \
  --name voice_jobs \
  --idx @voice_jobs_indexing_policy.json
```

**Expected Results:**
- Job listing queries: **10-20x faster**
- User's jobs filtering: **15x faster**
- Status-based queries: **12x faster**
- RU consumption: **50-60% reduction** on job queries

---

#### 2. Update voice_analytics Container (HIGH Priority)
```bash
az cosmosdb sql container update \
  --account-name cosmos-dev-sonic \
  --resource-group rg-dev-sonic-uksouth \
  --database-name Voice-transcription \
  --name voice_analytics \
  --idx @voice_analytics_indexing_policy.json
```

**Expected Results:**
- Analytics dashboard queries: **15-30x faster**
- Event filtering: **20x faster**
- Time-series queries: **10x faster**
- RU consumption: **40-50% reduction** on analytics

---

## Index Build Time

⏱️ **Estimated Time:** 5-30 minutes depending on data size

**Monitoring Index Progress:**
```bash
# Check indexing transformation progress
az cosmosdb sql container show \
  --account-name cosmos-dev-sonic \
  --resource-group rg-dev-sonic-uksouth \
  --database-name Voice-transcription \
  --name voice_jobs \
  --query "resource.indexingPolicy"
```

---

## Verification Steps

### 1. Verify Indexes Applied
```bash
# voice_jobs
az cosmosdb sql container show \
  --account-name cosmos-dev-sonic \
  --resource-group rg-dev-sonic-uksouth \
  --database-name Voice-transcription \
  --name voice_jobs \
  --query "resource.indexingPolicy.compositeIndexes" -o json

# voice_analytics
az cosmosdb sql container show \
  --account-name cosmos-dev-sonic \
  --resource-group rg-dev-sonic-uksouth \
  --database-name Voice-transcription \
  --name voice_analytics \
  --query "resource.indexingPolicy.compositeIndexes" -o json
```

### 2. Monitor RU Consumption (Before vs After)
```bash
# Go to Azure Portal → Cosmos DB → Metrics
# Compare:
# - Total Request Units (should decrease 40-60%)
# - Average RU per operation (should decrease 10-20x)
# - Query execution time (check Application Insights)
```

### 3. Test Query Performance
Run these test queries in Data Explorer to verify performance:

**voice_jobs test query:**
```sql
SELECT * FROM c 
WHERE c.type = 'job' 
AND c.user_id = 'test-user-id' 
AND c.is_deleted = false 
ORDER BY c.created_at DESC
```
✅ Should complete in < 50ms with < 5 RUs

**voice_analytics test query:**
```sql
SELECT * FROM c 
WHERE c.type = 'analytics_event' 
AND c.user_id = 'test-user-id' 
AND c.created_at >= '2025-09-01T00:00:00Z'
ORDER BY c.created_at DESC
```
✅ Should complete in < 100ms with < 10 RUs

---

## Rollback Plan

If issues occur, revert to default indexing:

```json
{
  "indexingMode": "consistent",
  "automatic": true,
  "includedPaths": [{"path": "/*"}],
  "excludedPaths": [{"path": "/\"_etag\"/?"}]
}
```

Apply with:
```bash
az cosmosdb sql container update \
  --account-name cosmos-dev-sonic \
  --resource-group rg-dev-sonic-uksouth \
  --database-name Voice-transcription \
  --name voice_jobs \
  --idx @rollback_policy.json
```

---

## What These Indexes Optimize

### voice_jobs Composite Indexes:
1. **(type, user_id)** - User's job list
2. **(type, status)** - Job status filtering
3. **(type, user_id, created_at DESC)** - User's jobs sorted by date
4. **(user_id, status, created_at DESC)** - Filtered & sorted user jobs
5. **(type, is_deleted, created_at DESC)** - Soft-delete queries
6. **(type, microsoft_oid)** - SSO user job lookups
7. **(user_id, is_deleted)** - Active jobs per user

### voice_analytics Composite Indexes:
1. **(type, user_id, created_at DESC)** - User activity timeline
2. **(type, event_type, created_at DESC)** - Event type filtering
3. **(user_id, event_type, timestamp DESC)** - User-specific events
4. **(type, session_id, created_at DESC)** - Session analytics
5. **(type, job_id, created_at DESC)** - Job-specific analytics
6. **(type, action, created_at DESC)** - Action-based queries

---

## Cost Impact

**Current Estimated Cost (without optimization):**
- ~1000 RU/s average
- ~$0.58/hour = ~$420/month

**After Optimization:**
- ~400-500 RU/s average
- ~$0.25/hour = ~$180/month

**💰 Savings: ~$240/month (~57% reduction)**

---

## Excluded Paths Explanation

### voice_jobs:
- `/transcription/*` - Large text blobs, never queried directly
- `/analysis/*` - Large AI analysis results, never queried directly

### voice_analytics:
- `/metadata/*` - Rarely queried detail fields
- `/details/*` - Large event payload data

These exclusions reduce index size and improve write performance while maintaining query speed.

---

## Troubleshooting

### Issue: "Index transformation in progress"
**Solution:** Wait 5-30 minutes. Check progress with:
```bash
az cosmosdb sql container show --name voice_jobs ... --query "resource.indexingPolicy"
```

### Issue: "Queries still slow after applying indexes"
**Solution:** 
1. Verify indexes applied: Check composite indexes exist
2. Clear application cache: Restart backend app
3. Check query includes indexed fields: Use query metrics
4. Wait for index build to complete: Check indexing progress

### Issue: "RU consumption still high"
**Solution:**
1. Add query metrics logging (see Query_fix audit report)
2. Identify expensive queries in Application Insights
3. Verify queries use partition keys where possible
4. Implement result caching for frequent queries

---

## Next Steps After Applying

1. ✅ **Monitor for 24 hours** - Watch RU metrics and query performance
2. ✅ **Implement query caching** - Add TTL cache for user lookups
3. ✅ **Add query metrics** - Log RU consumption per query
4. ✅ **Add pagination** - Limit result sets to reduce RU usage
5. ✅ **Plan partition key migration** - Long-term optimization (Phase 3)

---

## Related Documentation
- Full audit report: `../Query_fix`
- Azure Cosmos DB Indexing: https://learn.microsoft.com/azure/cosmos-db/index-policy
- Query optimization: https://learn.microsoft.com/azure/cosmos-db/sql/query-metrics

---

**Questions?** Check the full optimization audit in `Query_fix` or review Azure Portal metrics.
