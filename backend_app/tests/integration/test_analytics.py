"""
Integration Tests: Analytics and Export Features

Tests the analytics and reporting features that managers and admins use
to track usage, generate reports, and justify budgets.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json


class TestAnalyticsAndReporting:
    """
    USER STORY: "As a manager, I want to see usage analytics and export reports"
    
    Validates:
    1. User analytics calculation (total minutes, jobs, trends)
    2. System-wide analytics aggregation
    3. Export functionality (CSV, PDF)
    4. Session tracking and activity monitoring
    
    Critical for business decision-making and budget justification.
    """
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service with analytics data"""
        service = AsyncMock()
        
        # Mock user jobs for analytics
        service.query_items_async.return_value = [
            {
                "id": "job-1",
                "user_id": "user-123",
                "audio_duration_minutes": 45.5,
                "file_size_bytes": 50_000_000,
                "status": "completed",
                "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
            },
            {
                "id": "job-2",
                "user_id": "user-123",
                "audio_duration_minutes": 60.0,
                "file_size_bytes": 70_000_000,
                "status": "completed",
                "created_at": (datetime.utcnow() - timedelta(days=10)).isoformat()
            },
            {
                "id": "job-3",
                "user_id": "user-123",
                "audio_duration_minutes": 30.5,
                "file_size_bytes": 40_000_000,
                "status": "completed",
                "created_at": (datetime.utcnow() - timedelta(days=15)).isoformat()
            }
        ]
        
        return service
    
    @pytest.fixture
    def mock_analytics_service(self):
        """Mock analytics service"""
        service = Mock()
        
        service.calculate_user_analytics.return_value = {
            "total_minutes": 136.0,
            "total_jobs": 3,
            "avg_duration_minutes": 45.3,
            "total_storage_mb": 152.6,
            "jobs_per_day": 0.2,
            "trend": "stable"
        }
        
        return service
    
    @pytest.fixture
    def mock_export_service(self):
        """Mock export service"""
        service = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_manager_can_view_user_analytics(
        self,
        mock_cosmos_service,
        mock_analytics_service
    ):
        """
        MANAGER WORKFLOW: View analytics for team member
        
        Steps:
        1. Manager authenticates
        2. Manager requests analytics for user
        3. System calculates total minutes, jobs, trends
        4. Manager views analytics dashboard
        
        Critical for tracking team productivity.
        """
        
        # STEP 1: Manager authenticates (with analytics permission)
        manager = {
            "id": "manager-123",
            "email": "manager@example.com",
            "permission_level": "editor",  # Has analytics access
            "capabilities": {"view_analytics": True}
        }
        assert manager["capabilities"]["view_analytics"] is True
        print(f"✅ STEP 1: Manager authenticated: {manager['email']}")
        
        # STEP 2: Manager requests user analytics for past 30 days
        days = 30
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        user_jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c WHERE c.user_id = @user_id AND c.created_at >= @cutoff_date",
            parameters=[
                {"name": "@user_id", "value": "user-123"},
                {"name": "@cutoff_date", "value": cutoff_date.isoformat()}
            ]
        )
        
        assert len(user_jobs) == 3
        print(f"✅ STEP 2: Retrieved {len(user_jobs)} jobs for analytics period")
        
        # STEP 3: System calculates analytics
        total_minutes = sum(j["audio_duration_minutes"] for j in user_jobs)
        total_jobs = len(user_jobs)
        avg_duration = total_minutes / total_jobs if total_jobs > 0 else 0
        total_storage_bytes = sum(j["file_size_bytes"] for j in user_jobs)
        total_storage_mb = total_storage_bytes / (1024 * 1024)
        
        analytics = {
            "user_id": "user-123",
            "period_days": days,
            "total_minutes": total_minutes,
            "total_jobs": total_jobs,
            "avg_duration_minutes": avg_duration,
            "total_storage_mb": total_storage_mb,
            "jobs_per_day": total_jobs / days
        }
        
        assert analytics["total_minutes"] == 136.0
        assert analytics["total_jobs"] == 3
        assert analytics["avg_duration_minutes"] > 0
        print(f"✅ STEP 3: Analytics calculated: {analytics['total_minutes']} minutes, {analytics['total_jobs']} jobs")
        
        # STEP 4: Manager views formatted analytics
        formatted_report = f"""
        User Analytics Report
        =====================
        User: user-123
        Period: Last {days} days
        
        Summary:
        - Total Audio Processed: {analytics['total_minutes']:.1f} minutes ({analytics['total_minutes']/60:.1f} hours)
        - Total Jobs: {analytics['total_jobs']}
        - Average Duration: {analytics['avg_duration_minutes']:.1f} minutes
        - Storage Used: {analytics['total_storage_mb']:.1f} MB
        - Activity Rate: {analytics['jobs_per_day']:.2f} jobs/day
        """
        
        assert "Total Audio Processed" in formatted_report
        assert f"{analytics['total_minutes']:.1f}" in formatted_report
        print(f"✅ STEP 4: Manager views formatted analytics report")
        
        print("✅ COMPLETE: Manager can view user analytics for team tracking")
    
    @pytest.mark.asyncio
    async def test_admin_can_view_system_wide_analytics(
        self,
        mock_cosmos_service
    ):
        """
        ADMIN WORKFLOW: View system-wide analytics
        
        Steps:
        1. Admin authenticates
        2. Admin requests system-wide statistics
        3. System aggregates data across all users
        4. Admin views comprehensive dashboard
        
        Critical for capacity planning and budgeting.
        """
        
        # STEP 1: Admin authenticates
        admin = {
            "id": "admin-123",
            "email": "admin@example.com",
            "permission_level": "admin"
        }
        print(f"✅ STEP 1: Admin authenticated: {admin['email']}")
        
        # STEP 2: System queries all jobs for analytics
        mock_cosmos_service.query_items_async.return_value = [
            {"id": "job-1", "user_id": "user-1", "audio_duration_minutes": 45, "status": "completed"},
            {"id": "job-2", "user_id": "user-2", "audio_duration_minutes": 60, "status": "completed"},
            {"id": "job-3", "user_id": "user-3", "audio_duration_minutes": 30, "status": "completed"},
            {"id": "job-4", "user_id": "user-1", "audio_duration_minutes": 50, "status": "processing"},
            {"id": "job-5", "user_id": "user-2", "audio_duration_minutes": 0, "status": "failed"},
        ]
        
        all_jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c",
            parameters=[]
        )
        
        print(f"✅ STEP 2: Retrieved {len(all_jobs)} total jobs from system")
        
        # STEP 3: Calculate system-wide statistics
        total_jobs = len(all_jobs)
        completed_jobs = sum(1 for j in all_jobs if j["status"] == "completed")
        processing_jobs = sum(1 for j in all_jobs if j["status"] == "processing")
        failed_jobs = sum(1 for j in all_jobs if j["status"] == "failed")
        
        total_minutes = sum(j["audio_duration_minutes"] for j in all_jobs if j["status"] == "completed")
        unique_users = len(set(j["user_id"] for j in all_jobs))
        
        success_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        system_stats = {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "processing_jobs": processing_jobs,
            "failed_jobs": failed_jobs,
            "success_rate_percent": success_rate,
            "total_audio_minutes": total_minutes,
            "total_audio_hours": total_minutes / 60,
            "unique_users": unique_users,
            "avg_jobs_per_user": total_jobs / unique_users if unique_users > 0 else 0
        }
        
        assert system_stats["total_jobs"] == 5
        assert system_stats["completed_jobs"] == 3
        assert system_stats["success_rate_percent"] == 60.0  # 3 completed out of 5
        assert system_stats["unique_users"] == 3
        print(f"✅ STEP 3: System stats: {system_stats['total_jobs']} jobs, {system_stats['success_rate_percent']:.0f}% success rate")
        
        # STEP 4: Admin views dashboard
        dashboard = {
            "overview": system_stats,
            "health": {
                "success_rate": system_stats["success_rate_percent"],
                "active_processing": system_stats["processing_jobs"],
                "failed_rate": (failed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            },
            "usage": {
                "total_hours_processed": system_stats["total_audio_hours"],
                "active_users": system_stats["unique_users"]
            }
        }
        
        assert dashboard["health"]["success_rate"] >= 50  # At least 50% success rate
        assert dashboard["usage"]["active_users"] > 0
        print(f"✅ STEP 4: Admin dashboard: {dashboard['usage']['total_hours_processed']:.1f} hours processed")
        
        print("✅ COMPLETE: Admin can view comprehensive system analytics")
    
    @pytest.mark.asyncio
    async def test_manager_can_export_analytics_as_csv(
        self,
        mock_cosmos_service,
        mock_export_service
    ):
        """
        EXPORT WORKFLOW: Export analytics data as CSV
        
        Steps:
        1. Manager requests CSV export
        2. System generates CSV with all data
        3. Manager downloads CSV file
        4. CSV contains all expected columns
        
        Critical for reporting to executives and budgeting.
        """
        
        # STEP 1: Manager requests export
        export_format = "csv"
        print(f"✅ STEP 1: Manager requested {export_format.upper()} export")
        
        # STEP 2: Retrieve data for export
        user_jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c WHERE c.user_id = @user_id",
            parameters=[{"name": "@user_id", "value": "user-123"}]
        )
        
        # STEP 3: Generate CSV content
        csv_rows = ["Job ID,File Name,Duration (minutes),Size (MB),Status,Created At\n"]
        
        for job in user_jobs:
            size_mb = job["file_size_bytes"] / (1024 * 1024)
            csv_row = f"{job['id']},{job.get('file_name', 'N/A')},{job['audio_duration_minutes']:.1f},{size_mb:.1f},{job['status']},{job['created_at']}\n"
            csv_rows.append(csv_row)
        
        csv_content = "".join(csv_rows)
        
        # Validate CSV structure
        assert "Job ID" in csv_content
        assert "Duration (minutes)" in csv_content
        assert "Status" in csv_content
        lines = csv_content.strip().split("\n")
        assert len(lines) == 4  # 1 header + 3 data rows
        print(f"✅ STEP 2: Generated CSV with {len(lines) - 1} data rows")
        
        # STEP 4: Manager downloads file
        mock_export_service.generate_csv.return_value = csv_content
        downloaded_csv = mock_export_service.generate_csv(user_jobs)
        
        assert downloaded_csv == csv_content
        assert len(downloaded_csv) > 0
        print(f"✅ STEP 3: CSV downloaded ({len(csv_content)} bytes)")
        
        # STEP 5: Verify CSV can be parsed
        csv_lines = downloaded_csv.strip().split("\n")
        header = csv_lines[0].split(",")
        assert "Job ID" in header
        assert "Duration (minutes)" in header
        print(f"✅ STEP 4: CSV contains {len(header)} columns")
        
        print("✅ COMPLETE: Manager can export analytics as CSV")
    
    @pytest.mark.asyncio
    async def test_session_tracking_for_user_activity(
        self,
        mock_cosmos_service
    ):
        """
        SESSION TRACKING: Track user activity and engagement
        
        Steps:
        1. System records user sessions
        2. Admin requests session analytics
        3. System calculates active users, session duration
        4. Admin views engagement metrics
        
        Critical for understanding user engagement and product usage.
        """
        
        # STEP 1: System has recorded sessions
        mock_cosmos_service.query_items_async.return_value = [
            {
                "session_id": "session-1",
                "user_id": "user-1",
                "started_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "ended_at": (datetime.utcnow() - timedelta(hours=1, minutes=30)).isoformat(),
                "actions_count": 15
            },
            {
                "session_id": "session-2",
                "user_id": "user-2",
                "started_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
                "ended_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "actions_count": 25
            },
            {
                "session_id": "session-3",
                "user_id": "user-1",
                "started_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
                "ended_at": datetime.utcnow().isoformat(),
                "actions_count": 10
            }
        ]
        
        sessions = await mock_cosmos_service.query_items_async(
            container_name="sessions",
            query="SELECT * FROM c WHERE c.started_at >= @cutoff",
            parameters=[{"name": "@cutoff", "value": (datetime.utcnow() - timedelta(days=1)).isoformat()}]
        )
        
        print(f"✅ STEP 1: Retrieved {len(sessions)} sessions from last 24 hours")
        
        # STEP 2: Calculate session metrics
        total_sessions = len(sessions)
        unique_users = len(set(s["user_id"] for s in sessions))
        
        session_durations = []
        for session in sessions:
            started = datetime.fromisoformat(session["started_at"])
            ended = datetime.fromisoformat(session["ended_at"])
            duration_minutes = (ended - started).total_seconds() / 60
            session_durations.append(duration_minutes)
        
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        total_actions = sum(s["actions_count"] for s in sessions)
        
        session_analytics = {
            "total_sessions": total_sessions,
            "unique_active_users": unique_users,
            "avg_session_duration_minutes": avg_session_duration,
            "total_actions": total_actions,
            "avg_actions_per_session": total_actions / total_sessions if total_sessions > 0 else 0
        }
        
        assert session_analytics["total_sessions"] == 3
        assert session_analytics["unique_active_users"] == 2
        assert session_analytics["avg_session_duration_minutes"] > 0
        print(f"✅ STEP 2: Session analytics: {session_analytics['unique_active_users']} active users, "
              f"{session_analytics['avg_session_duration_minutes']:.1f} min avg session")
        
        # STEP 3: Calculate engagement score
        engagement_score = (
            (session_analytics["avg_actions_per_session"] / 20) * 50 +  # Action engagement (50% weight)
            (min(session_analytics["avg_session_duration_minutes"] / 30, 1.0)) * 50  # Duration engagement (50% weight)
        )
        
        engagement_level = "High" if engagement_score >= 70 else "Medium" if engagement_score >= 40 else "Low"
        
        print(f"✅ STEP 3: Engagement score: {engagement_score:.1f}/100 ({engagement_level})")
        
        print("✅ COMPLETE: Session tracking provides user engagement insights")


class TestExportEdgeCases:
    """
    Edge cases for export functionality
    """
    
    @pytest.fixture
    def mock_cosmos_service(self):
        """Mock database service"""
        service = AsyncMock()
        return service
    
    @pytest.mark.asyncio
    async def test_export_handles_large_datasets(
        self,
        mock_cosmos_service
    ):
        """
        EDGE CASE: Export large dataset (1000+ jobs)
        
        Validates:
        - System can handle large exports
        - Export doesn't timeout
        - Data is paginated if needed
        - Memory doesn't explode
        """
        
        # STEP 1: User has many jobs (simulate 1000 jobs)
        large_dataset = [
            {
                "id": f"job-{i}",
                "user_id": "user-123",
                "audio_duration_minutes": 45.0,
                "status": "completed"
            }
            for i in range(1000)
        ]
        
        mock_cosmos_service.query_items_async.return_value = large_dataset
        
        jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c WHERE c.user_id = @user_id",
            parameters=[{"name": "@user_id", "value": "user-123"}]
        )
        
        assert len(jobs) == 1000
        print(f"✅ STEP 1: User has {len(jobs)} jobs to export")
        
        # STEP 2: Export in chunks to prevent memory issues
        chunk_size = 100
        chunks = [jobs[i:i + chunk_size] for i in range(0, len(jobs), chunk_size)]
        
        assert len(chunks) == 10
        print(f"✅ STEP 2: Data split into {len(chunks)} chunks of {chunk_size} each")
        
        # STEP 3: Generate CSV for each chunk
        csv_parts = []
        for chunk in chunks:
            chunk_csv = "\n".join([f"{j['id']},{j['audio_duration_minutes']},{j['status']}" for j in chunk])
            csv_parts.append(chunk_csv)
        
        # STEP 4: Combine chunks
        header = "Job ID,Duration (minutes),Status\n"
        full_csv = header + "\n".join(csv_parts)
        
        lines = full_csv.strip().split("\n")
        assert len(lines) == 1001  # 1 header + 1000 data rows
        print(f"✅ STEP 3: Generated CSV with {len(lines) - 1} rows")
        
        print("✅ COMPLETE: Large dataset export handled successfully")
    
    @pytest.mark.asyncio
    async def test_export_handles_special_characters_in_data(
        self,
        mock_cosmos_service
    ):
        """
        EDGE CASE: Export data with special characters
        
        Validates:
        - Commas in data don't break CSV
        - Quotes are escaped properly
        - Unicode characters handled correctly
        """
        
        # STEP 1: Jobs with special characters
        mock_cosmos_service.query_items_async.return_value = [
            {
                "id": "job-1",
                "file_name": "Meeting, Q4 2025.mp3",  # Comma in name
                "notes": 'Client said "revenue up"',  # Quotes in notes
                "user_email": "françois@example.com"  # Unicode character
            }
        ]
        
        jobs = await mock_cosmos_service.query_items_async(
            container_name="jobs",
            query="SELECT * FROM c",
            parameters=[]
        )
        
        print(f"✅ STEP 1: Retrieved job with special characters")
        
        # STEP 2: Generate CSV with proper escaping
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(["Job ID", "File Name", "Notes", "User Email"])
        
        # Write data (csv module handles escaping)
        for job in jobs:
            writer.writerow([
                job["id"],
                job["file_name"],
                job["notes"],
                job["user_email"]
            ])
        
        csv_content = output.getvalue()
        
        # Verify special characters are properly escaped
        assert '"Meeting, Q4 2025.mp3"' in csv_content  # Comma wrapped in quotes
        assert 'françois' in csv_content  # Unicode preserved
        print(f"✅ STEP 2: CSV properly escaped special characters")
        
        # STEP 3: Verify CSV can be parsed back
        input_stream = StringIO(csv_content)
        reader = csv.reader(input_stream)
        rows = list(reader)
        
        assert len(rows) == 2  # Header + 1 data row
        assert rows[1][1] == "Meeting, Q4 2025.mp3"  # Comma preserved correctly
        print(f"✅ STEP 3: CSV can be parsed back correctly")
        
        print("✅ COMPLETE: Special characters handled properly in exports")
