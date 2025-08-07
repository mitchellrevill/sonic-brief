"""
Test script to validate the analytics endpoint implementation.
This can be run to check if the analytics endpoint structure is correct.
"""

import json
from datetime import datetime, timedelta
import sys
import os

# Add the parent directory to sys.path to import the function_app module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from function_app import get_user_analytics_data
    print("✅ Successfully imported get_user_analytics_data function")
except ImportError as e:
    print(f"❌ Failed to import function: {e}")
    sys.exit(1)

# Mock Cosmos service for testing
class MockCosmosService:
    def __init__(self):
        self.container = MockContainer()

class MockContainer:
    def query_items(self, query, parameters, enable_cross_partition_query=True):
        # Return mock data for testing
        return [
            {
                "id": "job1",
                "user_id": "test-user-123",
                "created_at": "2025-07-27T10:30:00Z",
                "duration_minutes": 15,
                "file_name": "test_audio.mp3",
                "status": "completed"
            },
            {
                "id": "job2", 
                "user_id": "test-user-123",
                "created_at": "2025-07-26T14:15:00Z",
                "duration_minutes": 8,
                "file_name": None,  # Text input
                "status": "completed"
            }
        ]

def test_analytics_endpoint():
    """Test the analytics endpoint with mock data."""
    print("\n🧪 Testing analytics endpoint implementation...")
    
    # Setup test data
    user_id = "test-user-123"
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    days = 30
    
    # Create mock service
    mock_cosmos = MockCosmosService()
    
    # Test the analytics function
    try:
        result = get_user_analytics_data(mock_cosmos, user_id, start_date, end_date, days)
        
        # Validate the structure
        required_fields = ["user_id", "period_days", "start_date", "end_date", "analytics"]
        analytics_fields = ["transcription_stats", "activity_stats", "usage_patterns"]
        transcription_fields = ["total_minutes", "total_jobs", "average_job_duration"]
        activity_fields = ["login_count", "jobs_created", "last_activity"]
        usage_fields = ["most_active_hours", "most_used_transcription_method", "file_upload_count", "text_input_count"]
        
        # Check top-level structure
        for field in required_fields:
            if field not in result:
                print(f"❌ Missing required field: {field}")
                return False
            else:
                print(f"✅ Found required field: {field}")
        
        # Check analytics structure
        analytics = result.get("analytics", {})
        for field in analytics_fields:
            if field not in analytics:
                print(f"❌ Missing analytics field: {field}")
                return False
            else:
                print(f"✅ Found analytics field: {field}")
        
        # Check transcription_stats
        transcription_stats = analytics.get("transcription_stats", {})
        for field in transcription_fields:
            if field not in transcription_stats:
                print(f"❌ Missing transcription_stats field: {field}")
                return False
            else:
                print(f"✅ Found transcription_stats field: {field}")
        
        # Check activity_stats
        activity_stats = analytics.get("activity_stats", {})
        for field in activity_fields:
            if field not in activity_stats:
                print(f"❌ Missing activity_stats field: {field}")
                return False
            else:
                print(f"✅ Found activity_stats field: {field}")
        
        # Check usage_patterns
        usage_patterns = analytics.get("usage_patterns", {})
        for field in usage_fields:
            if field not in usage_patterns:
                print(f"❌ Missing usage_patterns field: {field}")
                return False
            else:
                print(f"✅ Found usage_patterns field: {field}")
        
        # Validate calculated values
        expected_total_jobs = 2
        expected_total_minutes = 23  # 15 + 8
        expected_file_uploads = 1
        expected_text_inputs = 1
        
        if transcription_stats["total_jobs"] != expected_total_jobs:
            print(f"❌ Incorrect total_jobs: expected {expected_total_jobs}, got {transcription_stats['total_jobs']}")
            return False
        
        if transcription_stats["total_minutes"] != expected_total_minutes:
            print(f"❌ Incorrect total_minutes: expected {expected_total_minutes}, got {transcription_stats['total_minutes']}")
            return False
        
        if usage_patterns["file_upload_count"] != expected_file_uploads:
            print(f"❌ Incorrect file_upload_count: expected {expected_file_uploads}, got {usage_patterns['file_upload_count']}")
            return False
        
        if usage_patterns["text_input_count"] != expected_text_inputs:
            print(f"❌ Incorrect text_input_count: expected {expected_text_inputs}, got {usage_patterns['text_input_count']}")
            return False
        
        print("\n📊 Sample analytics response:")
        print(json.dumps(result, indent=2, default=str))
        
        print("\n✅ All tests passed! Analytics endpoint implementation is correct.")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False

if __name__ == "__main__":
    success = test_analytics_endpoint()
    if not success:
        sys.exit(1)
    print("\n🎉 Analytics endpoint implementation validated successfully!")
