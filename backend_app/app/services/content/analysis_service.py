import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from azure.cosmos.exceptions import CosmosHttpResponseError
import random
from collections import defaultdict

# Use the improved logging utility
from app.utils.logging_config import get_logger, log_completion, log_error_with_context
from datetime import datetime, timezone, timedelta


class AnalyticsService:
    """Service for tracking and aggregating user analytics data from the analytics container"""
    
    def __init__(self, cosmos_db):
        self.cosmos_db = cosmos_db
        self.logger = get_logger(__name__)
        
        # Log initialization
        self.logger.info("📊 AnalyticsService initialized (using analytics container as source of truth)")
        
        # Verify containers on initialization
        if hasattr(cosmos_db, 'analytics_container') and cosmos_db.analytics_container is not None:
            self.logger.info("✓ Analytics container is available for analytics aggregation")
            self._analytics_container_available = True
        else:
            self.logger.warning("⚠️ Analytics container is not available - analytics aggregation may fail")
            self._analytics_container_available = False
            
        if hasattr(cosmos_db, 'sessions_container') and cosmos_db.sessions_container is not None:
            self.logger.info("✓ Sessions container is available for session analytics")
            self._sessions_container_available = True
        else:
            self.logger.error("❌ Sessions container is not available - session analytics will fail")
            self._sessions_container_available = False
            
        if hasattr(cosmos_db, 'events_container') and cosmos_db.events_container is not None:
            self.logger.info("✓ Events container is available for event tracking")
            self._events_container_available = True
        else:
            self.logger.warning("⚠️ Events container is not available - event tracking may fail")
            self._events_container_available = False

    async def track_event(
        self, 
        event_type: str, 
        user_id: str, 
        metadata: Optional[Dict[str, Any]] = None,
        job_id: Optional[str] = None
    ) -> str:
        """
        Track analytics events
        
        Args:
            event_type: Type of event (job_created, job_completed, user_login, etc.)
            user_id: ID of the user performing the action
            metadata: Additional event data
            job_id: Optional job ID if event is job-related
            
        Returns:
            Event ID
        """
        try:
            # Validate required parameters
            if not event_type or not user_id:
                self.logger.error(f"Missing required parameters: event_type={event_type}, user_id={user_id}")
                return ""
            
            event_id = str(uuid.uuid4())
            
            event_data = {
                "id": event_id,
                "type": "event",
                "event_type": event_type,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
                "partition_key": user_id  # Partition by user for efficient queries
            }
            
            if job_id:
                event_data["job_id"] = job_id
            
            # Check if events container exists
            if not hasattr(self.cosmos_db, 'events_container') or self.cosmos_db.events_container is None:
                self.logger.error("Events container is not initialized")
                return ""
            
            # Store event in events container
            result = self.cosmos_db.events_container.create_item(body=event_data)
            
            self.logger.info(f"✓ Analytics event tracked successfully: {event_type} for user {user_id} with event_id {event_id}")
            
            # Log metadata for debugging
            if metadata and event_type in ['job_uploaded', 'job_completed']:
                audio_mins = metadata.get('audio_duration_minutes', 'N/A')
                self.logger.info(f"  Audio duration logged: {audio_mins} minutes")
            
            return event_id
            
        except CosmosHttpResponseError as e:
            self.logger.error(f"Cosmos DB error tracking analytics event: {e.status_code} - {e.message}")
            self.logger.error(f"  Event details: {event_type}, user: {user_id}, metadata: {metadata}")
            return ""
        except Exception as e:
            self.logger.error(f"Unexpected error tracking analytics event: {str(e)}")
            self.logger.error(f"  Event details: {event_type}, user: {user_id}, metadata: {metadata}")
            # Don't fail the main operation if analytics fails
            return ""

    async def track_job_event(
        self, 
        job_id: str, 
        user_id: str, 
        event_type: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track job-specific events with additional metadata
        
        Args:
            job_id: ID of the job
            user_id: ID of the user
            event_type: job_created, job_started, job_completed, job_failed, etc.
            metadata: Job-specific data (duration, file_size, transcription_method, etc.)
        """
        job_metadata = {
            "job_id": job_id,
            **(metadata or {})
        }
        
        return await self.track_event(
            event_type=event_type,
            user_id=user_id,
            job_id=job_id,
            metadata=job_metadata
        )

    async def get_active_users(self, minutes: int = 5) -> List[str]:
        """
        Get users who were active in the last N minutes based on session heartbeats
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            List of active user IDs
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
            
            query = """
            SELECT DISTINCT c.user_id
            FROM c 
            WHERE c.type = 'session' 
            AND c.status = 'active'
            AND c.last_heartbeat >= @cutoff_time
            """
            
            parameters = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
            
            active_users = []
            for item in self.cosmos_db.sessions_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ):
                active_users.append(item["user_id"])
            
            return list(set(active_users))  # Remove duplicates
            
        except Exception as e:
            self.logger.error(f"Error getting active users: {str(e)}")
            return []

    async def get_user_session_duration(self, user_id: str, days: int = 1) -> float:
        """
        Calculate total session duration for a user in the last N days using new session schema
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Total session duration in minutes
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = """
            SELECT c.id, c.created_at, c.last_heartbeat, c.status, c.session_duration_seconds
            FROM c 
            WHERE c.type = 'session' 
            AND c.user_id = @user_id
            AND c.created_at >= @cutoff_time
            ORDER BY c.created_at ASC
            """
            
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@cutoff_time", "value": cutoff_time.isoformat()}
            ]
            
            total_duration_minutes = 0.0
            
            for session in self.cosmos_db.sessions_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=user_id
            ):
                try:
                    # For completed sessions with duration already calculated
                    if session.get("session_duration_seconds"):
                        total_duration_minutes += session["session_duration_seconds"] / 60.0
                    else:
                        # For active sessions, calculate duration from created_at to last_heartbeat
                        created_at = datetime.fromisoformat(session["created_at"].replace('Z', '+00:00'))
                        last_heartbeat = datetime.fromisoformat(session["last_heartbeat"].replace('Z', '+00:00'))
                        duration_seconds = (last_heartbeat - created_at).total_seconds()
                        total_duration_minutes += duration_seconds / 60.0
                        
                except Exception as parse_error:
                    self.logger.warning(f"Error parsing session duration for session {session.get('id')}: {parse_error}")
                    continue
            
            return total_duration_minutes
            
        except Exception as e:
            self.logger.error(f"Error calculating user session duration: {str(e)}")
            return 0.0
            
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@cutoff_time", "value": cutoff_time.isoformat()}
            ]
            
            session_events = []
            for item in self.cosmos_db.sessions_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ):
                session_events.append(item)
            
            # Calculate session durations with idle detection
            idle_threshold = timedelta(minutes=5)
            total = timedelta(0)
            start_ts: Optional[datetime] = None
            last_active: Optional[datetime] = None
            for event in session_events:
                ts = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                et = event.get("event_type")
                if et == "session_start":
                    start_ts = ts
                    last_active = ts
                elif et in ("session_heartbeat", "session_page_view") and start_ts:
                    if last_active and ts - last_active > idle_threshold:
                        total += (last_active - start_ts)
                        start_ts = ts
                    last_active = ts
                elif et == "session_end" and start_ts:
                    end_ts = ts
                    if last_active and end_ts - last_active > idle_threshold:
                        end_ts = last_active
                    total += (end_ts - start_ts)
                    start_ts = None
                    last_active = None

            if start_ts:
                end_ts = last_active or datetime.now(timezone.utc)
                total += (end_ts - start_ts)

            return total.total_seconds() / 60.0
            
        except Exception as e:
            self.logger.error(f"Error calculating session duration: {str(e)}")
            return 0.0

    async def get_user_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get aggregated analytics for a specific user from analytics container
        
        Args:
            user_id: ID of the user
            days: Number of days to look back
            
        Returns:
            Dictionary containing user analytics
        """
        try:
            # Calculate date range
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=days)

            # Aggregate transcription minutes from analytics, fallback to jobs
            minutes_total = 0.0
            jobs_count = 0

            query = (
                "SELECT c.audio_duration_minutes, c.audio_duration_seconds FROM c WHERE c.user_id = @user_id "
                "AND c.timestamp >= @start AND c.timestamp <= @end"
            )
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start", "value": start_dt.isoformat()},
                {"name": "@end", "value": end_dt.isoformat()},
            ]
            try:
                for item in self.cosmos_db.analytics_container.query_items(
                    query=query, parameters=params, enable_cross_partition_query=True
                ):
                    m = item.get("audio_duration_minutes")
                    if m is None and item.get("audio_duration_seconds") is not None:
                        m = float(item["audio_duration_seconds"]) / 60.0
                    if isinstance(m, (int, float)):
                        minutes_total += float(m)
                        jobs_count += 1
            except Exception as qe:
                self.logger.warning(f"analytics_container query failed, will fallback to jobs: {qe}")

            if jobs_count == 0:
                q2 = (
                    "SELECT c.audio_duration_minutes, c.audio_duration_seconds FROM c WHERE c.user_id = @user_id "
                    "AND c.created_at >= @start_ms"
                )
                params2 = [
                    {"name": "@user_id", "value": user_id},
                    {"name": "@start_ms", "value": int(start_dt.timestamp() * 1000)},
                ]
                try:
                    for it in self.cosmos_db.jobs_container.query_items(
                        query=q2, parameters=params2, enable_cross_partition_query=True
                    ):
                        m = it.get("audio_duration_minutes")
                        if m is None and it.get("audio_duration_seconds") is not None:
                            m = float(it["audio_duration_seconds"]) / 60.0
                        if isinstance(m, (int, float)):
                            minutes_total += float(m)
                            jobs_count += 1
                except Exception as jf:
                    self.logger.warning(f"jobs_container fallback failed: {jf}")

            avg = (minutes_total / jobs_count) if jobs_count > 0 else 0.0
            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "analytics": {
                    "transcription_stats": {
                        "total_minutes": float(minutes_total),
                        "total_jobs": int(jobs_count),
                        "average_job_duration": float(avg),
                    }
                },
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user analytics for {user_id}: {str(e)}")
            # Fallback path: attempt to compute analytics from events/jobs directly
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Try to get events from analytics container first
            analytics = None
            try:
                # Query events for the user in the date range
                query = """
                    SELECT * FROM c 
                    WHERE c.user_id = @user_id 
                    AND c.timestamp >= @start_date 
                    AND c.timestamp <= @end_date
                    ORDER BY c.timestamp DESC
                """
                
                parameters = [
                    {"name": "@user_id", "value": user_id},
                    {"name": "@start_date", "value": start_date.isoformat()},
                    {"name": "@end_date", "value": end_date.isoformat()}
                ]
                
                events = list(self.cosmos_db.events_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=False,
                    partition_key=user_id
                ))
                
                # If we have events, use them for analytics
                if events:
                    analytics = await self._aggregate_user_events(events)
                    self.logger.info(f"Found {len(events)} analytics events for user {user_id}")
                else:
                    self.logger.info(f"No analytics events found for user {user_id}, falling back to jobs data")
                    
            except Exception as events_error:
                self.logger.warning(f"Error querying analytics events for user {user_id}: {str(events_error)}")
            
            # Fallback: Calculate analytics directly from jobs collection if no events found
            if not analytics:
                self.logger.info(f"No analytics from events, using jobs data fallback for user {user_id}")
                analytics = await self._get_user_analytics_from_jobs(user_id, start_date, end_date)
            else:
                self.logger.info(f"Using analytics from {len(events) if 'events' in locals() else 0} events for user {user_id}")
                # Log the minutes found for debugging
                total_mins = analytics.get("transcription_stats", {}).get("total_minutes", 0)
                self.logger.info(f"  Total minutes from events: {total_mins}")
            
            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "analytics": analytics or {
                    "transcription_stats": {"total_minutes": 0.0, "total_jobs": 0, "average_job_duration": 0.0},
                    "activity_stats": {"login_count": 0, "jobs_created": 0, "last_activity": None},
                    "usage_patterns": {"most_active_hours": [], "most_used_transcription_method": None, "file_upload_count": 0, "text_input_count": 0},
                },
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user analytics: {str(e)}")
            # Return a valid response structure even on error
            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": start_date.isoformat() if 'start_date' in locals() and start_date else datetime.now(timezone.utc).isoformat(),
                "end_date": end_date.isoformat() if 'end_date' in locals() and end_date else datetime.now(timezone.utc).isoformat(),
                "analytics": {
                    "error": str(e),
                    "transcription_stats": {"total_minutes": 0.0, "total_jobs": 0, "average_job_duration": 0.0},
                    "activity_stats": {"login_count": 0, "jobs_created": 0, "last_activity": None},
                    "usage_patterns": {"most_active_hours": [], "most_used_transcription_method": None, "file_upload_count": 0, "text_input_count": 0},
                },
            }

    async def _aggregate_user_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate raw events into analytics summary"""
        
        analytics = {
            "transcription_stats": {
                "total_minutes": 0.0,
                "total_jobs": 0,
                "average_job_duration": 0.0
            },
            "activity_stats": {
                "login_count": 0,
                "jobs_created": 0,
                "last_activity": None
            },
            "usage_patterns": {
                "most_active_hours": [],
                "most_used_transcription_method": None,
                "file_upload_count": 0,
                "text_input_count": 0
            }
        }
        
        if not events:
            return analytics
        
        transcription_durations = []
        hourly_activity = {}
        transcription_methods = {}
        
        for event in events:
            event_type = event.get("event_type", "")
            metadata = event.get("metadata", {})
            timestamp = event.get("timestamp", "")
            
            # Parse timestamp for hourly patterns
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    hour = dt.hour
                    hourly_activity[hour] = hourly_activity.get(hour, 0) + 1
                except:
                    pass
            
            # Update last activity
            if not analytics["activity_stats"]["last_activity"] or timestamp > analytics["activity_stats"]["last_activity"]:
                analytics["activity_stats"]["last_activity"] = timestamp
            
            # Count different event types
            if event_type == "user_login":
                analytics["activity_stats"]["login_count"] += 1
            elif event_type == "job_created":
                analytics["activity_stats"]["jobs_created"] += 1
                analytics["transcription_stats"]["total_jobs"] += 1
                
                # Track input method
                if metadata.get("has_file"):
                    analytics["usage_patterns"]["file_upload_count"] += 1
                else:
                    analytics["usage_patterns"]["text_input_count"] += 1
                    
            elif event_type == "job_uploaded":
                # Track audio duration from uploaded files
                if metadata.get("audio_duration_minutes"):
                    audio_minutes = float(metadata["audio_duration_minutes"])
                    analytics["transcription_stats"]["total_minutes"] += audio_minutes
                    transcription_durations.append(audio_minutes)
                    
                # Track transcription methods
                transcription_method = metadata.get("transcription_method")
                if transcription_method:
                    transcription_methods[transcription_method] = transcription_methods.get(transcription_method, 0) + 1
                    
            elif event_type == "job_completed":
                # Track audio duration if available (fallback for older events)
                if metadata.get("audio_duration_minutes"):
                    audio_minutes = float(metadata["audio_duration_minutes"])
                    analytics["transcription_stats"]["total_minutes"] += audio_minutes
                    transcription_durations.append(audio_minutes)
                elif metadata.get("duration_seconds"):
                    # Fallback to processing duration if audio duration not available
                    duration_minutes = metadata["duration_seconds"] / 60.0
                    analytics["transcription_stats"]["total_minutes"] += duration_minutes
                    transcription_durations.append(duration_minutes)
                    
                # Track transcription methods
                transcription_method = metadata.get("transcription_method")
                if transcription_method:
                    transcription_methods[transcription_method] = transcription_methods.get(transcription_method, 0) + 1
        
        # Calculate derived metrics
        total_jobs = analytics["transcription_stats"]["total_jobs"]
        
        if transcription_durations:
            analytics["transcription_stats"]["average_job_duration"] = sum(transcription_durations) / len(transcription_durations)
        
        # Find most active hours (top 3)
        if hourly_activity:
            sorted_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)
            analytics["usage_patterns"]["most_active_hours"] = [hour for hour, count in sorted_hours[:3]]
        
        # Find most used transcription method
        if transcription_methods:
            most_used = max(transcription_methods.items(), key=lambda x: x[1])
            analytics["usage_patterns"]["most_used_transcription_method"] = most_used[0]
        
        return analytics

    async def get_recent_jobs(self, limit: int = 10, prompt_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent jobs for analytics dashboard, optionally filtered by prompt_id
        """
        try:
            query = "SELECT * FROM c WHERE c.type = 'job'"
            parameters = []
            if prompt_id:
                query += " AND c.prompt_id = @prompt_id"
                parameters.append({"name": "@prompt_id", "value": prompt_id})
            query += " ORDER BY c.created_at DESC"
            jobs = []
            for item in self.cosmos_db.analytics_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ):
                jobs.append(item)
                if len(jobs) >= limit:
                    break
            return jobs
        except Exception as e:
            self.logger.error(f"Error fetching recent jobs: {str(e)}")
            return []

    async def _get_user_analytics_records(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch per-user analytics records from analytics container within a time range.

        Returns a list of dicts with keys: job_id, timestamp (ISO), event_type, audio_duration_minutes.
        """
        records: List[Dict[str, Any]] = []
        try:
            query = (
                "SELECT c.job_id, c.timestamp, c.event_type, c.audio_duration_minutes, c.audio_duration_seconds "
                "FROM c WHERE c.type = 'transcription_analytics' AND c.user_id = @user_id "
                "AND c.timestamp >= @start AND c.timestamp <= @end"
            )
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start", "value": start_date.isoformat()},
                {"name": "@end", "value": end_date.isoformat()},
            ]
            for item in self.cosmos_db.analytics_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            ):
                minutes = item.get("audio_duration_minutes")
                if minutes is None and item.get("audio_duration_seconds") is not None:
                    minutes = float(item["audio_duration_seconds"]) / 60.0
                # Keep records even if minutes missing; aggregation will handle None
                records.append(
                    {
                        "job_id": item.get("job_id"),
                        "timestamp": item.get("timestamp"),
                        "event_type": item.get("event_type"),
                        "audio_duration_minutes": float(minutes) if minutes is not None else None,
                    }
                )
        except Exception as e:
            self.logger.warning(f"_get_user_analytics_records failed: {e}")
        return records

    async def _get_user_session_events(self, user_id: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Fetch session-related events for a user in date range from sessions container.

        Reads from voice_user_sessions (sessions_container) and returns basic fields.
        """
        events: List[Dict[str, Any]] = []
        try:
            query = (
                "SELECT c.event_type, c.timestamp FROM c WHERE c.user_id = @user_id "
                "AND c.timestamp >= @start AND c.timestamp <= @end"
            )
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start", "value": start_date.isoformat()},
                {"name": "@end", "value": end_date.isoformat()},
            ]
            container = getattr(self.cosmos_db, "sessions_container", None) or getattr(self.cosmos_db, "events_container", None)
            if container is None:
                return events
            for item in container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            ):
                events.append(item)
        except Exception as e:
            self.logger.warning(f"_get_user_session_events failed: {e}")
        return events

    async def _aggregate_user_analytics_data(
        self,
        analytics_records: List[Dict[str, Any]],
        session_events: List[Dict[str, Any]],
        start_date: datetime,
        end_date: datetime,
        days: int,
    ) -> Dict[str, Any]:
        """Aggregate analytics and session data into the public response shape."""
        try:
            # Minutes and jobs
            minutes_list: List[float] = [
                float(r["audio_duration_minutes"]) for r in analytics_records if r.get("audio_duration_minutes") is not None
            ]
            total_minutes = sum(minutes_list) if minutes_list else 0.0
            # Count unique jobs if present; else fall back to count of records
            job_ids = [r.get("job_id") for r in analytics_records if r.get("job_id")]
            total_jobs = len(set(job_ids)) if job_ids else len(analytics_records)
            avg_job_duration = (total_minutes / total_jobs) if total_jobs > 0 else 0.0

            # Session stats
            login_count = sum(1 for e in session_events if e.get("event_type") in ("user_login", "session_start"))
            last_activity_candidates: List[str] = [
                e.get("timestamp") for e in session_events if e.get("timestamp")
            ] + [r.get("timestamp") for r in analytics_records if r.get("timestamp")]
            last_activity = max(last_activity_candidates) if last_activity_candidates else None

            return {
                "transcription_stats": {
                    "total_minutes": float(total_minutes),
                    "total_jobs": int(total_jobs),
                    "average_job_duration": float(avg_job_duration),
                },
                "activity_stats": {
                    "login_count": int(login_count) if login_count is not None else 0,
                    "jobs_created": int(total_jobs) if total_jobs is not None else 0,
                    "last_activity": last_activity if last_activity is not None else None,
                },
                "usage_patterns": {
                    "most_active_hours": [],
                    "most_used_transcription_method": None,
                    "file_upload_count": 0,
                    "text_input_count": 0,
                },
            }
        except Exception as e:
            self.logger.warning(f"_aggregate_user_analytics_data failed: {e}")
            return {
                "transcription_stats": {
                    "total_minutes": 0.0,
                    "total_jobs": 0,
                    "average_job_duration": 0.0,
                },
                "activity_stats": {
                    "login_count": 0,
                    "jobs_created": 0,
                    "last_activity": None,
                },
                "usage_patterns": {
                    "most_active_hours": [],
                    "most_used_transcription_method": None,
                    "file_upload_count": 0,
                    "text_input_count": 0,
                },
            }

    async def _get_user_analytics_from_jobs(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Fallback: compute analytics directly from voice_jobs container for a user and date range."""
        try:
            query = (
                "SELECT c.id, c.created_at, c.audio_duration_minutes, c.audio_duration_seconds "
                "FROM c WHERE c.type = 'job' AND c.user_id = @user_id AND c.created_at >= @start_ms AND c.created_at <= @end_ms"
            )
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start_ms", "value": int(start_date.timestamp() * 1000)},
                {"name": "@end_ms", "value": int(end_date.timestamp() * 1000)},
            ]
            minutes_list: List[float] = []
            count = 0
            for item in self.cosmos_db.jobs_container.query_items(
                query=query, parameters=params, enable_cross_partition_query=True
            ):
                count += 1
                minutes = item.get("audio_duration_minutes")
                if minutes is None and item.get("audio_duration_seconds") is not None:
                    minutes = float(item["audio_duration_seconds"]) / 60.0
                if minutes is not None:
                    minutes_list.append(float(minutes))

            total_minutes = sum(minutes_list) if minutes_list else 0.0
            avg = (total_minutes / count) if count > 0 else 0.0
            return {
                "transcription_stats": {
                    "total_minutes": float(total_minutes),
                    "total_jobs": int(count),
                    "average_job_duration": float(avg),
                },
                "activity_stats": {
                    "login_count": 0,
                    "jobs_created": int(count),
                    "last_activity": None,
                },
                "usage_patterns": {
                    "most_active_hours": [],
                    "most_used_transcription_method": None,
                    "file_upload_count": 0,
                    "text_input_count": 0,
                },
            }
        except Exception as e:
            self.logger.error(f"_get_user_analytics_from_jobs failed: {e}")
            return {
                "transcription_stats": {
                    "total_minutes": 0.0,
                    "total_jobs": 0,
                    "average_job_duration": 0.0,
                },
                "activity_stats": {
                    "login_count": 0,
                    "jobs_created": 0,
                    "last_activity": None,
                },
                "usage_patterns": {
                    "most_active_hours": [],
                    "most_used_transcription_method": None,
                    "file_upload_count": 0,
                    "text_input_count": 0,
                },
            }

    async def get_user_minutes_records(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Return per-record minutes for a user within the last N days.

        Aggregates from analytics_container (event_type job_uploaded/job_completed) and
        falls back to jobs data when needed.
        """
        try:
            end_dt = datetime.now(timezone.utc)
            start_dt = end_dt - timedelta(days=days)

            # First, try analytics_container for detailed per-job records
            query = (
                "SELECT c.job_id, c.timestamp, c.event_type, c.audio_duration_minutes, c.file_name, "
                "c.prompt_category_id, c.prompt_subcategory_id "
                "FROM c WHERE c.user_id = @user_id AND c.timestamp >= @start_date "
                "AND c.type = 'transcription_analytics' AND (IS_DEFINED(c.audio_duration_minutes) OR IS_DEFINED(c.audio_duration_seconds))"
            )
            params = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start_date", "value": start_dt.isoformat()},
            ]

            records: List[Dict[str, Any]] = []
            try:
                for item in self.cosmos_db.analytics_container.query_items(
                    query=query, parameters=params, enable_cross_partition_query=True
                ):
                    minutes = item.get("audio_duration_minutes")
                    if minutes is None and item.get("audio_duration_seconds") is not None:
                        minutes = float(item["audio_duration_seconds"]) / 60.0
                    if minutes is None:
                        continue
                    records.append(
                        {
                            "job_id": item.get("job_id"),
                            "timestamp": item.get("timestamp"),
                            "event_type": item.get("event_type"),
                            "audio_duration_minutes": float(minutes),
                            "file_name": item.get("file_name"),
                            "prompt_category_id": item.get("prompt_category_id"),
                            "prompt_subcategory_id": item.get("prompt_subcategory_id"),
                        }
                    )
            except Exception as e:
                self.logger.warning(f"Analytics container query failed for user minutes: {str(e)}")

            # Fallback: inspect jobs in analytics_container (type='job') for audio_duration fields
            if not records:
                job_query = (
                    "SELECT c.id, c.created_at, c.audio_duration_minutes, c.audio_duration_seconds "
                    "FROM c WHERE c.type = 'job' AND c.user_id = @user_id AND c.created_at >= @start_ms"
                )
                params2 = [
                    {"name": "@user_id", "value": user_id},
                    {"name": "@start_ms", "value": int(start_dt.timestamp() * 1000)},
                ]
                try:
                    for item in self.cosmos_db.analytics_container.query_items(
                        query=job_query, parameters=params2, enable_cross_partition_query=True
                    ):
                        minutes = item.get("audio_duration_minutes")
                        if minutes is None and item.get("audio_duration_seconds") is not None:
                            minutes = float(item["audio_duration_seconds"]) / 60.0
                        if minutes is None:
                            continue
                        ts_ms = item.get("created_at")
                        ts_iso = (
                            datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
                            if isinstance(ts_ms, (int, float))
                            else None
                        )
                        records.append(
                            {
                                "job_id": item.get("id"),
                                "timestamp": ts_iso,
                                "event_type": "job_created",
                                "audio_duration_minutes": float(minutes),
                            }
                        )
                except Exception as e:
                    self.logger.warning(f"Jobs fallback query failed for user minutes: {str(e)}")

            # Aggregate totals
            total_minutes = sum(r.get("audio_duration_minutes", 0.0) for r in records)
            # Sort by timestamp descending
            records.sort(key=lambda r: r.get("timestamp") or "", reverse=True)

            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": start_dt.isoformat(),
                "end_date": end_dt.isoformat(),
                "total_minutes": total_minutes,
                "total_records": len(records),
                "records": records,
            }
        except Exception as e:
            self.logger.error(f"Error getting user minutes records: {str(e)}")
            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": None,
                "end_date": None,
                "total_minutes": 0.0,
                "total_records": 0,
                "records": [],
                "error": str(e),
            }