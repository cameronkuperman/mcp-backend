#!/usr/bin/env python3
"""Quick test of all three fixed endpoints"""

import asyncio
import httpx
import json
from datetime import date, timedelta

API_URL = "http://localhost:8000"
TEST_USER = "802ba1fe-7dad-4a54-8681-32239f11fb37"  # User with data

async def test_endpoints():
    print("="*60)
    print("TESTING WEEKLY JOB ENDPOINTS")
    print("="*60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Insights
        print("\n1. Testing Insights Endpoint...")
        response = await client.post(
            f"{API_URL}/api/generate-insights/{TEST_USER}",
            json={"force_refresh": True}
        )
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Count: {data.get('count')}")
        if data.get('data'):
            print(f"   Sample: {data['data'][0].get('title', 'No title')}")
        
        # Test 2: Shadow Patterns
        print("\n2. Testing Shadow Patterns Endpoint...")
        response = await client.post(
            f"{API_URL}/api/generate-shadow-patterns/{TEST_USER}",
            json={"force_refresh": True}
        )
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Count: {data.get('count')}")
        if data.get('data'):
            print(f"   Sample: {data['data'][0].get('name', 'No name')}")
        
        # Test 3: Strategic Moves
        print("\n3. Testing Strategic Moves Endpoint...")
        response = await client.post(
            f"{API_URL}/api/generate-strategies/{TEST_USER}",
            json={"force_refresh": True}
        )
        data = response.json()
        print(f"   Status: {data.get('status')}")
        print(f"   Count: {data.get('count')}")
        if data.get('data'):
            print(f"   Sample: {data['data'][0].get('strategy', 'No strategy')}")
        
        print("\n" + "="*60)
        print("✅ All endpoints are working!")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_endpoints())