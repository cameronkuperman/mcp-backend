#!/usr/bin/env python3
"""Manual testing script for background jobs - Run individual jobs on demand"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Import the jobs
from services.background_jobs_v2 import (
    get_all_users,
    weekly_health_stories_job,
    weekly_ai_predictions_job,
    weekly_health_insights_job,
    weekly_shadow_patterns_job,
    weekly_strategic_moves_job,
    weekly_health_scores_job,
    batch_processor,
    init_redis,
    cleanup_redis
)

async def test_single_user(user_id: str = None):
    """Test jobs for a single user"""
    print(f"\n{'='*60}")
    print("TESTING SINGLE USER")
    print(f"{'='*60}")
    
    # Get a user if not provided
    if not user_id:
        users = await get_all_users()
        if users:
            user_id = users[0]['user_id']
            print(f"Using first user: {user_id}")
        else:
            print("No users found!")
            return
    
    # Test each endpoint
    import httpx
    API_URL = os.getenv("API_URL", "http://localhost:8000")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        
        # 1. Health Story
        print("\n📖 Testing Health Story Generation...")
        try:
            response = await client.post(
                f"{API_URL}/api/health-story",
                json={"user_id": user_id}
            )
            print(f"Health Story: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Story generated: {len(data.get('story', ''))} characters")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 2. Health Score
        print("\n📊 Testing Health Score Generation...")
        try:
            response = await client.get(
                f"{API_URL}/api/health-score/{user_id}",
                params={"force_refresh": True}
            )
            print(f"Health Score: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Score: {data.get('score')}/100")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 3. AI Predictions
        print("\n🔮 Testing AI Predictions...")
        for pred_type in ['dashboard-alert', 'predictions/immediate']:
            try:
                endpoint = f"/api/ai/{pred_type}/{user_id}"
                response = await client.get(
                    f"{API_URL}{endpoint}",
                    params={"force_refresh": True}
                )
                print(f"{pred_type}: {response.status_code}")
                if response.status_code == 200:
                    print(f"✅ {pred_type} generated")
            except Exception as e:
                print(f"❌ {pred_type} error: {e}")

async def test_batch_processing():
    """Test batch processing with a small number of users"""
    print(f"\n{'='*60}")
    print("TESTING BATCH PROCESSING (First 3 Users)")
    print(f"{'='*60}")
    
    users = await get_all_users()
    if not users:
        print("No users found!")
        return
    
    # Test with just 3 users
    test_users = users[:3]
    print(f"Testing with {len(test_users)} users")
    
    async def mock_health_score(user_id: str):
        """Generate health score for testing"""
        import httpx
        API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_URL}/api/health-score/{user_id}",
                params={"force_refresh": False}
            )
            if response.status_code == 200:
                return {'status': 'success', 'score': response.json().get('score')}
            else:
                raise Exception(f"Failed with status {response.status_code}")
    
    # Process the batch
    results = await batch_processor.process_users(
        test_users,
        mock_health_score,
        'test_health_scores'
    )
    
    print(f"\nResults:")
    print(f"✅ Successful: {results['successful']}")
    print(f"❌ Failed: {results['failed']}")
    print(f"📊 Total: {results['total']}")

async def test_specific_job(job_name: str):
    """Test a specific job"""
    print(f"\n{'='*60}")
    print(f"TESTING {job_name.upper()} JOB")
    print(f"{'='*60}")
    
    jobs = {
        'stories': weekly_health_stories_job,
        'predictions': weekly_ai_predictions_job,
        'insights': weekly_health_insights_job,
        'patterns': weekly_shadow_patterns_job,
        'strategies': weekly_strategic_moves_job,
        'scores': weekly_health_scores_job
    }
    
    if job_name not in jobs:
        print(f"Unknown job: {job_name}")
        print(f"Available jobs: {', '.join(jobs.keys())}")
        return
    
    print(f"Running {job_name} job...")
    print("NOTE: This will process ALL users! Press Ctrl+C to cancel in 3 seconds...")
    await asyncio.sleep(3)
    
    try:
        await jobs[job_name]()
        print(f"✅ {job_name} job completed!")
    except Exception as e:
        print(f"❌ {job_name} job failed: {e}")

async def main():
    """Main test menu"""
    print("="*60)
    print("BACKGROUND JOBS MANUAL TESTER")
    print("="*60)
    print("\nOptions:")
    print("1. Test single user (all endpoints)")
    print("2. Test batch processing (3 users)")
    print("3. Test specific job (all users)")
    print("4. Run all tests")
    print("5. Exit")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    # Initialize Redis
    await init_redis()
    
    try:
        if choice == '1':
            user_id = input("Enter user_id (or press Enter for first user): ").strip()
            await test_single_user(user_id if user_id else None)
            
        elif choice == '2':
            await test_batch_processing()
            
        elif choice == '3':
            print("\nAvailable jobs: stories, predictions, insights, patterns, strategies, scores")
            job_name = input("Enter job name: ").strip().lower()
            await test_specific_job(job_name)
            
        elif choice == '4':
            await test_single_user()
            await test_batch_processing()
            print("\n✅ All tests completed!")
            
        elif choice == '5':
            print("Exiting...")
        else:
            print("Invalid choice!")
    
    finally:
        # Cleanup
        await cleanup_redis()
        await batch_processor.close()
        print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(main())