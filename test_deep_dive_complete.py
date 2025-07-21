#!/usr/bin/env python3
"""
Test script for Deep Dive complete endpoint with realistic mock data.
Tests the full flow: start -> continue with multiple Q&As -> complete
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional

# API Configuration
BASE_URL = "https://web-production-945c4.up.railway.app"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_step(step_num: int, message: str):
    """Print a step header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}Step {step_num}: {message}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")

def print_info(key: str, value: Any):
    """Print info key-value pair"""
    print(f"{Colors.OKCYAN}{key}:{Colors.ENDC} {value}")

def print_json(data: Dict[str, Any], indent: int = 2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent))

def make_request(endpoint: str, method: str = "POST", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request and handle response"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method == "POST":
            response = requests.post(url, headers=HEADERS, json=data)
        else:
            response = requests.get(url, headers=HEADERS)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_error(f"Request failed: {e}")
        if hasattr(e.response, 'text'):
            print_error(f"Response: {e.response.text}")
        raise

def test_deep_dive_complete():
    """Test the complete Deep Dive flow with realistic medical data"""
    
    # Step 1: Create initial Deep Dive session
    print_step(1, "Starting Deep Dive Session")
    
    # Realistic chest pain scenario
    start_data = {
        "body_part": "chest",
        "form_data": {
            "symptoms": "sharp chest pain on left side, worse with deep breathing",
            "painLevel": 7,
            "duration": "3 days",
            "timing": "intermittent",
            "triggers": "deep breathing, movement",
            "associatedSymptoms": ["shortness of breath", "mild fatigue"],
            "medicalHistory": ["mild asthma"],
            "medications": ["albuterol inhaler as needed"],
            "age": 35,
            "gender": "male"
        },
        "user_id": None,  # Anonymous user for testing
        "model": "tngtech/deepseek-r1t-chimera:free"
    }
    
    print_info("Request data", "")
    print_json(start_data)
    
    try:
        start_response = make_request("/api/deep-dive/start", data=start_data)
        session_id = start_response.get("session_id")
        
        if not session_id:
            print_error("No session_id received")
            return
        
        print_success(f"Deep Dive session created: {session_id}")
        print_info("First question", start_response.get("question", ""))
        print_info("Question type", start_response.get("question_type", ""))
        
    except Exception as e:
        print_error(f"Failed to start deep dive: {e}")
        return
    
    # Step 2: Simulate multiple Q&A rounds
    print_step(2, "Answering Deep Dive Questions")
    
    # Prepare realistic answers that would lead to high confidence
    qa_pairs = [
        {
            "question_context": "pain characteristics",
            "answer": "The pain is sharp and stabbing, located about 2 inches to the left of my sternum. It's worse when I take a deep breath, twist my torso, or press on the area. It rates about 7/10 at worst, 3/10 at rest."
        },
        {
            "question_context": "timing and progression",
            "answer": "It started 3 days ago after I helped a friend move heavy furniture. The pain was sudden onset while lifting a couch. It hasn't spread to other areas and seems consistent in location."
        },
        {
            "question_context": "associated symptoms",
            "answer": "No fever, no cough, no nausea. I feel slightly short of breath but only because deep breaths hurt. No dizziness, no sweating, no pain radiating to my arm or jaw. My heart rate feels normal."
        },
        {
            "question_context": "medical history",
            "answer": "I have mild asthma controlled with albuterol. No heart problems, no high blood pressure. I don't smoke. I exercise regularly - usually run 3 times a week. No recent illnesses or injuries besides this."
        },
        {
            "question_context": "relief measures",
            "answer": "Ibuprofen helps reduce the pain to about 4/10. Shallow breathing helps avoid the sharp pain. Lying on my right side is more comfortable than lying flat. Heat packs provide some relief."
        }
    ]
    
    question_number = 1
    ready_for_analysis = False
    
    for qa in qa_pairs:
        print(f"\n{Colors.BOLD}Question {question_number}:{Colors.ENDC}")
        
        continue_data = {
            "session_id": session_id,
            "answer": qa["answer"],
            "question_number": question_number
        }
        
        print_info("Answering about", qa["question_context"])
        print_info("Answer", qa["answer"][:100] + "..." if len(qa["answer"]) > 100 else qa["answer"])
        
        try:
            continue_response = make_request("/api/deep-dive/continue", data=continue_data)
            
            if continue_response.get("ready_for_analysis"):
                print_success("Deep Dive ready for final analysis!")
                ready_for_analysis = True
                break
            else:
                next_question = continue_response.get("question", "")
                confidence = continue_response.get("current_confidence", 0)
                
                print_info("Current confidence", f"{confidence}%")
                print_info("Next question", next_question)
                print_info("Questions remaining", continue_response.get("questions_remaining", "unknown"))
                
                if continue_response.get("is_final_question"):
                    print(f"{Colors.WARNING}This is the final question before analysis{Colors.ENDC}")
                
                question_number += 1
                
        except Exception as e:
            print_error(f"Failed to continue deep dive: {e}")
            return
        
        # Small delay to simulate real user interaction
        time.sleep(0.5)
    
    # Step 3: Complete the Deep Dive
    print_step(3, "Completing Deep Dive Analysis")
    
    # If we didn't naturally reach completion, add a final answer
    if not ready_for_analysis and question_number <= len(qa_pairs):
        print_info("Adding final answer", "Providing comprehensive final details")
        final_answer = "No previous chest trauma or surgery. The pain is definitely musculoskeletal - it's reproducible with movement and palpation. No cardiac risk factors in my family."
    else:
        final_answer = None
    
    complete_data = {
        "session_id": session_id,
        "final_answer": final_answer
    }
    
    try:
        print_info("Requesting final analysis", "")
        complete_response = make_request("/api/deep-dive/complete", data=complete_data)
        
        if complete_response.get("status") == "success":
            print_success("Deep Dive analysis completed successfully!")
            
            # Display results
            analysis = complete_response.get("analysis", {})
            
            print(f"\n{Colors.BOLD}Final Analysis Results:{Colors.ENDC}")
            print_info("Deep Dive ID", complete_response.get("deep_dive_id", ""))
            print_info("Primary Condition", analysis.get("primaryCondition", ""))
            print_info("Confidence", f"{analysis.get('confidence', 0)}%")
            print_info("Likelihood", analysis.get("likelihood", ""))
            print_info("Urgency", analysis.get("urgency", ""))
            print_info("Questions Asked", complete_response.get("questions_asked", 0))
            
            # Display key findings
            if analysis.get("symptoms"):
                print(f"\n{Colors.BOLD}Key Symptoms Identified:{Colors.ENDC}")
                for symptom in analysis.get("symptoms", [])[:5]:
                    print(f"  • {symptom}")
            
            # Display recommendations
            if analysis.get("recommendations"):
                print(f"\n{Colors.BOLD}Recommendations:{Colors.ENDC}")
                for rec in analysis.get("recommendations", [])[:5]:
                    print(f"  • {rec}")
            
            # Display red flags
            if analysis.get("redFlags"):
                print(f"\n{Colors.WARNING}{Colors.BOLD}Red Flags to Watch:{Colors.ENDC}")
                for flag in analysis.get("redFlags", []):
                    print(f"  ⚠️  {flag}")
            
            # Display reasoning snippets
            if complete_response.get("reasoning_snippets"):
                print(f"\n{Colors.BOLD}Clinical Reasoning:{Colors.ENDC}")
                for snippet in complete_response.get("reasoning_snippets", [])[:3]:
                    print(f"  → {snippet}")
            
            # Display usage stats
            if complete_response.get("usage"):
                usage = complete_response.get("usage", {})
                print(f"\n{Colors.BOLD}API Usage:{Colors.ENDC}")
                print_info("Total tokens", usage.get("total_tokens", "N/A"))
                print_info("Model used", complete_response.get("model", "N/A"))
            
        else:
            print_error("Deep Dive completion failed")
            print_json(complete_response)
            
    except Exception as e:
        print_error(f"Failed to complete deep dive: {e}")
        return
    
    # Step 4: Summary
    print_step(4, "Test Summary")
    print_success(f"Successfully tested Deep Dive complete endpoint")
    print_info("Session ID", session_id)
    print_info("Total questions asked", question_number)
    print_info("Final confidence achieved", f"{analysis.get('confidence', 0)}%")
    print_info("Primary diagnosis", analysis.get("primaryCondition", "Unknown"))
    
    print(f"\n{Colors.OKGREEN}{Colors.BOLD}Test completed successfully!{Colors.ENDC}")
    
    # Optional: Test error scenarios
    if input("\nTest error scenarios? (y/n): ").lower() == 'y':
        test_error_scenarios()

def test_error_scenarios():
    """Test various error scenarios"""
    print_step(5, "Testing Error Scenarios")
    
    # Test 1: Invalid session ID
    print(f"\n{Colors.BOLD}Test 1: Invalid session ID{Colors.ENDC}")
    try:
        response = make_request("/api/deep-dive/complete", data={
            "session_id": "invalid-session-id-12345"
        })
        if response.get("error"):
            print_success(f"Correctly handled invalid session: {response.get('error')}")
        else:
            print_error("Should have returned an error for invalid session")
    except:
        print_success("Request failed as expected for invalid session")
    
    # Test 2: Missing session ID
    print(f"\n{Colors.BOLD}Test 2: Missing session ID{Colors.ENDC}")
    try:
        response = make_request("/api/deep-dive/complete", data={})
        print_error("Should have failed validation for missing session_id")
    except:
        print_success("Request failed as expected for missing session_id")
    
    # Test 3: Complete already completed session (would need a real completed session ID)
    print(f"\n{Colors.BOLD}Test 3: Double completion attempt{Colors.ENDC}")
    print_info("Note", "This would require a previously completed session ID to test properly")

if __name__ == "__main__":
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}Deep Dive Complete Endpoint Test Script{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"\nTarget URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    try:
        test_deep_dive_complete()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Test interrupted by user{Colors.ENDC}")
    except Exception as e:
        print(f"\n{Colors.FAIL}Unexpected error: {e}{Colors.ENDC}")