import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from azure.cosmos.exceptions import CosmosHttpResponseError
import random
from collections import defaultdict

# Use the improved logging utility
from app.utils.logging_config import get_logger, log_completion, log_error_with_context


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
        else:
            self.logger.warning("⚠️ Analytics container is not available - analytics aggregation may fail")
            
        if hasattr(cosmos_db, 'events_container') and cosmos_db.events_container is not None:
            self.logger.info("✓ Events container is available for session tracking")
        else:
            self.logger.warning("⚠️ Events container is not available - session tracking may fail")

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

    async def track_user_session(
        self, 
        user_id: str, 
        action: str, 
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track user login/logout and session data
        
        Args:
            user_id: ID of the user
            action: login, logout, activity
            metadata: Session data (ip_address, user_agent, etc.)
        """
        try:
            session_id = str(uuid.uuid4())
            
            session_data = {
                "id": session_id,
                "type": "session",
                "user_id": user_id,
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
                "partition_key": user_id
            }
            
            self.cosmos_db.sessions_container.create_item(body=session_data)
            
            self.logger.info(f"User session tracked: {action} for user {user_id}")
            return session_id
            
        except Exception as e:
            self.logger.error(f"Error tracking user session: {str(e)}")
            return ""

    async def track_user_session(
        self, 
        user_id: str, 
        action: str, 
        page: Optional[str] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> str:
        """
        Track user session activity
        
        Args:
            user_id: ID of the user
            action: session action (start, heartbeat, end, focus, blur, page_view)
            page: current page/route
            user_agent: browser user agent
            ip_address: user IP address
            
        Returns:
            Session event ID
        """
        try:
            session_event_id = str(uuid.uuid4())
            
            session_event = {
                "id": session_event_id,
                "type": "session",
                "event_type": f"session_{action}",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {
                    "page": page,
                    "user_agent": user_agent,
                    "ip_address": ip_address,
                    "action": action
                },
                "partition_key": user_id
            }
            
            # Store in analytics container
            self.cosmos_db.events_container.create_item(body=session_event)
            
            self.logger.info(f"Session event tracked: session_{action} for user {user_id}")
            return session_event_id
            
        except Exception as e:
            self.logger.error(f"Error tracking session event: {str(e)}")
            # Don't fail the main operation if session tracking fails
            return ""

    async def get_active_users(self, minutes: int = 5) -> List[str]:
        """
        Get users who were active in the last N minutes
        
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
            AND c.event_type IN ('session_heartbeat', 'session_start', 'session_page_view') 
            AND c.timestamp >= @cutoff_time
            """
            
            parameters = [{"name": "@cutoff_time", "value": cutoff_time.isoformat()}]
            
            active_users = []
            for item in self.cosmos_db.events_container.query_items(
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
        Calculate total session duration for a user in the last N days
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            Total session duration in minutes
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
            
            query = """
            SELECT c.event_type, c.timestamp
            FROM c 
            WHERE c.type = 'session' 
            AND c.user_id = @user_id
            AND c.event_type IN ('session_start', 'session_end')
            AND c.timestamp >= @cutoff_time
            ORDER BY c.timestamp ASC
            """
            
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@cutoff_time", "value": cutoff_time.isoformat()}
            ]
            
            session_events = []
            for item in self.cosmos_db.events_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ):
                session_events.append(item)
            
            # Calculate session durations
            total_duration = 0.0
            session_start = None
            
            for event in session_events:
                if event["event_type"] == "session_start":
                    session_start = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                elif event["event_type"] == "session_end" and session_start:
                    session_end = datetime.fromisoformat(event["timestamp"].replace('Z', '+00:00'))
                    duration = (session_end - session_start).total_seconds() / 60  # Convert to minutes
                    total_duration += duration
                    session_start = None
            
            return total_duration
            
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
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            self.logger.info(f"Getting user analytics for {user_id} from analytics container for {days} days")
            
            # Get user's analytics records from analytics container
            user_analytics_records = await self._get_user_analytics_records(user_id, start_date, end_date)
            
            # Get user's session events
            user_session_events = await self._get_user_session_events(user_id, start_date, end_date)
            
            # Aggregate user data
            user_analytics = await self._aggregate_user_analytics_data(
                user_analytics_records, 
                user_session_events, 
                start_date, 
                end_date, 
                days
            )
            
            self.logger.info(f"User analytics aggregated for {user_id}: {user_analytics['transcription_stats']['total_jobs']} jobs, "
                           f"{user_analytics['transcription_stats']['total_minutes']:.1f} minutes")
            
            return user_analytics
            
        except Exception as e:
            self.logger.error(f"Error getting user analytics for {user_id}: {str(e)}")
            return await self._get_fallback_user_analytics(days)
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
                "analytics": analytics
            }
            
        except Exception as e:
            self.logger.error(f"Error getting user analytics: {str(e)}")
            # Return a valid response structure even on error
            return {
                "user_id": user_id,
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "analytics": {
                    "error": str(e),
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