#!/usr/bin/env python3
"""
Job Sharing Test Script for Existing Users

This script tests job sharing functionality using your existing users.
It assumes you already have users in your Cosmos DB and will work with them.
"""

import requests
import json
import sys
from typing import Dict, Any, List

# API Base URL - Update this to your deployed backend URL
API_BASE_URL = input("Enter your backend URL (e.g., https://sonic-web-app-h7hna2g2b3b3aghw.uksouth-01.azurewebsites.net): ").strip()
if not API_BASE_URL:
    API_BASE_URL = "http://localhost:8000"

print(f"Using API URL: {API_BASE_URL}")

class JobSharingTester:
    def __init__(self):
        self.tokens = {}
        self.users = {}
        self.test_job_id = None

    def login_user(self, email: str, password: str) -> str:
        """Login a user and get their access token"""
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/auth/login",
                json={"email": email, "password": password}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                if token:
                    self.tokens[email] = token
                    print(f"✓ Successfully logged in user: {email}")
                    return token
                else:
                    print(f"✗ No token received for {email}")
                    return None
            else:
                print(f"✗ Login failed for {email}: {response.text}")
                return None
        except Exception as e:
            print(f"✗ Error logging in {email}: {str(e)}")
            return None

    def get_user_jobs(self, email: str) -> List[Dict]:
        """Get jobs for a user"""
        token = self.tokens.get(email)
        if not token:
            print(f"No token for {email}")
            return []
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/jobs",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                jobs = data.get("jobs", [])
                print(f"✓ User {email} has {len(jobs)} jobs")
                return jobs
            else:
                print(f"✗ Failed to get jobs for {email}: {response.text}")
                return []
        except Exception as e:
            print(f"✗ Error getting jobs for {email}: {str(e)}")
            return []

    def share_job(self, owner_email: str, job_id: str, target_email: str, permission: str = "view") -> bool:
        """Share a job with another user"""
        token = self.tokens.get(owner_email)
        if not token:
            print(f"No token for {owner_email}")
            return False
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/jobs/{job_id}/share",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "target_user_email": target_email,
                    "permission_level": permission,
                    "message": f"Sharing job for testing purposes with {permission} permission"
                }
            )
            
            if response.status_code == 200:
                print(f"✓ Successfully shared job {job_id} with {target_email} ({permission})")
                return True
            else:
                print(f"✗ Failed to share job {job_id} with {target_email}: {response.text}")
                return False
        except Exception as e:
            print(f"✗ Error sharing job {job_id}: {str(e)}")
            return False

    def get_shared_jobs(self, email: str) -> Dict:
        """Get shared jobs for a user"""
        token = self.tokens.get(email)
        if not token:
            print(f"No token for {email}")
            return {}
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/jobs/shared",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                shared_count = len(data.get("shared_jobs", []))
                owned_shared_count = len(data.get("owned_jobs_shared_with_others", []))
                print(f"✓ User {email} has {shared_count} shared jobs and {owned_shared_count} owned jobs shared with others")
                return data
            else:
                print(f"✗ Failed to get shared jobs for {email}: {response.text}")
                return {}
        except Exception as e:
            print(f"✗ Error getting shared jobs for {email}: {str(e)}")
            return {}

    def get_job_sharing_info(self, email: str, job_id: str) -> Dict:
        """Get sharing information for a specific job"""
        token = self.tokens.get(email)
        if not token:
            print(f"No token for {email}")
            return {}
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/jobs/{job_id}/sharing-info",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                permission = data.get("user_permission", "none")
                is_owner = data.get("is_owner", False)
                shared_count = data.get("total_shares", 0)
                print(f"✓ User {email} - Job {job_id}: Permission={permission}, Owner={is_owner}, Shared with {shared_count} users")
                return data
            else:
                print(f"✗ Access denied or error for {email} on job {job_id}: {response.text}")
                return {}
        except Exception as e:
            print(f"✗ Error getting job sharing info for {email}: {str(e)}")
            return {}

    def test_job_access(self, email: str, job_id: str) -> bool:
        """Test if a user can access a job by trying to get its transcription"""
        token = self.tokens.get(email)
        if not token:
            print(f"No token for {email}")
            return False
        
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/jobs/transcription/{job_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                print(f"✓ User {email} can access job {job_id}")
                return True
            elif response.status_code == 403:
                print(f"✗ User {email} access denied to job {job_id}")
                return False
            else:
                print(f"? User {email} - job {job_id} response: {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error testing access for {email}: {str(e)}")
            return False

    def run_interactive_test(self):
        """Run an interactive test session"""
        print("\n=== Job Sharing Test ===")
        print("This will test job sharing with your existing users.")
        print()
        
        # Get user credentials
        print("Please provide credentials for two existing users:")
        
        # User 1 (job owner)
        owner_email = input("Owner email: ").strip()
        owner_password = input("Owner password: ").strip()
        
        # User 2 (target user)
        target_email = input("Target user email: ").strip()
        target_password = input("Target user password: ").strip()
        
        print("\n--- Step 1: Login users ---")
        owner_token = self.login_user(owner_email, owner_password)
        target_token = self.login_user(target_email, target_password)
        
        if not owner_token or not target_token:
            print("Failed to login users. Exiting.")
            return
        
        print("\n--- Step 2: Get owner's jobs ---")
        owner_jobs = self.get_user_jobs(owner_email)
        
        if not owner_jobs:
            print("Owner has no jobs to share. Exiting.")
            return
        
        # Show available jobs
        print("\nAvailable jobs to share:")
        for i, job in enumerate(owner_jobs):
            print(f"{i+1}. Job ID: {job.get('id', 'N/A')} - Status: {job.get('status', 'N/A')}")
        
        # Let user select a job
        try:
            choice = int(input(f"\nSelect job to share (1-{len(owner_jobs)}): ")) - 1
            selected_job = owner_jobs[choice]
            job_id = selected_job.get('id')
        except (ValueError, IndexError):
            print("Invalid selection. Using first job.")
            job_id = owner_jobs[0].get('id')
        
        self.test_job_id = job_id
        print(f"\nSelected job: {job_id}")
        
        print("\n--- Step 3: Test initial access ---")
        print("Before sharing:")
        self.test_job_access(owner_email, job_id)
        self.test_job_access(target_email, job_id)
        
        print("\n--- Step 4: Share the job ---")
        permission = input("Enter permission level (view/edit/admin) [default: view]: ").strip() or "view"
        success = self.share_job(owner_email, job_id, target_email, permission)
        
        if not success:
            print("Failed to share job. Exiting.")
            return
        
        print("\n--- Step 5: Test access after sharing ---")
        print("After sharing:")
        self.test_job_access(owner_email, job_id)
        self.test_job_access(target_email, job_id)
        
        print("\n--- Step 6: Get sharing information ---")
        self.get_job_sharing_info(owner_email, job_id)
        self.get_job_sharing_info(target_email, job_id)
        
        print("\n--- Step 7: Get shared jobs ---")
        self.get_shared_jobs(owner_email)
        self.get_shared_jobs(target_email)
        
        print("\n=== Test completed! ===")
        print("Job sharing functionality appears to be working.")

def main():
    """Main function"""
    print("Job Sharing Test with Existing Users")
    print("====================================")
    print()
    
    # Test backend connectivity
    try:
        response = requests.get(f"{API_BASE_URL}/docs", timeout=10)
        print("✓ Backend is accessible")
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to backend: {e}")
        print("Please check your backend URL and ensure it's running.")
        return
    
    tester = JobSharingTester()
    tester.run_interactive_test()

if __name__ == "__main__":
    main()
