#!/usr/bin/env python3
"""
Job Sharing API Test Script

This script tests the job sharing functionality via HTTP API calls only.
No direct database access - works with deployed backend.

Usage:
1. Update BACKEND_URL to your deployed backend
2. Update test credentials if needed
3. Run: python test_job_sharing_api.py
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

# Configuration
BACKEND_URL = "https://your-deployed-backend.azurewebsites.net"  # Update this
TEST_USERS = [
    {"email": "owner@test.com", "password": "TestPass123!"},
    {"email": "viewer@test.com", "password": "TestPass123!"},
    {"email": "editor@test.com", "password": "TestPass123!"}
]

class JobSharingAPITest:
    def __init__(self, backend_url: str):
        self.backend_url = backend_url.rstrip('/')
        self.tokens = {}
        self.test_job_id = None
        
    def register_user(self, email: str, password: str) -> bool:
        """Register a test user"""
        print(f"Registering user: {email}")
        
        response = requests.post(
            f"{self.backend_url}/api/auth/register",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == 200:
                print(f"✓ User {email} registered successfully")
                return True
            elif "already registered" in data.get("message", ""):
                print(f"✓ User {email} already exists")
                return True
        
        print(f"✗ Failed to register {email}: {response.text}")
        return False
    
    def login_user(self, email: str, password: str) -> Optional[str]:
        """Login user and get token"""
        print(f"Logging in user: {email}")
        
        response = requests.post(
            f"{self.backend_url}/api/auth/login",
            json={"email": email, "password": password}
        )
        
        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")
            if token:
                print(f"✓ Login successful for {email}")
                return token
        
        print(f"✗ Login failed for {email}: {response.text}")
        return None
    
    def create_test_job(self, token: str) -> Optional[str]:
        """Create a test job via file upload"""
        print("Creating test job...")
        
        # Create a simple test file
        test_content = "This is test content for job sharing functionality testing."
        
        files = {
            'file': ('test_sharing.txt', test_content.encode(), 'text/plain')
        }
        data = {
            'prompt_category_id': 'test_category',
            'prompt_subcategory_id': 'test_subcategory'
        }
        
        response = requests.post(
            f"{self.backend_url}/api/upload",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
            data=data
        )
        
        if response.status_code == 200:
            data = response.json()
            job_id = data.get("job_id")
            if job_id:
                print(f"✓ Test job created: {job_id}")
                return job_id
        
        print(f"✗ Failed to create test job: {response.text}")
        return None
    
    def share_job(self, owner_token: str, job_id: str, target_email: str, permission: str) -> bool:
        """Share a job with another user"""
        print(f"Sharing job {job_id} with {target_email} ({permission} permission)")
        
        response = requests.post(
            f"{self.backend_url}/api/jobs/{job_id}/share",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={
                "target_user_email": target_email,
                "permission_level": permission,
                "message": f"Test sharing with {permission} permission"
            }
        )
        
        if response.status_code == 200:
            print(f"✓ Successfully shared job with {target_email}")
            return True
        
        print(f"✗ Failed to share job with {target_email}: {response.text}")
        return False
    
    def get_shared_jobs(self, token: str) -> Dict[str, Any]:
        """Get jobs shared with user"""
        response = requests.get(
            f"{self.backend_url}/api/jobs/shared",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            return response.json()
        
        print(f"✗ Failed to get shared jobs: {response.text}")
        return {}
    
    def get_job_sharing_info(self, token: str, job_id: str) -> Dict[str, Any]:
        """Get sharing info for a job"""
        response = requests.get(
            f"{self.backend_url}/api/jobs/{job_id}/sharing-info",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            return response.json()
        
        return {"error": response.text, "status_code": response.status_code}
    
    def test_job_access(self, token: str, job_id: str) -> bool:
        """Test if user can access a job"""
        response = requests.get(
            f"{self.backend_url}/api/jobs?job_id={job_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            return len(jobs) > 0
        
        return False
    
    def run_tests(self) -> bool:
        """Run all job sharing tests"""
        print("=== Job Sharing API Tests ===\n")
        
        # Step 1: Register and login users
        print("1. Setting up test users...")
        for user in TEST_USERS:
            if not self.register_user(user["email"], user["password"]):
                return False
            
            token = self.login_user(user["email"], user["password"])
            if not token:
                return False
            
            self.tokens[user["email"]] = token
        
        print()
        
        # Step 2: Create test job
        print("2. Creating test job...")
        owner_email = TEST_USERS[0]["email"]
        owner_token = self.tokens[owner_email]
        
        self.test_job_id = self.create_test_job(owner_token)
        if not self.test_job_id:
            return False
        
        print()
        
        # Step 3: Test job sharing
        print("3. Testing job sharing...")
        
        # Share with viewer
        if not self.share_job(owner_token, self.test_job_id, TEST_USERS[1]["email"], "view"):
            return False
        
        # Share with editor
        if not self.share_job(owner_token, self.test_job_id, TEST_USERS[2]["email"], "edit"):
            return False
        
        print()
        
        # Step 4: Test shared job retrieval
        print("4. Testing shared job access...")
        
        for i, user in enumerate(TEST_USERS):
            email = user["email"]
            token = self.tokens[email]
            
            # Test getting shared jobs
            shared_data = self.get_shared_jobs(token)
            if i == 0:  # Owner
                owned_shared = shared_data.get("owned_jobs_shared_with_others", [])
                print(f"✓ Owner has {len(owned_shared)} jobs shared with others")
            else:  # Shared users
                shared_jobs = shared_data.get("shared_jobs", [])
                print(f"✓ {email} has access to {len(shared_jobs)} shared jobs")
            
            # Test job access via regular jobs endpoint
            has_access = self.test_job_access(token, self.test_job_id)
            print(f"✓ {email} can access job via jobs endpoint: {has_access}")
            
            # Test sharing info
            sharing_info = self.get_job_sharing_info(token, self.test_job_id)
            if "error" not in sharing_info:
                permission = sharing_info.get("user_permission", "none")
                is_owner = sharing_info.get("is_owner", False)
                print(f"✓ {email} - Permission: {permission}, Is Owner: {is_owner}")
            else:
                print(f"✗ {email} - Error getting sharing info: {sharing_info['error']}")
        
        print()
        
        # Step 5: Test permission levels
        print("5. Testing permission-based access...")
        
        # Test that viewer can access but not edit
        viewer_token = self.tokens[TEST_USERS[1]["email"]]
        sharing_info = self.get_job_sharing_info(viewer_token, self.test_job_id)
        if sharing_info.get("user_permission") == "view":
            print("✓ Viewer has correct 'view' permission")
        else:
            print(f"✗ Viewer permission incorrect: {sharing_info.get('user_permission')}")
        
        # Test that editor has edit permission
        editor_token = self.tokens[TEST_USERS[2]["email"]]
        sharing_info = self.get_job_sharing_info(editor_token, self.test_job_id)
        if sharing_info.get("user_permission") == "edit":
            print("✓ Editor has correct 'edit' permission")
        else:
            print(f"✗ Editor permission incorrect: {sharing_info.get('user_permission')}")
        
        print()
        print("=== All Tests Completed ===")
        return True
    
    def cleanup_test_job(self):
        """Clean up test job (if API supports it)"""
        if self.test_job_id and TEST_USERS:
            print(f"\nNote: Test job {self.test_job_id} created. You may want to clean it up manually.")

def main():
    print("Job Sharing API Test")
    print("===================")
    print(f"Testing against: {BACKEND_URL}")
    print()
    
    # Check if backend is accessible
    try:
        response = requests.get(f"{BACKEND_URL}/docs", timeout=10)
        if response.status_code == 200:
            print("✓ Backend is accessible")
        else:
            print(f"⚠️ Backend returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to backend: {e}")
        print("Please update BACKEND_URL in the script and ensure backend is running.")
        return False
    
    print()
    
    # Run tests
    tester = JobSharingAPITest(BACKEND_URL)
    success = tester.run_tests()
    
    if success:
        print("🎉 All tests passed! Job sharing functionality is working.")
    else:
        print("❌ Some tests failed. Check the output above for details.")
    
    tester.cleanup_test_job()
    return success

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BACKEND_URL = sys.argv[1]
        print(f"Using backend URL from command line: {BACKEND_URL}")
    
    success = main()
    sys.exit(0 if success else 1)
