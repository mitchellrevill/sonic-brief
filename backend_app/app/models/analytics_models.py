from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime


class AnalyticsEventRequest(BaseModel):
    event_type: str
    metadata: Optional[Dict[str, Any]] = None
    job_id: Optional[str] = None


class UserAnalyticsResponse(BaseModel):
    user_id: str
    period_days: int
    start_date: str
    end_date: str
    analytics: Dict[str, Any]


class SystemAnalyticsResponse(BaseModel):
    period_days: int
    start_date: str
    end_date: str
    analytics: Dict[str, Any]


class TranscriptionStats(BaseModel):
    total_minutes: float
    total_jobs: int
    average_job_duration: float


class ActivityStats(BaseModel):
    total_events: int
    login_count: int
    jobs_created: int
    last_activity: Optional[str]


class UsagePatterns(BaseModel):
    most_active_hours: List[int]
    most_used_transcription_method: Optional[str]
    file_upload_count: int
    text_input_count: int


class UserAnalytics(BaseModel):
    transcription_stats: TranscriptionStats
    activity_stats: ActivityStats
    usage_patterns: UsagePatterns


class UserDetailsResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
    permission: str
    source: str
    microsoft_oid: Optional[str]
    tenant_id: Optional[str]
    created_at: str
    last_login: Optional[str]
    is_active: bool
    permission_changed_at: str
    permission_changed_by: str
    permission_history: List[Dict[str, Any]]
    updated_at: str
    analytics: Optional[UserAnalytics] = None


class ExportRequest(BaseModel):
    format: str  # 'csv' or 'pdf'
    filters: Optional[Dict[str, Any]] = None
    date_range: Optional[Dict[str, str]] = None


class ExportResponse(BaseModel):
    status: str
    message: str
    download_url: Optional[str] = None
    filename: Optional[str] = None
