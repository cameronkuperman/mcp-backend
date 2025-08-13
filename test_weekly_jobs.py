#!/usr/bin/env python3
"""
Test script for weekly job endpoints
Tests that the updated jobs correctly call the health analysis endpoints
"""

import asyncio
import os
from datetime import datetime, date, timedelta
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client
import json

# Load environment variables
load_dotenv()

# Initialize Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# API URL
API_URL = os.getenv("API_URL", "http://localhost:8000")

def get_current_week_monday() -> date:
    """Get Monday of the current week"""
    today = date.today()
    days_since_monday = today.weekday()
    return today - timedelta(days=days_since_monday)

async def test_single_user(user_id: str):
    """Test all three endpoints for a single user"""
    print(f"\n{'='*60}")
    print(f"Testing Weekly Jobs for User: {user_id}")
    print(f"{'='*60}")
    
    week_of = get_current_week_monday()
    results = {}
    
    # Test 1: Health Insights
    print("\n1. Testing Health Insights Generation...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{API_URL}/api/generate-insights/{user_id}",
                json={"force_refresh": True}
            )
            
            if response.status_code == 200:
                data = response.json()
                insights = data.get('data', [])
                print(f"   ✅ Success! Generated {len(insights)} insights")
                
                # Show sample insight
                if insights:
                    print(f"   Sample: {insights[0].get('title', 'No title')}")
                    print(f"   Type: {insights[0].get('type', 'unknown')}")
                    print(f"   Confidence: {insights[0].get('confidence', 0)}%")
                
                results['insights'] = len(insights)
            else:
                print(f"   ❌ Failed with status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results['insights'] = 0
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        results['insights'] = 0
    
    # Test 2: Shadow Patterns
    print("\n2. Testing Shadow Patterns Generation...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{API_URL}/api/generate-shadow-patterns/{user_id}",
                json={"force_refresh": True}
            )
            
            if response.status_code == 200:
                data = response.json()
                patterns = data.get('data', [])
                print(f"   ✅ Success! Generated {len(patterns)} shadow patterns")
                
                # Show sample pattern
                if patterns:
                    print(f"   Sample: {patterns[0].get('name', 'No name')}")
                    print(f"   Category: {patterns[0].get('category', 'unknown')}")
                    print(f"   Significance: {patterns[0].get('significance', 'unknown')}")
                
                results['patterns'] = len(patterns)
            else:
                print(f"   ❌ Failed with status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results['patterns'] = 0
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        results['patterns'] = 0
    
    # Test 3: Strategic Moves
    print("\n3. Testing Strategic Moves Generation...")
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{API_URL}/api/generate-strategies/{user_id}",
                json={"force_refresh": True}
            )
            
            if response.status_code == 200:
                data = response.json()
                strategies = data.get('data', [])
                print(f"   ✅ Success! Generated {len(strategies)} strategic moves")
                
                # Show sample strategy
                if strategies:
                    print(f"   Sample: {strategies[0].get('strategy', 'No strategy')}")
                    print(f"   Type: {strategies[0].get('type', 'unknown')}")
                    print(f"   Priority: {strategies[0].get('priority', 0)}/10")
                
                results['strategies'] = len(strategies)
            else:
                print(f"   ❌ Failed with status {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                results['strategies'] = 0
                
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        results['strategies'] = 0
    
    # Check database for stored data
    print("\n4. Verifying Database Storage...")
    
    # Check insights table
    insights_db = supabase.table('health_insights').select('id').eq(
        'user_id', user_id
    ).eq('week_of', week_of.isoformat()).execute()
    print(f"   Health Insights in DB: {len(insights_db.data)} records")
    
    # Check patterns table
    patterns_db = supabase.table('shadow_patterns').select('id').eq(
        'user_id', user_id
    ).eq('week_of', week_of.isoformat()).execute()
    print(f"   Shadow Patterns in DB: {len(patterns_db.data)} records")
    
    # Check strategies table
    strategies_db = supabase.table('strategic_moves').select('id').eq(
        'user_id', user_id
    ).eq('week_of', week_of.isoformat()).execute()
    print(f"   Strategic Moves in DB: {len(strategies_db.data)} records")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY:")
    print(f"  Insights:   {results['insights']} generated")
    print(f"  Patterns:   {results['patterns']} generated")
    print(f"  Strategies: {results['strategies']} generated")
    
    success = all(v > 0 for v in results.values())
    if success:
        print(f"\n✅ ALL TESTS PASSED for user {user_id}!")
    else:
        print(f"\n⚠️  Some tests failed for user {user_id}")
    
    return results

async def test_batch_processing():
    """Test processing multiple users like the actual job does"""
    print(f"\n{'='*60}")
    print("Testing Batch Processing (Like Weekly Jobs)")
    print(f"{'='*60}")
    
    # Get a few test users
    result = supabase.table('medical').select('id').limit(3).execute()
    users = [{'user_id': record['id']} for record in (result.data or [])]
    
    if not users:
        print("❌ No users found in database!")
        return
    
    print(f"Found {len(users)} test users")
    
    # Process each user
    all_results = []
    for user in users:
        user_id = user['user_id']
        print(f"\nProcessing user {user_id[:8]}...")
        results = await test_single_user(user_id)
        all_results.append(results)
        
        # Small delay between users (like the real job)
        await asyncio.sleep(2)
    
    # Final summary
    print(f"\n{'='*60}")
    print("BATCH PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Processed {len(all_results)} users")
    
    total_insights = sum(r['insights'] for r in all_results)
    total_patterns = sum(r['patterns'] for r in all_results)
    total_strategies = sum(r['strategies'] for r in all_results)
    
    print(f"Total Insights Generated:   {total_insights}")
    print(f"Total Patterns Generated:   {total_patterns}")
    print(f"Total Strategies Generated: {total_strategies}")

async def main():
    """Main test function"""
    print("="*60)
    print("WEEKLY JOB ENDPOINT TESTER")
    print("="*60)
    
    # First check if API is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/api/health")
            if response.status_code != 200:
                print(f"❌ API is not responding at {API_URL}")
                print("Please start the API with: python run_oracle.py")
                return
    except Exception as e:
        print(f"❌ Cannot connect to API at {API_URL}")
        print(f"Error: {e}")
        print("Please start the API with: python run_oracle.py")
        return
    
    print(f"✅ API is running at {API_URL}")
    
    # Get a test user
    result = supabase.table('medical').select('id').limit(1).execute()
    if not result.data:
        print("❌ No users found in database!")
        return
    
    test_user_id = result.data[0]['id']
    
    # Run tests
    print("\nRunning tests...")
    
    # Test single user
    await test_single_user(test_user_id)
    
    # Ask if user wants to test batch processing
    print("\n" + "="*60)
    response = input("Test batch processing with multiple users? (y/n): ")
    if response.lower() == 'y':
        await test_batch_processing()
    
    print("\n✅ Testing complete!")

if __name__ == "__main__":
    asyncio.run(main())