#!/usr/bin/env python3
"""
Debug test for intelligence endpoints
Shows exactly what's happening
"""
import requests
import json

user_id = "45b61b67-175d-48a0-aca6-d0be57609383"
base_url = "https://web-production-945c4.up.railway.app"

print("🔍 TESTING INTELLIGENCE ENDPOINTS\n")

# Test 1: Force refresh insights
print("1. Testing INSIGHTS generation with force_refresh=true")
print("=" * 60)
try:
    response = requests.post(
        f"{base_url}/api/generate-insights/{user_id}?force_refresh=true",
        timeout=90
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if data.get('insights'):
        print(f"\n✅ Generated {len(data['insights'])} insights!")
        for i, insight in enumerate(data['insights'][:2], 1):
            print(f"\nInsight {i}:")
            print(f"  Type: {insight.get('insight_type')}")
            print(f"  Title: {insight.get('title')}")
            print(f"  Description: {insight.get('description')}")
    else:
        print("\n❌ No insights generated!")
        print("Possible reasons:")
        print("- User has no health data")
        print("- LLM call failed")
        print("- JSON parsing failed")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)

# Test 2: Check what's in DB
print("\n2. Checking what's stored in database")
print("=" * 60)
try:
    response = requests.get(f"{base_url}/api/insights/{user_id}")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    print(f"Insights in DB: {len(data.get('insights', []))}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)

# Test 3: Shadow patterns
print("\n3. Testing SHADOW PATTERNS generation")
print("=" * 60)
try:
    response = requests.post(
        f"{base_url}/api/generate-shadow-patterns/{user_id}?force_refresh=true",
        timeout=90
    )
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if data.get('shadow_patterns'):
        print(f"\n✅ Found {len(data['shadow_patterns'])} shadow patterns!")
        for i, pattern in enumerate(data['shadow_patterns'][:2], 1):
            print(f"\nPattern {i}:")
            print(f"  Name: {pattern.get('pattern_name')}")
            print(f"  Category: {pattern.get('pattern_category')}")
            print(f"  Last Seen: {pattern.get('last_seen_description')}")
    else:
        print("\n❌ No shadow patterns found!")
        print("This could mean:")
        print("- User has been consistent (nothing missing)")
        print("- Not enough historical data")
        print("- LLM call failed")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("\n📊 SUMMARY:")
print("- Endpoints are responding")
print("- But returning empty data")
print("- Need to check Railway logs to see LLM calls")