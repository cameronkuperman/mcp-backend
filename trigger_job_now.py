#!/usr/bin/env python3
"""Trigger a specific job immediately for testing"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import argparse

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

# Import the jobs
from services.background_jobs_v2 import (
    weekly_health_stories_job,
    weekly_ai_predictions_job,
    weekly_health_insights_job,
    weekly_shadow_patterns_job,
    weekly_strategic_moves_job,
    weekly_health_scores_job,
    init_redis,
    cleanup_redis,
    get_all_users,
    batch_processor
)

async def trigger_job(job_name: str, limit_users: int = None):
    """Trigger a specific job immediately"""
    
    jobs = {
        'stories': weekly_health_stories_job,
        'predictions': weekly_ai_predictions_job,
        'insights': weekly_health_insights_job,
        'patterns': weekly_shadow_patterns_job,
        'strategies': weekly_strategic_moves_job,
        'scores': weekly_health_scores_job
    }
    
    if job_name == 'all':
        print(f"🚀 Running ALL jobs at {datetime.now(timezone.utc).isoformat()}")
        for name, job_func in jobs.items():
            print(f"\n{'='*60}")
            print(f"Running {name.upper()}...")
            print(f"{'='*60}")
            try:
                await job_func()
                print(f"✅ {name} completed!")
            except Exception as e:
                print(f"❌ {name} failed: {e}")
        return
    
    if job_name not in jobs:
        print(f"❌ Unknown job: {job_name}")
        print(f"Available jobs: {', '.join(jobs.keys())} or 'all'")
        return
    
    print(f"🚀 Triggering {job_name.upper()} job at {datetime.now(timezone.utc).isoformat()}")
    
    if limit_users:
        print(f"⚠️  Limiting to first {limit_users} users for testing")
        # Temporarily override get_all_users
        original_get_all_users = get_all_users
        async def limited_get_all_users():
            users = await original_get_all_users()
            return users[:limit_users]
        
        # Monkey patch for this run
        import services.background_jobs_v2
        services.background_jobs_v2.get_all_users = limited_get_all_users
    
    try:
        await init_redis()
        await jobs[job_name]()
        print(f"✅ {job_name} job completed successfully!")
    except Exception as e:
        print(f"❌ {job_name} job failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await cleanup_redis()
        await batch_processor.close()

async def quick_test():
    """Quick test with 1 user for each job"""
    print("🧪 QUICK TEST MODE - Testing each job with 1 user")
    
    users = await get_all_users()
    if not users:
        print("No users found!")
        return
    
    test_user = users[0]
    print(f"Test user: {test_user['user_id']}")
    
    import httpx
    API_URL = os.getenv("API_URL", "http://localhost:8000")
    
    tests = [
        ("Health Story", "POST", f"/api/health-story", {"user_id": test_user['user_id']}),
        ("Health Score", "GET", f"/api/health-score/{test_user['user_id']}", None),
        ("AI Dashboard", "GET", f"/api/ai/dashboard-alert/{test_user['user_id']}", None),
    ]
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        for name, method, endpoint, json_data in tests:
            print(f"\n📝 Testing {name}...")
            try:
                if method == "POST":
                    response = await client.post(f"{API_URL}{endpoint}", json=json_data)
                else:
                    response = await client.get(f"{API_URL}{endpoint}")
                
                if response.status_code == 200:
                    print(f"✅ {name}: SUCCESS")
                else:
                    print(f"⚠️  {name}: Status {response.status_code}")
            except Exception as e:
                print(f"❌ {name}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Trigger background jobs manually')
    parser.add_argument('job', nargs='?', default='help',
                      help='Job name: stories, predictions, insights, patterns, strategies, scores, all, or quick')
    parser.add_argument('--limit', type=int, help='Limit to N users for testing')
    
    args = parser.parse_args()
    
    if args.job == 'help':
        print("🎯 Background Job Trigger Tool")
        print("\nUsage:")
        print("  python trigger_job_now.py <job_name> [--limit N]")
        print("\nAvailable jobs:")
        print("  stories     - Generate health stories")
        print("  predictions - Generate AI predictions")
        print("  insights    - Generate health insights")
        print("  patterns    - Generate shadow patterns")
        print("  strategies  - Generate strategic moves")
        print("  scores      - Generate health scores")
        print("  all         - Run all jobs")
        print("  quick       - Quick test with 1 user")
        print("\nExamples:")
        print("  python trigger_job_now.py scores")
        print("  python trigger_job_now.py stories --limit 5")
        print("  python trigger_job_now.py quick")
        return
    
    if args.job == 'quick':
        asyncio.run(quick_test())
    else:
        asyncio.run(trigger_job(args.job, args.limit))

if __name__ == "__main__":
    main()