import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from ...utils.logging_config import get_logger
from ...utils.async_utils import run_sync
from ...core.dependencies import CosmosService
from ...core.errors import QueryError, DatabaseConnectionError


logger = logging.getLogger(__name__)


class AnalyticsService:
    """Analytics service: lightweight, efficient accessors and trackers for analytics data.

    This is a trimmed and focused version of the recovered implementation optimized
    to be used as a singleton via DI.
    """

    def __init__(self, cosmos_service: CosmosService):
        self.cosmos_db = cosmos_service
        self.logger = get_logger(__name__)

        # quick availability flags to avoid repeated hasattr checks
        self._analytics_container_available = hasattr(self.cosmos_db, 'analytics_container') and self.cosmos_db.analytics_container is not None
        self._events_container_available = hasattr(self.cosmos_db, 'events_container') and self.cosmos_db.events_container is not None


    def close(self):
        """Graceful shutdown hook (no-op for now)."""
        self.logger.info("AnalyticsService.shutdown: no resources to close")

    async def track_event(self, event_type: str, user_id: str, metadata: Optional[Dict[str, Any]] = None, job_id: Optional[str] = None) -> str:
        if not event_type or not user_id:
            return ""
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "type": "event",
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "partition_key": user_id,
        }
        if job_id:
            event["job_id"] = job_id

        if not self._events_container_available:
            self.logger.warning("Events container unavailable; skipping analytics event storage")
            return ""

        try:
            # SDK create_item is synchronous; run in thread if needed by caller
            await run_sync(lambda: self.cosmos_db.events_container.create_item(body=event))
            return event_id
        except CosmosHttpResponseError as e:
            # Log specific Cosmos errors with context
            self.logger.error(
                "Failed to store analytics event in Cosmos",
                exc_info=True,
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "user_id": user_id,
                    "status_code": e.status_code,
                    "error_message": str(e)
                }
            )
            return ""
        except Exception as e:
            # Catch-all for unexpected errors
            self.logger.error(
                "Unexpected error storing analytics event",
                exc_info=True,
                extra={
                    "event_id": event_id,
                    "event_type": event_type,
                    "user_id": user_id
                }
            )
            return ""

    async def track_job_event(self, job_id: str, user_id: str, event_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        # Always write a lightweight event record
        event_meta = {**(metadata or {}), "job_id": job_id}
        event_id = await self.track_event(event_type=event_type, user_id=user_id, metadata=event_meta, job_id=job_id)

        # For compatibility with legacy analytics, also write a transcription_analytics
        # document when the event corresponds to an upload/creation or contains audio metadata.
        try:
            if self._analytics_container_available and (event_type in ("job_created", "job_uploaded") or any(k in (metadata or {}) for k in ("audio_duration_seconds", "audio_duration_minutes", "file_name", "prompt_category_id", "prompt_subcategory_id"))):
                ts_iso = datetime.now(timezone.utc).isoformat()
                ts_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
                analytics_id = f"analytics_job_{ts_ms}"

                audio_seconds = None
                audio_minutes = None
                if metadata:
                    audio_seconds = metadata.get("audio_duration_seconds") or metadata.get("audio_duration")
                    audio_minutes = metadata.get("audio_duration_minutes")

                # If only seconds provided, compute minutes
                if audio_minutes is None and audio_seconds is not None:
                    try:
                        audio_minutes = float(audio_seconds) / 60.0
                    except Exception:
                        audio_minutes = None

                analytics_doc = {
                    "id": analytics_id,
                    "type": "transcription_analytics",
                    "user_id": user_id,
                    "job_id": job_id,
                    "event_type": event_type,
                    "timestamp": ts_iso,
                    "audio_duration_minutes": float(audio_minutes) if audio_minutes is not None else None,
                    "audio_duration_seconds": float(audio_seconds) if audio_seconds is not None else None,
                    "file_name": (metadata.get("file_name") if metadata else None),
                    "file_extension": (metadata.get("file_extension") if metadata else None),
                    "prompt_category_id": (metadata.get("prompt_category_id") if metadata else None),
                    "prompt_subcategory_id": (metadata.get("prompt_subcategory_id") if metadata else None),
                    "partition_key": user_id,
                }

                # Remove keys with None to keep documents compact
                analytics_doc = {k: v for k, v in analytics_doc.items() if v is not None}

                try:
                    await run_sync(lambda: self.cosmos_db.analytics_container.create_item(body=analytics_doc))
                except CosmosHttpResponseError as e:
                    self.logger.warning(
                        "Failed to store analytics document in analytics_container",
                        extra={
                            "analytics_id": analytics_id,
                            "job_id": job_id,
                            "user_id": user_id,
                            "status_code": e.status_code
                        }
                    )
                except Exception as e:
                    self.logger.error(
                        "Unexpected error storing analytics document",
                        exc_info=True,
                        extra={"analytics_id": analytics_id, "job_id": job_id}
                    )

        except CosmosHttpResponseError as e:
            # Non-fatal; we already created the lightweight event
            self.logger.warning(
                "CosmosDB error while creating legacy analytics document",
                extra={
                    "job_id": job_id,
                    "user_id": user_id,
                    "status_code": e.status_code
                }
            )
        except Exception as e:
            # Non-fatal; we already created the lightweight event
            self.logger.error(
                "Unexpected error creating legacy analytics document",
                exc_info=True,
                extra={"job_id": job_id, "user_id": user_id}
            )

        return event_id

    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)
        minutes_total = 0.0
        jobs_count = 0
        if self._analytics_container_available:
            try:
                query = "SELECT c.audio_duration_minutes, c.audio_duration_seconds FROM c WHERE c.user_id = @user_id AND c.timestamp >= @start AND c.timestamp <= @end"
                params = [{"name": "@user_id", "value": user_id}, {"name": "@start", "value": start_dt.isoformat()}, {"name": "@end", "value": end_dt.isoformat()}]
                items = await run_sync(lambda: list(self.cosmos_db.analytics_container.query_items(query=query, parameters=params, enable_cross_partition_query=True)))
                for it in items:
                    m = it.get("audio_duration_minutes")
                    if m is None and it.get("audio_duration_seconds") is not None:
                        m = float(it.get("audio_duration_seconds")) / 60.0
                    if isinstance(m, (int, float)):
                        minutes_total += float(m)
                        jobs_count += 1
            except CosmosHttpResponseError as e:
                self.logger.warning(
                    "Failed to query analytics container for user analytics",
                    extra={
                        "user_id": user_id,
                        "days": days,
                        "status_code": e.status_code
                    }
                )
            except Exception as e:
                self.logger.error(
                    "Unexpected error querying user analytics",
                    exc_info=True,
                    extra={"user_id": user_id, "days": days}
                )

        if jobs_count == 0 and hasattr(self.cosmos_db, 'jobs_container'):
            try:
                # Optimized query: filter soft-deleted jobs at database level
                q2 = """
                    SELECT c.audio_duration_minutes, c.audio_duration_seconds 
                    FROM c 
                    WHERE c.type = 'job'
                    AND c.user_id = @user_id 
                    AND c.created_at >= @start_ms
                    AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
                """
                params2 = [{"name": "@user_id", "value": user_id}, {"name": "@start_ms", "value": int(start_dt.timestamp() * 1000)}]
                items = await run_sync(lambda: list(self.cosmos_db.jobs_container.query_items(query=q2, parameters=params2, enable_cross_partition_query=True)))
                for it in items:
                    m = it.get("audio_duration_minutes")
                    if m is None and it.get("audio_duration_seconds") is not None:
                        m = float(it.get("audio_duration_seconds")) / 60.0
                    if isinstance(m, (int, float)):
                        minutes_total += float(m)
                        jobs_count += 1
            except CosmosHttpResponseError as e:
                self.logger.warning(
                    "Failed to query jobs container for user analytics fallback",
                    extra={
                        "user_id": user_id,
                        "days": days,
                        "status_code": e.status_code
                    }
                )
            except Exception as e:
                self.logger.error(
                    "Unexpected error in jobs container fallback query",
                    exc_info=True,
                    extra={"user_id": user_id, "days": days}
                )

        avg = (minutes_total / jobs_count) if jobs_count > 0 else 0.0
        return {
            "user_id": user_id,
            "period_days": days,
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "analytics": {"transcription_stats": {"total_minutes": float(minutes_total), "total_jobs": int(jobs_count), "average_job_duration": float(avg)}}
        }

    async def get_user_minutes_records(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)
        records: List[Dict[str, Any]] = []
        # Query only the analytics container for transcription analytics records. Do not
        # fall back to job documents; requirement: "Should pull analytics data from the analytics container, not the jobs."
        if self._analytics_container_available:
            try:
                query = (
                    "SELECT c.job_id, c.timestamp, c.event_type, c.audio_duration_minutes, c.audio_duration_seconds, c.file_name, c.prompt_category_id, c.prompt_subcategory_id "
                    "FROM c WHERE c.user_id = @user_id AND c.timestamp >= @start_date AND c.type = 'transcription_analytics' "
                    "AND (IS_DEFINED(c.audio_duration_minutes) OR IS_DEFINED(c.audio_duration_seconds))"
                )
                params = [
                    {"name": "@user_id", "value": user_id},
                    {"name": "@start_date", "value": start_dt.isoformat()},
                ]
                for it in self.cosmos_db.analytics_container.query_items(
                    query=query, parameters=params, enable_cross_partition_query=True
                ):
                    minutes = it.get("audio_duration_minutes")
                    if minutes is None and it.get("audio_duration_seconds") is not None:
                        try:
                            minutes = float(it.get("audio_duration_seconds")) / 60.0
                        except Exception:
                            minutes = None
                    if minutes is None:
                        continue
                    records.append(
                        {
                            "job_id": it.get("job_id"),
                            "timestamp": it.get("timestamp"),
                            "event_type": it.get("event_type"),
                            "audio_duration_minutes": float(minutes),
                            "file_name": it.get("file_name"),
                            "prompt_category_id": it.get("prompt_category_id"),
                            "prompt_subcategory_id": it.get("prompt_subcategory_id"),
                        }
                    )
            except CosmosHttpResponseError as e:
                # If analytics container query fails, return empty records (no jobs fallback)
                self.logger.warning(
                    "Failed to query analytics container for user minutes records",
                    extra={
                        "user_id": user_id,
                        "days": days,
                        "status_code": e.status_code
                    }
                )
            except Exception as e:
                self.logger.error(
                    "Unexpected error querying user minutes records",
                    exc_info=True,
                    extra={"user_id": user_id, "days": days}
                )

        total_minutes = sum(r.get("audio_duration_minutes", 0.0) for r in records)
        records.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
        return {"user_id": user_id, "period_days": days, "start_date": start_dt.isoformat(), "end_date": end_dt.isoformat(), "total_minutes": total_minutes, "total_records": len(records), "records": records}

    async def get_system_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Return system-level analytics including per-job records for the last `days` days.

        This aggregates `transcription_analytics` documents where available, and falls
        back to job documents with duration metadata where necessary.
        """
        end_dt = datetime.now(timezone.utc)
        start_dt = end_dt - timedelta(days=days)
        records: List[Dict[str, Any]] = []
        total_minutes = 0.0
        total_jobs = 0

        try:
            if self._analytics_container_available:
                query = ("SELECT c.id, c.job_id, c.user_id, c.timestamp, c.event_type, c.audio_duration_minutes, c.audio_duration_seconds, c.file_name "
                         "FROM c WHERE c.timestamp >= @start AND c.timestamp <= @end AND c.type = 'transcription_analytics'")
                params = [{"name": "@start", "value": start_dt.isoformat()}, {"name": "@end", "value": end_dt.isoformat()}]
                for it in self.cosmos_db.analytics_container.query_items(query=query, parameters=params, enable_cross_partition_query=True):
                    minutes = it.get('audio_duration_minutes')
                    if minutes is None and it.get('audio_duration_seconds') is not None:
                        try:
                            minutes = float(it.get('audio_duration_seconds')) / 60.0
                        except Exception:
                            minutes = None
                    if minutes is None:
                        continue
                    record = {
                        'id': it.get('id'),
                        'job_id': it.get('job_id'),
                        'user_id': it.get('user_id'),
                        'timestamp': it.get('timestamp'),
                        'audio_duration_minutes': float(minutes),
                        'file_name': it.get('file_name')
                    }
                    records.append(record)
                    total_minutes += float(minutes)
                    total_jobs += 1
        except CosmosHttpResponseError as e:
            # Non-fatal: we'll try fallback below
            self.logger.warning(
                "Failed to query analytics container for system analytics",
                extra={
                    "days": days,
                    "status_code": e.status_code
                }
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error querying system analytics",
                exc_info=True,
                extra={"days": days}
            )

        # Fallback to jobs container if we found no records
        if not records and hasattr(self.cosmos_db, 'jobs_container'):
            try:
                # Optimized query: filter soft-deleted jobs at database level
                job_q = """
                    SELECT c.id, c.user_id, c.created_at, c.audio_duration_minutes, c.audio_duration_seconds, c.file_name 
                    FROM c 
                    WHERE c.type = 'job' 
                    AND c.created_at >= @start_ms
                    AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
                """
                params2 = [{"name": "@start_ms", "value": int(start_dt.timestamp() * 1000)}]
                for it in self.cosmos_db.jobs_container.query_items(query=job_q, parameters=params2, enable_cross_partition_query=True):
                    minutes = it.get('audio_duration_minutes')
                    if minutes is None and it.get('audio_duration_seconds') is not None:
                        try:
                            minutes = float(it.get('audio_duration_seconds')) / 60.0
                        except Exception:
                            minutes = None
                    if minutes is None:
                        continue
                    ts_ms = it.get('created_at')
                    ts_iso = (datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat() if isinstance(ts_ms, (int, float)) else None)
                    record = {
                        'id': it.get('id'),
                        'job_id': it.get('id'),
                        'user_id': it.get('user_id'),
                        'timestamp': ts_iso,
                        'audio_duration_minutes': float(minutes),
                        'file_name': it.get('file_name')
                    }
                    records.append(record)
                    total_minutes += float(minutes)
                    total_jobs += 1
            except CosmosHttpResponseError as e:
                self.logger.warning(
                    "Failed to query jobs container for system analytics fallback",
                    extra={
                        "days": days,
                        "status_code": e.status_code
                    }
                )
            except Exception as e:
                self.logger.error(
                    "Unexpected error in jobs container fallback for system analytics",
                    exc_info=True,
                    extra={"days": days}
                )

        # Sort records ascending by timestamp
        records.sort(key=lambda r: r.get('timestamp') or "")

        # Calculate active users by scanning the sessions container for recent heartbeats
        active_user_set = set()
        try:
            if hasattr(self.cosmos_db, 'sessions_container') and self.cosmos_db.sessions_container is not None:
                sess_query = "SELECT c.user_id, c.last_activity, c.last_heartbeat, c.status FROM c WHERE (IS_DEFINED(c.last_activity) AND c.last_activity >= @start) OR (IS_DEFINED(c.last_heartbeat) AND c.last_heartbeat >= @start)"
                sess_params = [{"name": "@start", "value": start_dt.isoformat()}]
                for s in self.cosmos_db.sessions_container.query_items(query=sess_query, parameters=sess_params, enable_cross_partition_query=True):
                    try:
                        uid = s.get('user_id')
                        status = s.get('status')
                        if uid and (status is None or str(status).lower() == 'active'):
                            active_user_set.add(uid)
                    except Exception as e:
                        self.logger.debug(
                            "Failed to process session record for active user",
                            extra={"error": str(e)}
                        )
                        continue
        except CosmosHttpResponseError as e:
            # Non-fatal; leave active_user_set empty
            self.logger.warning(
                "Failed to query sessions for active users",
                extra={
                    "days": days,
                    "status_code": e.status_code
                }
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error querying active users",
                exc_info=True,
                extra={"days": days}
            )

        active_users = len(active_user_set)

        # Derive peak active users per day (approx) by bucketing heartbeat timestamps if available
        peak_active_users = active_users
        try:
            # Re-query sessions for finer buckets only if container present
            if hasattr(self.cosmos_db, 'sessions_container') and self.cosmos_db.sessions_container is not None:
                bucket_counts = {}
                sess_query2 = "SELECT c.user_id, c.last_activity, c.last_heartbeat FROM c WHERE ((IS_DEFINED(c.last_activity) AND c.last_activity >= @start AND c.last_activity <= @end) OR (IS_DEFINED(c.last_heartbeat) AND c.last_heartbeat >= @start AND c.last_heartbeat <= @end))"
                sess_params2 = [{"name": "@start", "value": start_dt.isoformat()}, {"name": "@end", "value": end_dt.isoformat()}]
                for s in self.cosmos_db.sessions_container.query_items(query=sess_query2, parameters=sess_params2, enable_cross_partition_query=True):
                    try:
                        hb = s.get('last_activity') or s.get('last_heartbeat')
                        uid = s.get('user_id')
                        if not hb or not uid:
                            continue
                        # Normalize to hour bucket for rough concurrency approximation
                        from datetime import datetime as _dt
                        try:
                            ts = _dt.fromisoformat(hb.replace('Z','+00:00'))
                        except Exception:
                            continue
                        bucket = ts.strftime('%Y-%m-%dT%H:00')
                        bucket_counts.setdefault(bucket, set()).add(uid)
                    except Exception as e:
                        self.logger.debug(
                            "Failed to process session bucket for peak active users",
                            extra={"error": str(e)}
                        )
                        continue
                if bucket_counts:
                    peak_active_users = max(len(v) for v in bucket_counts.values())
        except CosmosHttpResponseError as e:
            self.logger.warning(
                "Failed to calculate peak active users",
                extra={
                    "days": days,
                    "status_code": e.status_code
                }
            )
        except Exception as e:
            self.logger.error(
                "Unexpected error calculating peak active users",
                exc_info=True,
                extra={"days": days}
            )

        return {
            'period_days': days,
            'start_date': start_dt.isoformat(),
            'end_date': end_dt.isoformat(),
            'total_minutes': total_minutes,
            'total_jobs': total_jobs,
            'active_users': active_users,
            'peak_active_users': peak_active_users,
            'analytics': {
                'records': records,
                'total_minutes': total_minutes,
                'total_jobs': total_jobs,
                'active_users': active_users,
                'peak_active_users': peak_active_users
            }
        }

    async def get_recent_jobs(self, limit: int = 10, prompt_id: Optional[str] = None) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not hasattr(self.cosmos_db, 'analytics_container'):
            return results
        try:
            # Optimized query with database-level LIMIT and soft-delete filter
            query = f"""
                SELECT * FROM c 
                WHERE c.type = 'job'
                AND (NOT IS_DEFINED(c.deleted) OR c.deleted = false)
            """
            params = []
            if prompt_id:
                query += " AND c.prompt_id = @prompt_id"
                params.append({"name": "@prompt_id", "value": prompt_id})
            query += f" ORDER BY c.created_at DESC OFFSET 0 LIMIT {limit}"
            items = await run_sync(lambda: list(self.cosmos_db.analytics_container.query_items(query=query, parameters=params, enable_cross_partition_query=True)))
            for it in items:
                results.append(it)
        except CosmosHttpResponseError as e:
            self.logger.warning(
                "Failed to query recent jobs",
                extra={
                    "limit": limit,
                    "prompt_id": prompt_id,
                    "status_code": e.status_code
                }
            )
            return []
        except Exception as e:
            self.logger.error(
                "Unexpected error querying recent jobs",
                exc_info=True,
                extra={"limit": limit, "prompt_id": prompt_id}
            )
            return []
        return results
