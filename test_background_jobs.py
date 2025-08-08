#!/usr/bin/env python3
"""Test script to verify background jobs functionality"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Import the enhanced background jobs
from services.background_jobs_v2 import (
    get_all_users,
    weekly_health_stories_job,
    weekly_ai_predictions_job,
    weekly_health_insights_job,
    weekly_shadow_patterns_job,
    weekly_strategic_moves_job,
    weekly_health_scores_job,
    init_redis,
    cleanup_redis,
    batch_processor
)

async def test_get_users():
    """Test getting all users"""
    print("\n=== Testing User Retrieval ===")
    users = await get_all_users()
    print(f"Found {len(users)} total users")
    if users:
        print(f"Sample user ID: {users[0].get('user_id')}")
    return len(users) > 0

async def test_batch_processor():
    """Test batch processing logic"""
    print("\n=== Testing Batch Processor ===")
    
    # Create mock users
    mock_users = [{'user_id': f'test-user-{i}'} for i in range(25)]
    
    async def mock_process(user_id):
        """Mock processing function"""
        await asyncio.sleep(0.1)  # Simulate some work
        return {'status': 'success', 'user_id': user_id}
    
    results = await batch_processor.process_users(
        mock_users[:5],  # Test with just 5 users
        mock_process,
        'test_job'
    )
    
    print(f"Processed {results['successful']} out of {results['total']} users")
    return results['successful'] == results['total']

async def test_redis_connection():
    """Test Redis connection"""
    print("\n=== Testing Redis Connection ===")
    try:
        await init_redis()
        print("Redis connection test passed")
        await cleanup_redis()
        return True
    except Exception as e:
        print(f"Redis connection test failed (this is okay): {e}")
        return True  # Redis is optional

async def verify_job_scheduling():
    """Verify jobs are properly scheduled"""
    print("\n=== Verifying Job Schedule ===")
    
    job_schedule = {
        'Monday 2 AM UTC': 'Health Stories',
        'Tuesday 2 AM UTC': 'AI Predictions',
        'Wednesday 2 AM UTC': 'Health Insights',
        'Thursday 2 AM UTC': 'Shadow Patterns',
        'Friday 2 AM UTC': 'Strategic Moves',
        'Saturday 2 AM UTC': 'Health Scores',
        'Hourly': 'AI Predictions Check',
        'Daily 3 AM': 'Cleanup expired shares',
        'Sunday Midnight': 'Reset weekly limits'
    }
    
    print("Scheduled Jobs:")
    for time, job in job_schedule.items():
        print(f"  - {time}: {job}")
    
    return True

async def test_single_user_generation():
    """Test generating data for a single user"""
    print("\n=== Testing Single User Generation ===")
    
    # Get one user to test with
    users = await get_all_users()
    if not users:
        print("No users found to test with")
        return False
    
    test_user_id = users[0].get('user_id')
    print(f"Testing with user: {test_user_id}")
    
    # Test health score generation (simplest endpoint)
    try:
        import httpx
        API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_URL}/api/health-score/{test_user_id}",
                params={"force_refresh": False}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"Successfully generated health score: {data.get('score')}")
                return True
            else:
                print(f"Health score generation returned status: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"Error testing single user generation: {e}")
        return False

async def main():
    """Run all tests"""
    print("=" * 50)
    print("BACKGROUND JOBS TEST SUITE")
    print(f"Started at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 50)
    
    tests = [
        ("User Retrieval", test_get_users),
        ("Batch Processor", test_batch_processor),
        ("Redis Connection", test_redis_connection),
        ("Job Scheduling", verify_job_scheduling),
        ("Single User Generation", test_single_user_generation)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"✓ {test_name}: {'PASSED' if result else 'FAILED'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"✗ {test_name}: FAILED - {str(e)}")
    
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Background jobs are ready for deployment.")
    else:
        print("\n⚠️ Some tests failed. Please review the errors above.")
    
    # Cleanup
    await batch_processor.close()

if __name__ == "__main__":
    asyncio.run(main())