#!/usr/bin/env python3
"""Test with a real Deep Dive session"""
import requests
import json

BASE_URL = "https://web-production-945c4.up.railway.app"

# Start a real session
start_data = {
    "body_part": "Reproductive Corpus Cavernosum Of Penis",
    "form_data": {
        "symptoms": "white filled pussy bumps that are painful",
        "painLevel": 7,
        "duration": "1 week"
    }
}

print("Starting Deep Dive...")
response = requests.post(f"{BASE_URL}/api/deep-dive/start", json=start_data)
session_data = response.json()
session_id = session_data["session_id"]
print(f"Session ID: {session_id}")

# Answer a question
answer_data = {
    "session_id": session_id,
    "answer": "no hair follicles but yes some have developed into open sores",
    "question_number": 1
}

print("\nAnswering question...")
response = requests.post(f"{BASE_URL}/api/deep-dive/continue", json=answer_data)
continue_data = response.json()
print(f"Confidence: {continue_data.get('current_confidence')}%")

# Force completion
complete_data = {
    "session_id": session_id,
    "final_answer": None
}

print("\nCompleting Deep Dive...")
response = requests.post(f"{BASE_URL}/api/deep-dive/complete", json=complete_data, timeout=60)
result = response.json()

print(f"\nStatus: {result.get('status')}")
if 'analysis' in result:
    analysis = result['analysis']
    print(f"Analysis type: {type(analysis)}")
    print(f"Primary: {analysis.get('primaryCondition')}")
    print(f"Confidence: {analysis.get('confidence')}%")
    
    if analysis.get('differentials'):
        print(f"Differentials: {len(analysis['differentials'])} found")
    else:
        print("Differentials: EMPTY (fallback!)")
else:
    print(f"Error: {result}")