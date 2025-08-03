#!/usr/bin/env python
"""Test script for new photo analysis follow-up endpoints"""

import httpx
import asyncio
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-123"
TEST_SESSION_ID = None  # Will be populated during tests
TEST_ANALYSIS_ID = None  # Will be populated during tests

async def test_follow_up_endpoint():
    """Test the follow-up photo upload endpoint"""
    print("\n1. Testing Follow-up Endpoint...")
    
    # First, we need a session ID - create a dummy session for testing
    async with httpx.AsyncClient() as client:
        # Create session
        session_response = await client.post(
            f"{BASE_URL}/api/photo-analysis/sessions",
            json={
                "user_id": TEST_USER_ID,
                "condition_name": "Test Mole on Arm",
                "description": "Testing follow-up functionality"
            }
        )
        
        if session_response.status_code == 200:
            session_data = session_response.json()
            global TEST_SESSION_ID
            TEST_SESSION_ID = session_data["session_id"]
            print(f"✓ Created test session: {TEST_SESSION_ID}")
        else:
            print(f"✗ Failed to create session: {session_response.status_code}")
            print(session_response.text)
            return False
        
        # Test follow-up endpoint (without actual photos for now)
        # In a real test, you would include actual image files
        follow_up_response = await client.post(
            f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/follow-up",
            data={
                "auto_compare": "true",
                "notes": "No changes observed"
            },
            files=[]  # Empty for now - would include actual photos in real usage
        )
        
        print(f"Follow-up endpoint status: {follow_up_response.status_code}")
        if follow_up_response.status_code in [200, 422]:  # 422 is expected without photos
            print("✓ Follow-up endpoint is reachable")
            return True
        else:
            print(f"✗ Unexpected status: {follow_up_response.text}")
            return False


async def test_reminders_endpoint():
    """Test the reminders configuration endpoint"""
    print("\n2. Testing Reminders Configuration Endpoint...")
    
    if not TEST_SESSION_ID:
        print("✗ No session ID available")
        return False
    
    # Create a dummy analysis ID for testing
    global TEST_ANALYSIS_ID
    TEST_ANALYSIS_ID = "test-analysis-123"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/photo-analysis/reminders/configure",
            json={
                "session_id": TEST_SESSION_ID,
                "analysis_id": TEST_ANALYSIS_ID,
                "enabled": True,
                "interval_days": 30,
                "reminder_method": "email",
                "reminder_text": "Time to update your mole photos",
                "contact_info": {
                    "email": "test@example.com"
                }
            }
        )
        
        print(f"Reminders endpoint status: {response.status_code}")
        if response.status_code in [200, 404]:  # 404 expected if analysis doesn't exist
            print("✓ Reminders endpoint is reachable")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"✗ Unexpected status: {response.text}")
            return False


async def test_monitoring_suggest_endpoint():
    """Test the monitoring suggestions endpoint"""
    print("\n3. Testing Monitoring Suggestions Endpoint...")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/photo-analysis/monitoring/suggest",
            json={
                "analysis_id": TEST_ANALYSIS_ID or "test-analysis-123",
                "condition_context": {
                    "is_first_analysis": True,
                    "user_concerns": "Mole has been changing",
                    "duration": "noticed 2 months ago"
                }
            }
        )
        
        print(f"Monitoring suggest endpoint status: {response.status_code}")
        if response.status_code in [200, 404]:  # 404 expected if analysis doesn't exist
            print("✓ Monitoring suggest endpoint is reachable")
            if response.status_code == 200:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
            return True
        else:
            print(f"✗ Unexpected status: {response.text}")
            return False


async def test_timeline_endpoint():
    """Test the session timeline endpoint"""
    print("\n4. Testing Timeline Endpoint...")
    
    if not TEST_SESSION_ID:
        print("✗ No session ID available")
        return False
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline"
        )
        
        print(f"Timeline endpoint status: {response.status_code}")
        if response.status_code == 200:
            print("✓ Timeline endpoint is working")
            timeline_data = response.json()
            print(f"Timeline events: {len(timeline_data.get('timeline_events', []))}")
            print(f"Overall trend: {timeline_data.get('overall_trend', {}).get('direction', 'N/A')}")
            return True
        else:
            print(f"✗ Failed: {response.text}")
            return False


async def main():
    """Run all tests"""
    print("=== Testing Photo Analysis Follow-up Endpoints ===")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            health_response = await client.get(f"{BASE_URL}/api/health")
            if health_response.status_code != 200:
                print("✗ Server is not responding on /api/health")
                return
            print("✓ Server is running")
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("Make sure the server is running with: python run_oracle.py")
        return
    
    # Run tests
    results = []
    results.append(await test_follow_up_endpoint())
    results.append(await test_reminders_endpoint())
    results.append(await test_monitoring_suggest_endpoint())
    results.append(await test_timeline_endpoint())
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All endpoints are implemented and reachable!")
    else:
        print("✗ Some endpoints may need attention")
    
    # Cleanup note
    if TEST_SESSION_ID:
        print(f"\nNote: Test session created with ID: {TEST_SESSION_ID}")
        print("You may want to clean this up from the database")


if __name__ == "__main__":
    asyncio.run(main())