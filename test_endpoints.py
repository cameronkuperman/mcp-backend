#!/usr/bin/env python3
"""Test script for Oracle chat endpoints"""

import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_chat_normal():
    """Test normal chat (within limits)"""
    print("Testing normal chat...")
    payload = {
        "message": "I have a headache",
        "conversation_id": str(uuid.uuid4()),
        "user_id": "test-user-" + str(uuid.uuid4())[:8]
    }
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Context status: {data.get('context_status', {}).get('status')}")
    print(f"Can continue: {data.get('context_status', {}).get('can_continue')}")
    print(f"User tier: {data.get('user_tier')}")
    print(f"Token percentage: {data.get('context_status', {}).get('percentage')}%\n")
    return response.status_code == 200

def test_exit_summary():
    """Test exit summary"""
    print("Testing exit summary...")
    conv_id = str(uuid.uuid4())
    payload = {
        "conversation_id": conv_id,
        "user_id": "test-user"
    }
    response = requests.post(f"{BASE_URL}/api/oracle/exit-summary", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    return response.status_code == 200

def test_generate_title():
    """Test title generation (will fail without existing conversation)"""
    print("Testing title generation...")
    payload = {
        "conversation_id": str(uuid.uuid4()),
        "force": False
    }
    response = requests.post(f"{BASE_URL}/api/oracle/generate-title", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")
    # This is expected to fail with "Conversation not found"
    return response.json().get("error") == "Conversation not found"

def test_blocked_scenario():
    """Test what happens when context limit is reached"""
    print("Testing blocked scenario (simulated)...")
    print("Note: In real scenario, free users would be blocked at 100k tokens")
    print("Current implementation would need actual conversation with 100k+ tokens\n")
    
    # Create a conversation and send a message
    conv_id = str(uuid.uuid4())
    payload = {
        "message": "Test message",
        "conversation_id": conv_id,
        "user_id": "test-user"
    }
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    data = response.json()
    
    # Check the response structure
    if "context_status" in data:
        status = data["context_status"]
        print(f"Token count: {status.get('tokens')}")
        print(f"Limit: {status.get('limit')}")
        print(f"Percentage: {status.get('percentage')}%")
        print(f"Can continue: {status.get('can_continue')}")
        print(f"Status: {status.get('status')}")
        
        # Check for upgrade prompt (would appear at 100k for free users)
        if status.get('upgrade_prompt'):
            print(f"Upgrade prompt: {status['upgrade_prompt']['title']}")
    
    return True

def run_all_tests():
    """Run all tests"""
    print("=" * 50)
    print("ORACLE CHAT ENDPOINT TESTS")
    print("=" * 50 + "\n")
    
    tests = [
        ("Health Check", test_health),
        ("Normal Chat", test_chat_normal),
        ("Exit Summary", test_exit_summary),
        ("Generate Title", test_generate_title),
        ("Blocked Scenario", test_blocked_scenario)
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, "PASSED" if passed else "FAILED"))
        except Exception as e:
            print(f"Error in {name}: {e}\n")
            results.append((name, "ERROR"))
    
    print("=" * 50)
    print("TEST RESULTS:")
    print("=" * 50)
    for name, result in results:
        status_emoji = "✅" if result == "PASSED" else "❌"
        print(f"{status_emoji} {name}: {result}")

if __name__ == "__main__":
    run_all_tests()