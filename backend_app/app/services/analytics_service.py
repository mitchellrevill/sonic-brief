import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
from azure.cosmos.exceptions import CosmosHttpResponseError
import random

# Use the improved logging utility
from app.utils.logging_config import get_logger, log_completion, log_error_with_context


class AnalyticsService:
    """Service for tracking and aggregating user analytics data"""
    
    def __init__(self, cosmos_db):
        self.cosmos_db = cosmos_db
        self.logger = get_logger(__name__)
        
        # Log initialization
        self.logger.info("📊 AnalyticsService initialized")
        
        # Verify events container on initialization
        if hasattr(cosmos_db, 'events_container') and cosmos_db.events_container is not None:
            self.logger.info("✓ Events container is available for analytics tracking")
        else:
            self.logger.warning("⚠️ Events container is not available - analytics tracking may fail")

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
        Get aggregated analytics for a specific user
        
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

    async def get_system_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get system-wide analytics
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary containing system analytics
        """
        try:
            # Calculate date range
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            # Try to get events from analytics container first
            events = []
            try:
                # Query all events in the date range
                query = """
                    SELECT * FROM c 
                    WHERE c.timestamp >= @start_date 
                    AND c.timestamp <= @end_date
                    ORDER BY c.timestamp DESC
                """
                
                parameters = [
                    {"name": "@start_date", "value": start_date.isoformat()},
                    {"name": "@end_date", "value": end_date.isoformat()}
                ]
                
                events = list(self.cosmos_db.events_container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                ))
                
                self.logger.info(f"Found {len(events)} system events for {days} days")
                if len(events) > 0:
                    # Log some sample event types for debugging
                    event_types = {}
                    for event in events[:10]:  # Sample first 10 events
                        event_type = event.get("event_type", "unknown")
                        event_types[event_type] = event_types.get(event_type, 0) + 1
                    self.logger.info(f"Sample event types found: {event_types}")
                else:
                    self.logger.warning("No events found in the specified date range")
                
            except Exception as events_error:
                self.logger.warning(f"Error querying system analytics events: {str(events_error)}")
            
            # Get user count from auth container
            user_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'user'"
            user_counts = list(self.cosmos_db.auth_container.query_items(
                query=user_count_query,
                enable_cross_partition_query=True
            ))
            total_users = user_counts[0] if user_counts else 0
            
            # Aggregate system-wide data
            system_analytics = await self._aggregate_system_events(events, total_users)
            
            # If no transcription minutes from events, try to get from jobs as fallback
            if system_analytics["overview"]["total_transcription_minutes"] == 0:
                self.logger.info("No transcription minutes from events, using jobs fallback")
                total_minutes_from_jobs = await self._get_total_minutes_from_jobs(start_date, end_date)
                system_analytics["overview"]["total_transcription_minutes"] = total_minutes_from_jobs
                self.logger.info(f"Found {total_minutes_from_jobs} minutes from {system_analytics['overview']['total_jobs']} jobs via fallback")
            else:
                self.logger.info(f"Using {system_analytics['overview']['total_transcription_minutes']} minutes from events data")
            
            # If still no data, generate sample data for demonstration
            if (system_analytics["overview"]["total_transcription_minutes"] == 0 and 
                system_analytics["overview"]["total_jobs"] == 0 and 
                len(system_analytics["trends"]["daily_activity"]) == 0):
                self.logger.warning(f"No real analytics data found for {days} days period. Reasons:")
                self.logger.warning(f"  - Events found: {len(events)}")
                self.logger.warning(f"  - Jobs with transcription minutes: {system_analytics['overview']['total_transcription_minutes']}")
                self.logger.warning(f"  - Total jobs counted: {system_analytics['overview']['total_jobs']}")
                self.logger.warning(f"  - Daily activity entries: {len(system_analytics['trends']['daily_activity'])}")
                self.logger.warning("Generating sample analytics data for demonstration")
                
                # Add a flag to indicate this is mock data
                system_analytics = self._generate_sample_analytics_data(days, start_date, end_date, total_users)
                system_analytics["_is_mock_data"] = True
                system_analytics["_mock_reason"] = "No real data available in events or jobs containers"
            
            return {
                "period_days": days,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "analytics": system_analytics
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system analytics: {str(e)}")
            # Return a valid response structure even on error
            return {
                "period_days": days,
                "start_date": start_date.isoformat() if 'start_date' in locals() else datetime.now(timezone.utc).isoformat(),
                "end_date": end_date.isoformat() if 'end_date' in locals() else datetime.now(timezone.utc).isoformat(),
                "analytics": {
                    "error": str(e),
                    "overview": {
                        "total_users": 0,
                        "active_users": 0,
                        "total_jobs": 0,
                        "total_transcription_minutes": 0.0,
                        "total_events": 0
                    },
                    "trends": {
                        "daily_activity": {},
                        "user_growth": {},
                        "job_completion_rate": 0.0
                    },
                    "usage": {
                        "transcription_methods": {},
                        "file_vs_text_ratio": {"files": 0, "text": 0},
                        "peak_hours": {}
                    }
                }
            }

    async def _aggregate_system_events(self, events: List[Dict[str, Any]], total_users: int) -> Dict[str, Any]:
        """Aggregate system-wide events"""
        
        analytics = {
            "overview": {
                "total_users": total_users,
                "active_users": 0,
                "total_jobs": 0,
                "total_transcription_minutes": 0.0
            },
            "trends": {
                "daily_activity": {},  # Only job events per day
                "daily_transcription_minutes": {},  # New: transcription minutes per day
                "daily_active_users": {},
                "user_growth": {},
                "job_completion_rate": 0.0
            },
            "usage": {
                "transcription_methods": {},
                "file_vs_text_ratio": {"files": 0, "text": 0},
                "peak_hours": {}
            }
        }
        
        unique_users = set()
        unique_session_users = set()
        jobs_created = 0
        jobs_completed = 0
        daily_jobs = {}
        daily_users = {}
        
        for event in events:
            event_type = event.get("event_type", "")
            user_id = event.get("user_id", "")
            metadata = event.get("metadata", {})
            timestamp = event.get("timestamp", "")
            event_category = event.get("type", "")
            
            if user_id:
                unique_users.add(user_id)
                
                # Track session users separately
                if event_category == "session":
                    unique_session_users.add(user_id)
            
            # Parse date for daily trends
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    date_key = dt.strftime('%Y-%m-%d')
                    hour = dt.hour
                    
                    # Only count job events for daily_activity
                    if event_type in ("job_created", "job_completed", "job_uploaded"):
                        if date_key not in analytics["trends"]["daily_activity"]:
                            analytics["trends"]["daily_activity"][date_key] = 0
                        analytics["trends"]["daily_activity"][date_key] += 1
                    
                    # Track transcription minutes per day
                    if event_type in ("job_uploaded", "job_completed"):
                        minutes = 0.0
                        if metadata.get("audio_duration_minutes"):
                            minutes = float(metadata["audio_duration_minutes"])
                        elif metadata.get("duration_seconds"):
                            minutes = float(metadata["duration_seconds"]) / 60.0
                        if date_key not in analytics["trends"]["daily_transcription_minutes"]:
                            analytics["trends"]["daily_transcription_minutes"][date_key] = 0.0
                        analytics["trends"]["daily_transcription_minutes"][date_key] += minutes
                    
                    # Daily active users (unique users per day)
                    if date_key not in daily_users:
                        daily_users[date_key] = set()
                    if user_id:
                        daily_users[date_key].add(user_id)
                    
                    # Peak hours
                    analytics["usage"]["peak_hours"][hour] = analytics["usage"]["peak_hours"].get(hour, 0) + 1
                except:
                    pass
            
            # Event-specific processing
            if event_type == "job_created":
                jobs_created += 1
                
                # File vs text tracking
                if metadata.get("has_file"):
                    analytics["usage"]["file_vs_text_ratio"]["files"] += 1
                else:
                    analytics["usage"]["file_vs_text_ratio"]["text"] += 1
            
            elif event_type == "job_uploaded":
                # Track audio duration from uploaded files
                if metadata.get("audio_duration_minutes"):
                    audio_minutes = float(metadata["audio_duration_minutes"])
                    analytics["overview"]["total_transcription_minutes"] += audio_minutes
            
            elif event_type == "job_completed":
                jobs_completed += 1
                
                # Track audio duration if available (fallback for older events)
                if metadata.get("audio_duration_minutes"):
                    audio_minutes = float(metadata["audio_duration_minutes"])
                    analytics["overview"]["total_transcription_minutes"] += audio_minutes
                elif metadata.get("duration_seconds"):
                    duration_minutes = metadata["duration_seconds"] / 60.0
                    analytics["overview"]["total_transcription_minutes"] += duration_minutes
                
                # Transcription methods
                method = metadata.get("transcription_method")
                if method:
                    analytics["usage"]["transcription_methods"][method] = \
                        analytics["usage"]["transcription_methods"].get(method, 0) + 1
        
        # Calculate derived metrics
        analytics["overview"]["active_users"] = len(unique_users)
        analytics["overview"]["total_jobs"] = jobs_created
        
        # Convert daily users sets to counts
        for date_key, users_set in daily_users.items():
            analytics["trends"]["daily_active_users"][date_key] = len(users_set)
        
        if jobs_created > 0:
            analytics["trends"]["job_completion_rate"] = (jobs_completed / jobs_created) * 100
        
        return analytics

    async def _get_user_analytics_from_jobs(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Fallback method to calculate user analytics directly from jobs collection
        when analytics events are not available
        """
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
        
        try:
            # Query jobs for this user in the date range
            jobs_query = """
                SELECT * FROM c 
                WHERE c.user_id = @user_id 
                AND c.date >= @start_date 
                AND c.date <= @end_date
                ORDER BY c.date DESC
            """
            
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@start_date", "value": start_date.isoformat()},
                {"name": "@end_date", "value": end_date.isoformat()}
            ]
            
            jobs = list(self.cosmos_db.jobs_container.query_items(
                query=jobs_query,
                parameters=parameters,
                enable_cross_partition_query=False,
                partition_key=user_id
            ))
            
            if not jobs:
                self.logger.info(f"No jobs found for user {user_id} in the date range")
                return analytics
            
            total_minutes = 0.0
            durations = []
            file_count = 0
            text_count = 0
            
            for job in jobs:
                # Count total jobs
                analytics["activity_stats"]["jobs_created"] += 1
                analytics["transcription_stats"]["total_jobs"] += 1
                
                # Calculate audio duration
                audio_minutes = 0.0
                if job.get("audio_duration_minutes"):
                    audio_minutes = float(job["audio_duration_minutes"])
                elif job.get("audio_duration_seconds"):
                    audio_minutes = float(job["audio_duration_seconds"]) / 60.0
                
                if audio_minutes > 0:
                    total_minutes += audio_minutes
                    durations.append(audio_minutes)
                
                # Track input methods  
                if job.get("has_file", False) or job.get("file_url"):
                    file_count += 1
                else:
                    text_count += 1
                
                # Update last activity
                job_date = job.get("date")
                if job_date and (not analytics["activity_stats"]["last_activity"] or job_date > analytics["activity_stats"]["last_activity"]):
                    analytics["activity_stats"]["last_activity"] = job_date
            
            # Update analytics with calculated values
            analytics["transcription_stats"]["total_minutes"] = total_minutes
            analytics["usage_patterns"]["file_upload_count"] = file_count
            analytics["usage_patterns"]["text_input_count"] = text_count
            
            # Calculate average duration
            if durations:
                analytics["transcription_stats"]["average_job_duration"] = sum(durations) / len(durations)
            
            self.logger.info(f"Calculated analytics from {len(jobs)} jobs for user {user_id}: {total_minutes:.2f} minutes")
            
        except Exception as e:
            self.logger.error(f"Error calculating user analytics from jobs: {str(e)}")
        
        return analytics

    async def _get_total_minutes_from_jobs(self, start_date: datetime, end_date: datetime) -> float:
        """
        Fallback method to calculate total transcription minutes from jobs collection
        """
        try:
            # Query all jobs in the date range - try multiple date field patterns
            # First try with just c.type = 'job' to see what we get
            simple_jobs_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'job'"
            simple_count = list(self.cosmos_db.jobs_container.query_items(
                query=simple_jobs_query,
                enable_cross_partition_query=True
            ))
            total_jobs_count = simple_count[0] if simple_count else 0
            self.logger.info(f"Total jobs in container: {total_jobs_count}")
            
            if total_jobs_count == 0:
                self.logger.warning("No jobs found in container at all")
                return 0.0
            
            # Now try to find jobs in date range with flexible date matching
            jobs_query = """
                SELECT * FROM c 
                WHERE c.type = 'job'
                AND (
                    (IS_DEFINED(c.date) AND c.date >= @start_date AND c.date <= @end_date) OR
                    (IS_DEFINED(c.created_at) AND c.created_at >= @start_date AND c.created_at <= @end_date) OR
                    (IS_DEFINED(c.updated_at) AND c.updated_at >= @start_date AND c.updated_at <= @end_date)
                )
                ORDER BY COALESCE(c.date, c.created_at, c.updated_at, '') DESC
            """
            
            parameters = [
                {"name": "@start_date", "value": start_date.isoformat()},
                {"name": "@end_date", "value": end_date.isoformat()}
            ]
            
            jobs = list(self.cosmos_db.jobs_container.query_items(
                query=jobs_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            self.logger.info(f"Found {len(jobs)} jobs in date range for duration calculation")
            
            # If no jobs in date range, let's try to get recent jobs without date filter
            if len(jobs) == 0:
                self.logger.info("No jobs found in date range, trying to get recent jobs without date filter")
                recent_jobs_query = "SELECT TOP 10 * FROM c WHERE c.type = 'job'"
                recent_jobs = list(self.cosmos_db.jobs_container.query_items(
                    query=recent_jobs_query,
                    enable_cross_partition_query=True
                ))
                self.logger.info(f"Found {len(recent_jobs)} recent jobs without date filtering")
                if recent_jobs:
                    sample_job = recent_jobs[0]
                    self.logger.info(f"Sample job date fields: date={sample_job.get('date')}, created_at={sample_job.get('created_at')}, updated_at={sample_job.get('updated_at')}")
            
            total_minutes = 0.0
            jobs_with_duration = 0
            
            for job in jobs:
                # Calculate audio duration
                audio_minutes = 0.0
                if job.get("audio_duration_minutes"):
                    audio_minutes = float(job["audio_duration_minutes"])
                    jobs_with_duration += 1
                elif job.get("audio_duration_seconds"):
                    audio_minutes = float(job["audio_duration_seconds"]) / 60.0
                    jobs_with_duration += 1
                
                total_minutes += audio_minutes
            
            self.logger.info(f"Calculated {total_minutes} total minutes from {jobs_with_duration}/{len(jobs)} jobs with duration data")
            return total_minutes
            
        except Exception as e:
            self.logger.error(f"Error calculating total minutes from jobs: {str(e)}")
            return 0.0

    async def verify_events_container(self) -> bool:
        """
        Verify that the events container is accessible and can be written to
        
        Returns:
            True if container is working, False otherwise
        """
        try:
            self.logger.info("🔍 Starting events container verification...")
            
            # Check if container exists
            if not hasattr(self.cosmos_db, 'events_container') or self.cosmos_db.events_container is None:
                self.logger.error("❌ Events container is not initialized in CosmosDB")
                return False
            
            self.logger.info("✓ Events container reference found, testing write access...")
            
            # Try to create a test event
            test_event_id = str(uuid.uuid4())
            test_event = {
                "id": test_event_id,
                "type": "test",
                "event_type": "container_test",
                "user_id": "system",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "metadata": {"test": True},
                "partition_key": "system"
            }
            
            self.logger.info(f"📝 Creating test event with ID: {test_event_id}")
            
            # Attempt to create and then delete the test event
            result = self.cosmos_db.events_container.create_item(body=test_event)
            self.logger.info("✓ Test event created successfully, cleaning up...")
            
            self.cosmos_db.events_container.delete_item(item=test_event_id, partition_key="system")
            self.logger.info("✓ Test event deleted successfully")
            
            self.logger.info("✅ Events container verification successful")
            return True
            
        except CosmosHttpResponseError as e:
            self.logger.error(f"❌ Events container verification failed - Cosmos error: {e.status_code} - {e.message}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Events container verification failed - Unexpected error: {str(e)}")
            return False

    async def create_job_events_for_existing_jobs(self, limit: int = 10) -> int:
        """
        Backfill analytics events for existing jobs that don't have events
        This is useful for populating events from historical job data
        
        Args:
            limit: Maximum number of jobs to process
            
        Returns:
            Number of events created
        """
        try:
            self.logger.info(f"Starting backfill of analytics events for up to {limit} jobs")
            
            # Query recent jobs without corresponding events
            jobs_query = """
                SELECT TOP @limit * FROM c 
                WHERE c.type = 'job'
                ORDER BY c.date DESC
            """
            
            parameters = [{"name": "@limit", "value": limit}]
            
            jobs = list(self.cosmos_db.jobs_container.query_items(
                query=jobs_query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            
            events_created = 0
            
            for job in jobs:
                user_id = job.get("user_id")
                job_id = job.get("id")
                
                if not user_id or not job_id:
                    continue
                
                # Create job_created event
                created_event_id = await self.track_job_event(
                    job_id=job_id,
                    user_id=user_id,
                    event_type="job_created",
                    metadata={
                        "has_file": job.get("has_file", False),
                        "file_size_bytes": job.get("file_size_bytes", 0),
                        "backfilled": True
                    }
                )
                
                if created_event_id:
                    events_created += 1
                
                # Create job_uploaded event if there's audio duration
                audio_duration_minutes = job.get("audio_duration_minutes")
                if audio_duration_minutes:
                    uploaded_event_id = await self.track_job_event(
                        job_id=job_id,
                        user_id=user_id,
                        event_type="job_uploaded",
                        metadata={
                            "has_file": job.get("has_file", True),
                            "audio_duration_minutes": float(audio_duration_minutes),
                            "audio_duration_seconds": job.get("audio_duration_seconds"),
                            "file_name": job.get("filename"),
                            "backfilled": True
                        }
                    )
                    
                    if uploaded_event_id:
                        events_created += 1
            
            self.logger.info(f"✓ Backfill completed: {events_created} events created for {len(jobs)} jobs")
            return events_created
            
        except Exception as e:
            self.logger.error(f"Error during events backfill: {str(e)}")
            return 0

    def _generate_sample_analytics_data(self, days: int, start_date: datetime, end_date: datetime, total_users: int) -> Dict[str, Any]:
        """Generate sample analytics data for demonstration purposes when no real data exists"""
        import random
        from datetime import timedelta
        
        # Generate sample daily activity data
        daily_activity = {}
        daily_active_users = {}
        user_growth = {}
        
        current_date = start_date
        base_jobs = max(5, total_users * 2)  # Base number of jobs per day
        base_users = max(3, total_users // 2)  # Base active users per day
        
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            
            # Generate realistic patterns (more activity on weekdays)
            day_multiplier = 1.0
            if current_date.weekday() < 5:  # Monday to Friday
                day_multiplier = 1.2
            elif current_date.weekday() == 6:  # Sunday
                day_multiplier = 0.6
            
            # Add some randomness
            activity_variance = random.uniform(0.7, 1.3)
            
            # Daily activity (job count)
            daily_jobs = int(base_jobs * day_multiplier * activity_variance)
            daily_activity[date_str] = daily_jobs
            
            # Daily active users
            active_users = int(base_users * day_multiplier * activity_variance)
            daily_active_users[date_str] = min(active_users, total_users)
            
            # User growth (cumulative)
            if current_date == start_date:
                user_growth[date_str] = total_users
            else:
                prev_date = current_date - timedelta(days=1)
                prev_date_str = prev_date.strftime("%Y-%m-%d")
                growth = random.randint(0, 2)  # 0-2 new users per day
                user_growth[date_str] = user_growth.get(prev_date_str, total_users) + growth
            
            current_date += timedelta(days=1)
        
        # Calculate totals
        total_jobs = sum(daily_activity.values())
        total_minutes = total_jobs * random.uniform(3.5, 8.5) # 3.5-8.5 minutes per job average
        
        return {
            "overview": {
                "total_users": max(total_users, 5),
                "active_users": max(total_users // 2, 3),
                "total_jobs": total_jobs,
                "total_transcription_minutes": round(total_minutes, 1)
            },
            "trends": {
                "daily_activity": daily_activity,
                "daily_active_users": daily_active_users,
                "user_growth": user_growth,
                "job_completion_rate": random.uniform(0.85, 0.98)
            },
            "usage": {
                "transcription_methods": {
                    "file_upload": random.randint(60, 80),
                    "text_input": random.randint(15, 25),
                    "microphone": random.randint(5, 15)
                },
                "file_vs_text_ratio": {
                    "files": random.randint(70, 85),
                    "text": random.randint(15, 30)
                },
                "peak_hours": {
                    "9": random.randint(8, 15),
                    "10": random.randint(12, 20),
                    "11": random.randint(15, 25),
                    "14": random.randint(10, 18),
                    "15": random.randint(8, 16),
                    "16": random.randint(5, 12)
                }
            }
        }

    async def diagnose_analytics_data_sources(self, days: int = 30) -> Dict[str, Any]:
        """
        Comprehensive diagnostic to understand why analytics are returning mock data
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Detailed diagnostic information about data sources
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)
            
            diagnostic = {
                "period": {
                    "days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "events_container": {},
                "jobs_container": {},
                "auth_container": {},
                "data_quality": {},
                "recommendations": []
            }
            
            # Check Events Container
            try:
                # Count total events
                total_events_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'event'"
                total_events = list(self.cosmos_db.events_container.query_items(
                    query=total_events_query,
                    enable_cross_partition_query=True
                ))
                
                # Count events in date range
                date_range_events_query = """
                    SELECT VALUE COUNT(1) FROM c 
                    WHERE c.type = 'event' 
                    AND c.timestamp >= @start_date 
                    AND c.timestamp <= @end_date
                """
                date_range_events = list(self.cosmos_db.events_container.query_items(
                    query=date_range_events_query,
                    parameters=[
                        {"name": "@start_date", "value": start_date.isoformat()},
                        {"name": "@end_date", "value": end_date.isoformat()}
                    ],
                    enable_cross_partition_query=True
                ))
                
                # Get sample events to analyze structure
                sample_events_query = "SELECT TOP 5 * FROM c WHERE c.type = 'event' ORDER BY c.timestamp DESC"
                sample_events = list(self.cosmos_db.events_container.query_items(
                    query=sample_events_query,
                    enable_cross_partition_query=True
                ))
                
                diagnostic["events_container"] = {
                    "accessible": True,
                    "total_events": total_events[0] if total_events else 0,
                    "events_in_date_range": date_range_events[0] if date_range_events else 0,
                    "sample_events": sample_events,
                    "sample_count": len(sample_events)
                }
                
            except Exception as e:
                diagnostic["events_container"] = {
                    "accessible": False,
                    "error": str(e)
                }
            
            # Check Jobs Container
            try:
                # Count total jobs
                total_jobs_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'job'"
                total_jobs = list(self.cosmos_db.jobs_container.query_items(
                    query=total_jobs_query,
                    enable_cross_partition_query=True
                ))
                
                # Count jobs in date range
                date_range_jobs_query = """
                    SELECT VALUE COUNT(1) FROM c 
                    WHERE c.type = 'job' 
                    AND c.date >= @start_date 
                    AND c.date <= @end_date
                """
                date_range_jobs = list(self.cosmos_db.jobs_container.query_items(
                    query=date_range_jobs_query,
                    parameters=[
                        {"name": "@start_date", "value": start_date.isoformat()},
                        {"name": "@end_date", "value": end_date.isoformat()}
                    ],
                    enable_cross_partition_query=True
                ))
                
                # Count jobs with audio duration
                jobs_with_duration_query = """
                    SELECT VALUE COUNT(1) FROM c 
                    WHERE c.type = 'job' 
                    AND (IS_DEFINED(c.audio_duration_minutes) OR IS_DEFINED(c.audio_duration_seconds))
                """
                jobs_with_duration = list(self.cosmos_db.jobs_container.query_items(
                    query=jobs_with_duration_query,
                    enable_cross_partition_query=True
                ))
                
                # Get sample jobs to analyze structure
                sample_jobs_query = "SELECT TOP 5 * FROM c WHERE c.type = 'job' ORDER BY c.date DESC"
                sample_jobs = list(self.cosmos_db.jobs_container.query_items(
                    query=sample_jobs_query,
                    enable_cross_partition_query=True
                ))
                
                diagnostic["jobs_container"] = {
                    "accessible": True,
                    "total_jobs": total_jobs[0] if total_jobs else 0,
                    "jobs_in_date_range": date_range_jobs[0] if date_range_jobs else 0,
                    "jobs_with_audio_duration": jobs_with_duration[0] if jobs_with_duration else 0,
                    "sample_jobs": [
                        {
                            "id": job.get("id"),
                            "date": job.get("date"),
                            "has_audio_duration_minutes": "audio_duration_minutes" in job,
                            "has_audio_duration_seconds": "audio_duration_seconds" in job,
                            "audio_duration_minutes": job.get("audio_duration_minutes"),
                            "audio_duration_seconds": job.get("audio_duration_seconds"),
                            "status": job.get("status"),
                            "user_id": job.get("user_id")
                        } for job in sample_jobs
                    ],
                    "sample_count": len(sample_jobs)
                }
                
            except Exception as e:
                diagnostic["jobs_container"] = {
                    "accessible": False,
                    "error": str(e)
                }
            
            # Check Auth Container (for user count)
            try:
                user_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'user'"
                user_count = list(self.cosmos_db.auth_container.query_items(
                    query=user_count_query,
                    enable_cross_partition_query=True
                ))
                
                diagnostic["auth_container"] = {
                    "accessible": True,
                    "total_users": user_count[0] if user_count else 0
                }
                
            except Exception as e:
                diagnostic["auth_container"] = {
                    "accessible": False,
                    "error": str(e)
                }
            
            # Data Quality Analysis
            events_exist = diagnostic["events_container"].get("events_in_date_range", 0) > 0
            jobs_exist = diagnostic["jobs_container"].get("jobs_in_date_range", 0) > 0
            jobs_with_duration = diagnostic["jobs_container"].get("jobs_with_audio_duration", 0) > 0
            
            diagnostic["data_quality"] = {
                "events_available": events_exist,
                "jobs_available": jobs_exist,
                "jobs_have_duration_data": jobs_with_duration,
                "using_mock_data": not (events_exist or (jobs_exist and jobs_with_duration))
            }
            
            # Generate Recommendations
            if not events_exist and not jobs_exist:
                diagnostic["recommendations"].append("No data found in any container. System may be newly deployed or containers may be empty.")
            elif not events_exist and jobs_exist:
                if not jobs_with_duration:
                    diagnostic["recommendations"].append("Jobs exist but lack audio duration data. Check job processing pipeline.")
                diagnostic["recommendations"].append("No analytics events found. Use the backfill API to create events from existing jobs.")
            elif events_exist:
                diagnostic["recommendations"].append("Analytics events are available and should provide real data.")
            
            if diagnostic["events_container"].get("accessible", False) == False:
                diagnostic["recommendations"].append("Events container is not accessible. Check container configuration and permissions.")
            
            if diagnostic["jobs_container"].get("accessible", False) == False:
                diagnostic["recommendations"].append("Jobs container is not accessible. Check container configuration and permissions.")
                
            return diagnostic
            
        except Exception as e:
            self.logger.error(f"Error during analytics diagnostics: {str(e)}")
            return {
                "error": str(e),
                "recommendations": ["Unable to run diagnostics. Check service configuration and container access."]
            }

    async def get_quick_data_summary(self) -> Dict[str, Any]:
        """
        Quick summary of available data across all containers
        
        Returns:
            Summary of data availability
        """
        try:
            summary = {}
            
            # Check events
            try:
                events_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'event'"
                events_count = list(self.cosmos_db.events_container.query_items(
                    query=events_count_query,
                    enable_cross_partition_query=True
                ))
                summary["events"] = events_count[0] if events_count else 0
            except Exception as e:
                summary["events"] = f"Error: {str(e)}"
            
            # Check jobs  
            try:
                jobs_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'job'"
                jobs_count = list(self.cosmos_db.jobs_container.query_items(
                    query=jobs_count_query,
                    enable_cross_partition_query=True
                ))
                summary["jobs"] = jobs_count[0] if jobs_count else 0
            except Exception as e:
                summary["jobs"] = f"Error: {str(e)}"
            
            # Check users
            try:
                users_count_query = "SELECT VALUE COUNT(1) FROM c WHERE c.type = 'user'"
                users_count = list(self.cosmos_db.auth_container.query_items(
                    query=users_count_query,
                    enable_cross_partition_query=True
                ))
                summary["users"] = users_count[0] if users_count else 0
            except Exception as e:
                summary["users"] = f"Error: {str(e)}"
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting quick data summary: {str(e)}")
            return {"error": str(e)}
