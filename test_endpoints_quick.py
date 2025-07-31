#!/usr/bin/env python3
"""
Quick test for intelligence endpoints
"""
import requests
import json
import sys

user_id = sys.argv[1] if len(sys.argv) > 1 else "45b61b67-175d-48a0-aca6-d0be57609383"
base_url = "http://localhost:8000"

print(f"Testing with user_id: {user_id}")

# Test 1: Generate Insights
print("\n1. Testing POST /api/generate-insights/{user_id}")
try:
    response = requests.post(f"{base_url}/api/generate-insights/{user_id}", timeout=30)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Get Insights
print("\n2. Testing GET /api/insights/{user_id}")
try:
    response = requests.get(f"{base_url}/api/insights/{user_id}", timeout=30)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Generate Shadow Patterns
print("\n3. Testing POST /api/generate-shadow-patterns/{user_id}")
try:
    response = requests.post(f"{base_url}/api/generate-shadow-patterns/{user_id}", timeout=30)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Get Shadow Patterns
print("\n4. Testing GET /api/shadow-patterns/{user_id}")
try:
    response = requests.get(f"{base_url}/api/shadow-patterns/{user_id}", timeout=30)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
except Exception as e:
    print(f"Error: {e}")