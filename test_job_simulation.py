#!/usr/bin/env python3
"""
Simulate what the weekly jobs do - test the exact flow
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
API_URL = "http://localhost:8000"

def get_current_week_monday() -> date:
    """Get Monday of the current week"""
    today = date.today()
    days_since_monday = today.weekday()
    return today - timedelta(days=days_since_monday)

async def simulate_insights_job(user_id: str):
    """Simulate exactly what the insights job does"""
    print(f"\nSimulating Health Insights Job for {user_id[:8]}...")
    week_of = get_current_week_monday()
    
    # This is exactly what the job does
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{API_URL}/api/generate-insights/{user_id}",
                json={"force_refresh": True}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Store insights - exactly as the job does
                insights = data.get('data', [])  # Changed from 'insights' to 'data'
                stored_count = 0
                
                for insight in insights:
                    try:
                        result = supabase.table('health_insights').insert({
                            'user_id': user_id,
                            'insight_type': insight.get('type', 'neutral'),
                            'title': insight.get('title', 'Health Insight'),
                            'description': insight.get('description', ''),
                            'confidence': insight.get('confidence', 70),
                            'week_of': week_of.isoformat(),
                            'generation_method': 'weekly'
                        }).execute()
                        stored_count += 1
                    except Exception as e:
                        print(f"  Error storing insight: {e}")
                
                print(f"  ✅ Generated {len(insights)} insights, stored {stored_count}")
                return {'status': 'success', 'count': len(insights)}
            else:
                print(f"  ❌ API returned {response.status_code}")
                return {'status': 'failed'}
                
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}

async def simulate_patterns_job(user_id: str):
    """Simulate exactly what the patterns job does"""
    print(f"\nSimulating Shadow Patterns Job for {user_id[:8]}...")
    week_of = get_current_week_monday()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{API_URL}/api/generate-shadow-patterns/{user_id}",
                json={"force_refresh": True}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Store patterns - exactly as the job does
                patterns = data.get('data', [])  # Changed from 'shadow_patterns' to 'data'
                stored_count = 0
                
                for pattern in patterns:
                    try:
                        # Map the fields correctly
                        result = supabase.table('shadow_patterns').insert({
                            'user_id': user_id,
                            'pattern_name': pattern.get('pattern_name') or pattern.get('name', 'Unknown Pattern'),
                            'pattern_category': pattern.get('pattern_category') or pattern.get('category'),
                            'last_seen_description': pattern.get('last_seen_description') or pattern.get('description', ''),
                            'significance': pattern.get('significance', 'medium'),
                            'last_mentioned_date': pattern.get('last_mentioned_date') or pattern.get('last_seen'),
                            'days_missing': pattern.get('days_missing', 0),
                            'week_of': week_of.isoformat(),
                            'generation_method': 'weekly'
                        }).execute()
                        stored_count += 1
                    except Exception as e:
                        print(f"  Error storing pattern: {e}")
                
                print(f"  ✅ Generated {len(patterns)} patterns, stored {stored_count}")
                return {'status': 'success', 'count': len(patterns)}
            else:
                print(f"  ❌ API returned {response.status_code}")
                return {'status': 'failed'}
                
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}

async def simulate_strategies_job(user_id: str):
    """Simulate exactly what the strategies job does"""
    print(f"\nSimulating Strategic Moves Job for {user_id[:8]}...")
    week_of = get_current_week_monday()
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{API_URL}/api/generate-strategies/{user_id}",
                json={"force_refresh": True}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Store strategies - exactly as the job does
                strategies = data.get('data', [])  # Changed from 'strategic_moves' to 'data'
                stored_count = 0
                
                for idx, strategy in enumerate(strategies):
                    try:
                        result = supabase.table('strategic_moves').insert({
                            'user_id': user_id,
                            'strategy': strategy.get('strategy', 'Health Strategy'),
                            'strategy_type': strategy.get('strategy_type') or strategy.get('type', 'optimization'),
                            'priority': strategy.get('priority', 5),
                            'rationale': strategy.get('rationale'),
                            'expected_outcome': strategy.get('expected_outcome'),
                            'week_of': week_of.isoformat(),
                            'generation_method': 'weekly'
                        }).execute()
                        stored_count += 1
                    except Exception as e:
                        print(f"  Error storing strategy: {e}")
                
                print(f"  ✅ Generated {len(strategies)} strategies, stored {stored_count}")
                return {'status': 'success', 'count': len(strategies)}
            else:
                print(f"  ❌ API returned {response.status_code}")
                return {'status': 'failed'}
                
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return {'status': 'error', 'error': str(e)}

async def main():
    """Test the job simulation"""
    print("="*60)
    print("WEEKLY JOB SIMULATION")
    print("="*60)
    
    # Use a test user with data
    test_user = "802ba1fe-7dad-4a54-8681-32239f11fb37"
    
    # Clear existing data for this week
    week_of = get_current_week_monday()
    print(f"\nClearing existing data for week of {week_of}...")
    
    supabase.table('health_insights').delete().eq(
        'user_id', test_user
    ).eq('week_of', week_of.isoformat()).execute()
    
    supabase.table('shadow_patterns').delete().eq(
        'user_id', test_user
    ).eq('week_of', week_of.isoformat()).execute()
    
    supabase.table('strategic_moves').delete().eq(
        'user_id', test_user
    ).eq('week_of', week_of.isoformat()).execute()
    
    print("Cleared existing data")
    
    # Run simulations
    await simulate_insights_job(test_user)
    await simulate_patterns_job(test_user)
    await simulate_strategies_job(test_user)
    
    # Check what's in the database
    print("\n" + "="*60)
    print("VERIFYING DATABASE")
    print("="*60)
    
    insights = supabase.table('health_insights').select('*').eq(
        'user_id', test_user
    ).eq('week_of', week_of.isoformat()).execute()
    print(f"Health Insights: {len(insights.data)} records")
    if insights.data:
        print(f"  Sample: {insights.data[0]['title']}")
    
    patterns = supabase.table('shadow_patterns').select('*').eq(
        'user_id', test_user
    ).eq('week_of', week_of.isoformat()).execute()
    print(f"Shadow Patterns: {len(patterns.data)} records")
    if patterns.data:
        print(f"  Sample: {patterns.data[0]['pattern_name']}")
    
    strategies = supabase.table('strategic_moves').select('*').eq(
        'user_id', test_user
    ).eq('week_of', week_of.isoformat()).execute()
    print(f"Strategic Moves: {len(strategies.data)} records")
    if strategies.data:
        print(f"  Sample: {strategies.data[0]['strategy']}")
    
    print("\n✅ Simulation complete!")

if __name__ == "__main__":
    asyncio.run(main())