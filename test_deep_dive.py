#!/usr/bin/env python3
"""Test script for Deep Dive complete endpoint with mock data"""
import requests
import json
import uuid
from datetime import datetime, timezone

# API endpoint
BASE_URL = "https://web-production-945c4.up.railway.app"
# BASE_URL = "http://localhost:8000"  # For local testing

def test_deep_dive_complete():
    """Test the deep dive complete endpoint with mock data"""
    
    # Step 1: Start a Deep Dive session
    print("=== Starting Deep Dive Session ===")
    
    start_request = {
        "body_part": "head",
        "form_data": {
            "symptoms": "Severe morning headaches for the past 2 weeks",
            "painLevel": 7,
            "duration": "2 weeks",
            "frequency": "daily",
            "whatHelps": "Rest and darkness",
            "whatWorsens": "Bright lights and loud noises",
            "associatedSymptoms": ["nausea", "sensitivity to light"]
        },
        "user_id": None  # Anonymous session
    }
    
    response = requests.post(
        f"{BASE_URL}/api/deep-dive/start",
        json=start_request,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"Error starting deep dive: {response.status_code}")
        print(response.text)
        return
    
    start_data = response.json()
    session_id = start_data.get("session_id")
    print(f"Session ID: {session_id}")
    print(f"First Question: {start_data.get('question')}")
    
    # Step 2: Answer questions to build confidence
    print("\n=== Answering Questions ===")
    
    # Answer 1: Specific timing
    answer1 = "The headaches usually start around 6-7 AM, right after I wake up. They're worst in the first hour."
    
    continue_request = {
        "session_id": session_id,
        "answer": answer1,
        "question_number": 1
    }
    
    response = requests.post(
        f"{BASE_URL}/api/deep-dive/continue",
        json=continue_request,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"Error continuing deep dive: {response.status_code}")
        print(response.text)
        return
    
    continue_data = response.json()
    print(f"Answer 1 recorded. Ready for analysis: {continue_data.get('ready_for_analysis', False)}")
    
    if not continue_data.get("ready_for_analysis"):
        # Answer 2: Pattern details
        print(f"Question 2: {continue_data.get('question')}")
        
        answer2 = "Yes, I've been under significant work stress. Also been drinking less water and more coffee."
        
        continue_request2 = {
            "session_id": session_id,
            "answer": answer2,
            "question_number": 2
        }
        
        response = requests.post(
            f"{BASE_URL}/api/deep-dive/continue",
            json=continue_request2,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code != 200:
            print(f"Error continuing deep dive: {response.status_code}")
            print(response.text)
            return
        
        continue_data2 = response.json()
        print(f"Answer 2 recorded. Ready for analysis: {continue_data2.get('ready_for_analysis', False)}")
        print(f"Current confidence: {continue_data2.get('current_confidence', 'Unknown')}%")
        
        # If still not ready, answer one more
        if not continue_data2.get("ready_for_analysis") and continue_data2.get("question"):
            print(f"Question 3: {continue_data2.get('question')}")
            
            answer3 = "No family history of migraines. I do grind my teeth at night sometimes."
            
            continue_request3 = {
                "session_id": session_id,
                "answer": answer3,
                "question_number": 3
            }
            
            response = requests.post(
                f"{BASE_URL}/api/deep-dive/continue",
                json=continue_request3,
                headers={"Content-Type": "application/json"}
            )
            
            continue_data3 = response.json()
            print(f"Answer 3 recorded. Ready for analysis: {continue_data3.get('ready_for_analysis', False)}")
            print(f"Current confidence: {continue_data3.get('current_confidence', 'Unknown')}%")
    
    # Step 3: Complete the Deep Dive
    print("\n=== Completing Deep Dive ===")
    
    complete_request = {
        "session_id": session_id,
        "final_answer": None  # No additional answer needed
    }
    
    response = requests.post(
        f"{BASE_URL}/api/deep-dive/complete",
        json=complete_request,
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code != 200:
        print(f"Error completing deep dive: {response.status_code}")
        print(response.text)
        return
    
    complete_data = response.json()
    
    # Print results
    print("\n=== DEEP DIVE RESULTS ===")
    print(f"Status: {complete_data.get('status')}")
    print(f"Deep Dive ID: {complete_data.get('deep_dive_id')}")
    print(f"Questions Asked: {complete_data.get('questions_asked')}")
    print(f"Final Confidence: {complete_data.get('confidence')}%")
    
    analysis = complete_data.get('analysis', {})
    print(f"\nPrimary Condition: {analysis.get('primaryCondition')}")
    print(f"Likelihood: {analysis.get('likelihood')}")
    print(f"Urgency: {analysis.get('urgency')}")
    
    print("\nDifferential Diagnoses:")
    for diff in analysis.get('differentials', []):
        print(f"  - {diff.get('condition')}: {diff.get('probability')}%")
    
    print("\nKey Symptoms:")
    for symptom in analysis.get('symptoms', [])[:5]:
        print(f"  - {symptom}")
    
    print("\nRecommendations:")
    for rec in analysis.get('recommendations', [])[:3]:
        print(f"  - {rec}")
    
    print("\nRed Flags:")
    for flag in analysis.get('redFlags', []):
        print(f"  - {flag}")
    
    print("\nReasoning Insights:")
    for insight in analysis.get('reasoning_snippets', []):
        print(f"  - {insight}")
    
    # Test Ultra Think if confidence is low
    if complete_data.get('confidence', 0) < 90:
        print(f"\n=== Testing Ultra Think (confidence {complete_data.get('confidence')}% < 90%) ===")
        
        ultra_request = {
            "deep_dive_id": session_id,
            "scan_id": session_id,  # Some frontends send both
            "user_id": None
        }
        
        response = requests.post(
            f"{BASE_URL}/api/quick-scan/ultra-think",
            json=ultra_request,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            ultra_data = response.json()
            print(f"Ultra Think Status: {ultra_data.get('status')}")
            print(f"Ultra Confidence: {ultra_data.get('confidence_progression', {}).get('ultra')}%")
            print(f"Critical Insights: {ultra_data.get('critical_insights', [])}")
        else:
            print(f"Ultra Think failed: {response.status_code}")

if __name__ == "__main__":
    test_deep_dive_complete()