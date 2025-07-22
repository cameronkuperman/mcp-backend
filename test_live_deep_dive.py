#!/usr/bin/env python3
"""Test the LIVE Deep Dive implementation"""
import requests
import json

BASE_URL = "https://web-production-945c4.up.railway.app"

def test_live_deep_dive():
    """Test the actual deployed Deep Dive"""
    
    print("=== Testing LIVE Deep Dive Implementation ===")
    
    # Step 1: Start Deep Dive with same data as frontend
    start_data = {
        "body_part": "Reproductive Corpus Cavernosum Of Penis",
        "form_data": {
            "symptoms": "like white filled pussy bumps they are painful and they are arranged in an order that appears to be random",
            "painLevel": 7,
            "duration": "1 week"
        },
        "user_id": None
    }
    
    print(f"\n1. Starting Deep Dive...")
    print(f"Request: {json.dumps(start_data, indent=2)}")
    
    response = requests.post(
        f"{BASE_URL}/api/deep-dive/start",
        json=start_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
    
    if response.status_code != 200:
        return
    
    data = response.json()
    session_id = data.get("session_id")
    
    # Step 2: Answer first question
    print(f"\n2. Answering first question...")
    answer1_data = {
        "session_id": session_id,
        "answer": "no hair follicles but yes some have developed into open sore/ulcers",
        "question_number": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/api/deep-dive/continue",
        json=answer1_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response Status: {response.status_code}")
    print(f"Current Confidence: {response.json().get('current_confidence')}%")
    
    # Step 3: Complete the Deep Dive
    print(f"\n3. Forcing completion...")
    complete_data = {
        "session_id": session_id,
        "final_answer": None
    }
    
    response = requests.post(
        f"{BASE_URL}/api/deep-dive/complete",
        json=complete_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Response Status: {response.status_code}")
    result = response.json()
    
    print(f"\n=== ANALYSIS RESULT ===")
    analysis = result.get("analysis", {})
    print(f"Primary Condition: {analysis.get('primaryCondition')}")
    print(f"Confidence: {analysis.get('confidence')}%")
    print(f"Differentials: {analysis.get('differentials')}")
    print(f"Is this generic? {analysis.get('primaryCondition', '').startswith('Analysis of')}")
    
    # Check if it's using the fallback
    if "Analysis of" in analysis.get('primaryCondition', '') and not analysis.get('differentials'):
        print("\n❌ PROBLEM: Getting FALLBACK response instead of real analysis!")
        print("This means the LLM response parsing is failing")

if __name__ == "__main__":
    test_live_deep_dive()