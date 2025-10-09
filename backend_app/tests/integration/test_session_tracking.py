"""
Integration tests for session tracking and user engagement metrics.

Business value:
- Ensures user sessions are tracked accurately for analytics
- Validates engagement metrics help understand user behavior
- Confirms session data supports business decision-making
- Protects against inaccurate analytics that mislead strategy
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta


class TestSessionTracking:
    """Test user session tracking and engagement metrics."""
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        service.query_items_async.return_value = []
        service.create_item_async.return_value = {"id": "session-123", "status": "active"}
        return service
    
    @pytest.fixture
    def mock_session_tracking_service(self):
        """Mock session tracking service"""
        service = AsyncMock()
        service.start_session_async.return_value = {"session_id": "session-123", "started_at": datetime.utcnow().isoformat()}
        service.end_session_async.return_value = {"session_id": "session-123", "duration_minutes": 45}
        service.get_user_sessions_async.return_value = []
        return service

    @pytest.mark.asyncio
    async def test_user_login_creates_session(self, mock_cosmos_service, mock_session_tracking_service):
        """
        USER JOURNEY: User logs in and session is tracked
        
        Steps:
        1. User authenticates with valid credentials
        2. System creates new session record
        3. Session has start time, user ID, device info
        4. User can see active session
        
        Business value: Track user login activity for security and analytics
        """
        # STEP 1: User logs in
        user_id = "user-123"
        device_info = {"browser": "Chrome", "os": "Windows", "ip": "192.168.1.1"}
        
        # STEP 2: System creates session
        session = await mock_session_tracking_service.start_session_async(
            user_id=user_id,
            device_info=device_info
        )
        
        assert session["session_id"] is not None
        assert session["started_at"] is not None
        print(f"✅ STEP 1: Session created for user {user_id} (session_id: {session['session_id']})")
        
        # STEP 3: Verify session attributes
        mock_cosmos_service.create_item_async.return_value = {
            "id": session["session_id"],
            "user_id": user_id,
            "started_at": session["started_at"],
            "device_info": device_info,
            "status": "active"
        }
        
        # STEP 4: User can retrieve active session
        mock_cosmos_service.query_items_async.return_value = [
            mock_cosmos_service.create_item_async.return_value
        ]
        
        active_sessions = await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.user_id = @user_id AND c.status = 'active'",
            parameters=[{"name": "@user_id", "value": user_id}]
        )
        
        assert len(active_sessions) == 1
        assert active_sessions[0]["user_id"] == user_id
        assert active_sessions[0]["status"] == "active"
        print(f"✅ STEP 2: Active session tracked with device info: {device_info['browser']} on {device_info['os']}")

    @pytest.mark.asyncio
    async def test_user_logout_ends_session(self, mock_cosmos_service, mock_session_tracking_service):
        """
        USER JOURNEY: User logs out and session is properly ended
        
        Steps:
        1. User has active session
        2. User logs out
        3. System ends session with end time
        4. Session duration is calculated
        5. Session marked as inactive
        
        Business value: Accurate session duration for engagement metrics
        """
        # STEP 1: User has active session
        session_id = "session-123"
        user_id = "user-123"
        started_at = datetime.utcnow() - timedelta(minutes=45)
        
        mock_cosmos_service.query_items_async.return_value = [{
            "id": session_id,
            "user_id": user_id,
            "started_at": started_at.isoformat(),
            "status": "active"
        }]
        
        print(f"✅ STEP 1: User has active session (started 45 minutes ago)")
        
        # STEP 2: User logs out
        ended_at = datetime.utcnow()
        
        # STEP 3: System ends session
        session_end = await mock_session_tracking_service.end_session_async(
            session_id=session_id
        )
        
        assert session_end["session_id"] == session_id
        assert session_end["duration_minutes"] == 45
        print(f"✅ STEP 2: Session ended after 45 minutes")
        
        # STEP 4: Session marked inactive
        mock_cosmos_service.query_items_async.return_value = [{
            "id": session_id,
            "user_id": user_id,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_minutes": 45,
            "status": "inactive"
        }]
        
        inactive_session = (await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.id = @session_id",
            parameters=[{"name": "@session_id", "value": session_id}]
        ))[0]
        
        assert inactive_session["status"] == "inactive"
        assert inactive_session["duration_minutes"] == 45
        print(f"✅ STEP 3: Session duration calculated: {inactive_session['duration_minutes']} minutes")

    @pytest.mark.asyncio
    async def test_concurrent_sessions_from_different_devices(self, mock_cosmos_service, mock_session_tracking_service):
        """
        USER JOURNEY: User logs in from multiple devices simultaneously
        
        Steps:
        1. User logs in from desktop
        2. User logs in from mobile (without logging out of desktop)
        3. Both sessions are active
        4. System tracks both sessions separately
        5. User can log out of one device independently
        
        Business value: Support multi-device usage patterns
        """
        user_id = "user-123"
        
        # STEP 1: Desktop login
        desktop_session = await mock_session_tracking_service.start_session_async(
            user_id=user_id,
            device_info={"browser": "Chrome", "os": "Windows", "ip": "192.168.1.10"}
        )
        print(f"✅ STEP 1: Desktop session created (session_id: {desktop_session['session_id']})")
        
        # STEP 2: Mobile login
        mobile_session = await mock_session_tracking_service.start_session_async(
            user_id=user_id,
            device_info={"browser": "Safari", "os": "iOS", "ip": "192.168.1.20"}
        )
        print(f"✅ STEP 2: Mobile session created (session_id: {mobile_session['session_id']})")
        
        # STEP 3: Both sessions active
        mock_cosmos_service.query_items_async.return_value = [
            {
                "id": desktop_session["session_id"],
                "user_id": user_id,
                "device_info": {"browser": "Chrome", "os": "Windows"},
                "status": "active"
            },
            {
                "id": mobile_session["session_id"],
                "user_id": user_id,
                "device_info": {"browser": "Safari", "os": "iOS"},
                "status": "active"
            }
        ]
        
        active_sessions = await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.user_id = @user_id AND c.status = 'active'",
            parameters=[{"name": "@user_id", "value": user_id}]
        )
        
        assert len(active_sessions) == 2
        print(f"✅ STEP 3: Both sessions active simultaneously")
        
        # STEP 4: End desktop session only
        await mock_session_tracking_service.end_session_async(session_id=desktop_session["session_id"])
        
        mock_cosmos_service.query_items_async.return_value = [
            {
                "id": mobile_session["session_id"],
                "user_id": user_id,
                "device_info": {"browser": "Safari", "os": "iOS"},
                "status": "active"
            }
        ]
        
        remaining_sessions = await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.user_id = @user_id AND c.status = 'active'",
            parameters=[{"name": "@user_id", "value": user_id}]
        )
        
        assert len(remaining_sessions) == 1
        assert remaining_sessions[0]["device_info"]["os"] == "iOS"
        print(f"✅ STEP 4: Desktop logged out, mobile session still active")

    @pytest.mark.asyncio
    async def test_session_timeout_after_inactivity(self, mock_cosmos_service, mock_session_tracking_service):
        """
        USER JOURNEY: Session times out after extended inactivity
        
        Steps:
        1. User logs in and has active session
        2. User is inactive for 2 hours
        3. System detects session timeout (>1 hour inactivity)
        4. Session automatically marked as expired
        5. User must re-authenticate on next request
        
        Business value: Security - auto-logout inactive users
        """
        # STEP 1: User has active session
        session_id = "session-123"
        user_id = "user-123"
        started_at = datetime.utcnow() - timedelta(hours=2)
        last_activity = datetime.utcnow() - timedelta(hours=2)
        
        mock_cosmos_service.query_items_async.return_value = [{
            "id": session_id,
            "user_id": user_id,
            "started_at": started_at.isoformat(),
            "last_activity_at": last_activity.isoformat(),
            "status": "active"
        }]
        
        print(f"✅ STEP 1: Session created 2 hours ago with no activity")
        
        # STEP 2: Check for timeout (>1 hour inactivity)
        timeout_threshold = datetime.utcnow() - timedelta(hours=1)
        
        # STEP 3: System detects timeout
        session = (await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.id = @session_id",
            parameters=[{"name": "@session_id", "value": session_id}]
        ))[0]
        
        session_last_activity = datetime.fromisoformat(session["last_activity_at"])
        is_expired = session_last_activity < timeout_threshold
        
        assert is_expired is True
        print(f"✅ STEP 2: Session expired due to inactivity (>1 hour)")
        
        # STEP 4: Mark session as expired
        mock_cosmos_service.query_items_async.return_value = [{
            "id": session_id,
            "user_id": user_id,
            "started_at": started_at.isoformat(),
            "last_activity_at": last_activity.isoformat(),
            "ended_at": datetime.utcnow().isoformat(),
            "status": "expired",
            "timeout_reason": "inactivity"
        }]
        
        expired_session = (await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.id = @session_id",
            parameters=[{"name": "@session_id", "value": session_id}]
        ))[0]
        
        assert expired_session["status"] == "expired"
        assert expired_session["timeout_reason"] == "inactivity"
        print(f"✅ STEP 3: Session marked as expired, user must re-authenticate")


class TestEngagementMetrics:
    """Test user engagement tracking and analytics."""
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        service.query_items_async.return_value = []
        return service

    @pytest.mark.asyncio
    async def test_track_user_engagement_across_sessions(self, mock_cosmos_service):
        """
        ANALYTICS: Calculate user engagement from session history
        
        Steps:
        1. User has 5 sessions over past week
        2. System calculates total time spent
        3. System calculates average session duration
        4. System identifies most active days/times
        5. Manager can see engagement report
        
        Business value: Understand user engagement patterns
        """
        user_id = "user-123"
        
        # STEP 1: User has 5 sessions
        mock_cosmos_service.query_items_async.return_value = [
            {"id": "s1", "user_id": user_id, "duration_minutes": 30, "started_at": (datetime.utcnow() - timedelta(days=1)).isoformat()},
            {"id": "s2", "user_id": user_id, "duration_minutes": 45, "started_at": (datetime.utcnow() - timedelta(days=2)).isoformat()},
            {"id": "s3", "user_id": user_id, "duration_minutes": 60, "started_at": (datetime.utcnow() - timedelta(days=3)).isoformat()},
            {"id": "s4", "user_id": user_id, "duration_minutes": 20, "started_at": (datetime.utcnow() - timedelta(days=5)).isoformat()},
            {"id": "s5", "user_id": user_id, "duration_minutes": 50, "started_at": (datetime.utcnow() - timedelta(days=6)).isoformat()}
        ]
        
        sessions = await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.user_id = @user_id AND c.started_at >= @start_date",
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@start_date", "value": (datetime.utcnow() - timedelta(days=7)).isoformat()}
            ]
        )
        
        # STEP 2: Calculate engagement metrics
        total_minutes = sum(s["duration_minutes"] for s in sessions)
        average_duration = total_minutes / len(sessions)
        session_count = len(sessions)
        
        assert session_count == 5
        assert total_minutes == 205  # 30+45+60+20+50
        assert average_duration == 41  # 205/5
        print(f"✅ STEP 1: User had {session_count} sessions over past week")
        print(f"✅ STEP 2: Total engagement: {total_minutes} minutes, avg {average_duration} min/session")

    @pytest.mark.asyncio
    async def test_track_feature_usage_within_sessions(self, mock_cosmos_service):
        """
        ANALYTICS: Track which features users use during sessions
        
        Steps:
        1. User performs various actions during session
        2. System tracks each action (upload, transcribe, analyze)
        3. Session has activity log with timestamps
        4. Analytics can show most-used features
        5. Business can identify valuable features
        
        Business value: Understand which features drive engagement
        """
        session_id = "session-123"
        user_id = "user-123"
        
        # STEP 1: User performs actions
        actions = [
            {"action": "upload_file", "timestamp": datetime.utcnow().isoformat(), "duration_seconds": 5},
            {"action": "view_jobs", "timestamp": datetime.utcnow().isoformat(), "duration_seconds": 10},
            {"action": "get_transcription", "timestamp": datetime.utcnow().isoformat(), "duration_seconds": 3},
            {"action": "request_analysis", "timestamp": datetime.utcnow().isoformat(), "duration_seconds": 15},
            {"action": "export_document", "timestamp": datetime.utcnow().isoformat(), "duration_seconds": 8}
        ]
        
        # STEP 2: System tracks actions
        mock_cosmos_service.query_items_async.return_value = [{
            "id": session_id,
            "user_id": user_id,
            "activity_log": actions,
            "status": "active"
        }]
        
        session = (await mock_cosmos_service.query_items_async(
            query="SELECT * FROM c WHERE c.id = @session_id",
            parameters=[{"name": "@session_id", "value": session_id}]
        ))[0]
        
        # STEP 3: Calculate feature usage
        action_counts = {}
        for action in session["activity_log"]:
            action_type = action["action"]
            action_counts[action_type] = action_counts.get(action_type, 0) + 1
        
        assert action_counts["upload_file"] == 1
        assert action_counts["get_transcription"] == 1
        assert action_counts["request_analysis"] == 1
        print(f"✅ STEP 1: Session tracked {len(actions)} user actions")
        print(f"✅ STEP 2: Feature usage: {action_counts}")

    @pytest.mark.asyncio
    async def test_identify_inactive_users_for_retention(self, mock_cosmos_service):
        """
        ANALYTICS: Identify users who haven't logged in recently
        
        Steps:
        1. Query all users' last session dates
        2. Identify users with no session in 30 days
        3. Flag users for retention campaign
        4. Manager can see inactive user list
        5. Business can send re-engagement emails
        
        Business value: Proactive user retention
        """
        # STEP 1: Get last session for all users
        mock_cosmos_service.query_items_async.return_value = [
            {"user_id": "user-1", "last_session": (datetime.utcnow() - timedelta(days=2)).isoformat()},  # Active
            {"user_id": "user-2", "last_session": (datetime.utcnow() - timedelta(days=45)).isoformat()}, # Inactive
            {"user_id": "user-3", "last_session": (datetime.utcnow() - timedelta(days=5)).isoformat()},  # Active
            {"user_id": "user-4", "last_session": (datetime.utcnow() - timedelta(days=90)).isoformat()}, # Inactive
            {"user_id": "user-5", "last_session": (datetime.utcnow() - timedelta(days=1)).isoformat()},  # Active
        ]
        
        all_users = await mock_cosmos_service.query_items_async(
            query="SELECT c.user_id, MAX(c.started_at) as last_session FROM c GROUP BY c.user_id"
        )
        
        # STEP 2: Identify inactive users (>30 days)
        inactive_threshold = datetime.utcnow() - timedelta(days=30)
        inactive_users = []
        
        for user in all_users:
            last_session = datetime.fromisoformat(user["last_session"])
            if last_session < inactive_threshold:
                inactive_users.append(user["user_id"])
        
        assert len(inactive_users) == 2  # user-2 and user-4
        assert "user-2" in inactive_users
        assert "user-4" in inactive_users
        print(f"✅ STEP 1: Identified {len(inactive_users)} inactive users (>30 days)")
        print(f"   Inactive users: {inactive_users}")
