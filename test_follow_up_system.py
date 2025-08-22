#!/usr/bin/env python3
"""Test script for the Assessment Follow-Up System"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import uuid
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = str(uuid.uuid4())

# Test data
TEST_ASSESSMENT = {
    "assessment_id": str(uuid.uuid4()),
    "assessment_type": "general_assessment",
    "user_id": TEST_USER_ID
}

# Color codes for output
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(message: str):
    print(f"{GREEN}✓ {message}{RESET}")

def print_warning(message: str):
    print(f"{YELLOW}⚠ {message}{RESET}")

def print_error(message: str):
    print(f"{RED}✗ {message}{RESET}")

def print_info(message: str):
    print(f"{BLUE}ℹ {message}{RESET}")

async def test_get_follow_up_questions(session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
    """Test getting follow-up questions"""
    print_info("Testing GET /api/follow-up/questions/{assessment_id}")
    
    try:
        url = f"{BASE_URL}/api/follow-up/questions/{TEST_ASSESSMENT['assessment_id']}"
        params = {
            "assessment_type": TEST_ASSESSMENT["assessment_type"],
            "user_id": TEST_ASSESSMENT["user_id"]
        }
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                
                # Validate response structure
                assert "base_questions" in data, "Missing base_questions"
                assert "ai_questions" in data, "Missing ai_questions"
                assert "context" in data, "Missing context"
                assert len(data["base_questions"]) == 5, "Should have 5 base questions"
                assert len(data["ai_questions"]) == 3, "Should have 3 AI questions"
                
                print_success(f"Retrieved questions successfully")
                print(f"  - Base questions: {len(data['base_questions'])}")
                print(f"  - AI questions: {len(data['ai_questions'])}")
                print(f"  - Chain ID: {data['context']['chain_id']}")
                print(f"  - Days since original: {data['context']['days_since_original']}")
                print(f"  - Follow-up number: {data['context']['follow_up_number']}")
                
                # Print AI questions
                print("\n  AI-generated questions:")
                for i, q in enumerate(data['ai_questions'], 1):
                    print(f"    {i}. {q.get('question', 'No question text')}")
                
                return data
            else:
                error_text = await response.text()
                print_error(f"Failed to get questions: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        print_error(f"Error getting questions: {str(e)}")
        return None

async def test_submit_follow_up(session: aiohttp.ClientSession, chain_id: str) -> Optional[Dict[str, Any]]:
    """Test submitting follow-up responses"""
    print_info("\nTesting POST /api/follow-up/submit")
    
    # Sample responses
    responses = {
        "q1": "Somewhat better",
        "q2": "Less frequent headaches, but still present",
        "q3": "Somewhat better",
        "q4": "Yes",
        "q4_text": "Stress from work seems to trigger symptoms",
        "q5": False,
        "ai_q1": "The headaches have reduced from daily to 3-4 times per week",
        "ai_q2": "Ibuprofen helps, meditation doesn't seem to make a difference",
        "ai_q3": "Symptoms are worse in the morning and during meetings"
    }
    
    payload = {
        "assessment_id": TEST_ASSESSMENT["assessment_id"],
        "assessment_type": TEST_ASSESSMENT["assessment_type"],
        "chain_id": chain_id,
        "responses": responses,
        "user_id": TEST_ASSESSMENT["user_id"]
    }
    
    try:
        async with session.post(f"{BASE_URL}/api/follow-up/submit", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                # Validate response structure
                assert "follow_up_id" in data, "Missing follow_up_id"
                assert "chain_id" in data, "Missing chain_id"
                assert "assessment" in data, "Missing assessment"
                assert "confidence_indicator" in data, "Missing confidence_indicator"
                
                print_success("Follow-up submitted successfully")
                print(f"  - Follow-up ID: {data['follow_up_id']}")
                print(f"  - Confidence: {data['confidence_indicator']['explanation']}")
                print(f"  - Next follow-up: {data.get('next_follow_up', 'Not specified')}")
                
                # Print evolution if present
                if "assessment_evolution" in data:
                    evo = data["assessment_evolution"]
                    print(f"\n  Assessment Evolution:")
                    print(f"    - Original: {evo.get('original_assessment', 'Unknown')}")
                    print(f"    - Current: {evo.get('current_assessment', 'Unknown')}")
                    if "key_discoveries" in evo:
                        print(f"    - Discoveries: {', '.join(evo['key_discoveries'][:2])}")
                
                return data
            else:
                error_text = await response.text()
                print_error(f"Failed to submit follow-up: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        print_error(f"Error submitting follow-up: {str(e)}")
        return None

async def test_submit_with_medical_visit(session: aiohttp.ClientSession, chain_id: str) -> Optional[Dict[str, Any]]:
    """Test submitting follow-up with medical visit"""
    print_info("\nTesting POST /api/follow-up/submit with medical visit")
    
    responses = {
        "q1": "Somewhat worse",
        "q2": "Increased pain and new symptoms",
        "q3": "Somewhat worse",
        "q4": "No",
        "q5": True,  # Saw doctor
        "ai_q1": "Pain has increased and spread to neck",
        "ai_q2": "Previous treatments stopped working",
        "ai_q3": "Constant now, no relief periods"
    }
    
    medical_visit = {
        "provider_type": "specialist",
        "provider_specialty": "Neurology",
        "assessment": "Patient presents with chronic tension-type headaches with cervicogenic component. Prescribed amitriptyline 10mg qHS for prophylaxis. Recommend PT for cervical spine mobility.",
        "treatments": "Amitriptyline 10mg at bedtime, Physical therapy 2x/week",
        "follow_up_timing": "4 weeks"
    }
    
    payload = {
        "assessment_id": TEST_ASSESSMENT["assessment_id"],
        "assessment_type": TEST_ASSESSMENT["assessment_type"],
        "chain_id": chain_id,
        "responses": responses,
        "medical_visit": medical_visit,
        "user_id": TEST_ASSESSMENT["user_id"]
    }
    
    try:
        async with session.post(f"{BASE_URL}/api/follow-up/submit", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                print_success("Follow-up with medical visit submitted")
                print(f"  - Follow-up ID: {data['follow_up_id']}")
                
                if "medical_visit_explained" in data and data["medical_visit_explained"]:
                    print(f"\n  Medical Visit Translation:")
                    print(f"    {data['medical_visit_explained'][:200]}...")
                
                return data
            else:
                error_text = await response.text()
                print_error(f"Failed to submit with medical visit: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        print_error(f"Error submitting with medical visit: {str(e)}")
        return None

async def test_get_follow_up_chain(session: aiohttp.ClientSession, chain_id: str) -> Optional[Dict[str, Any]]:
    """Test getting the follow-up chain"""
    print_info("\nTesting GET /api/follow-up/chain/{assessment_id}")
    
    try:
        url = f"{BASE_URL}/api/follow-up/chain/{TEST_ASSESSMENT['assessment_id']}"
        params = {"include_events": True}
        
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                
                print_success("Follow-up chain retrieved")
                print(f"  - Chain ID: {data['chain_id']}")
                print(f"  - Total follow-ups: {data['total_follow_ups']}")
                print(f"  - Peak confidence: {data['peak_confidence']}%")
                print(f"  - Latest assessment: {data['latest_assessment']}")
                print(f"  - Total days tracked: {data['total_days_tracked']}")
                
                if data['confidence_progression']:
                    print(f"\n  Confidence Progression: {' → '.join(str(c) for c in data['confidence_progression'])}")
                
                if data['assessment_progression']:
                    print(f"\n  Diagnosis Evolution:")
                    for i, assessment in enumerate(data['assessment_progression'], 1):
                        print(f"    {i}. {assessment}")
                
                if data['events']:
                    print(f"\n  Events tracked: {len(data['events'])}")
                    for event in data['events'][:3]:
                        print(f"    - {event['event_type']}: {event.get('event_timestamp', 'No timestamp')}")
                
                return data
            else:
                error_text = await response.text()
                print_error(f"Failed to get chain: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        print_error(f"Error getting chain: {str(e)}")
        return None

async def test_medical_jargon_translation(session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
    """Test medical jargon translation"""
    print_info("\nTesting POST /api/follow-up/medical-visit/explain")
    
    payload = {
        "medical_terms": "Patient diagnosed with GERD with esophagitis grade B. Started on PPI BID and H2 blocker PRN. F/U EGD in 8 weeks.",
        "context": "Stomach pain and acid reflux"
    }
    
    try:
        async with session.post(f"{BASE_URL}/api/follow-up/medical-visit/explain", json=payload) as response:
            if response.status == 200:
                data = await response.json()
                
                print_success("Medical jargon translated")
                print(f"\n  Original: {payload['medical_terms']}")
                print(f"\n  Explanation: {data['explanation'][:300]}...")
                
                if "key_takeaways" in data and data["key_takeaways"]:
                    print(f"\n  Key Takeaways:")
                    for takeaway in data["key_takeaways"]:
                        print(f"    • {takeaway}")
                
                if "action_items" in data and data["action_items"]:
                    print(f"\n  Action Items:")
                    for action in data["action_items"]:
                        print(f"    • {action}")
                
                return data
            else:
                error_text = await response.text()
                print_error(f"Failed to translate: {response.status} - {error_text}")
                return None
                
    except Exception as e:
        print_error(f"Error translating: {str(e)}")
        return None

async def test_validation(session: aiohttp.ClientSession, chain_id: str):
    """Test validation - submitting without answering questions"""
    print_info("\nTesting validation - empty responses")
    
    payload = {
        "assessment_id": TEST_ASSESSMENT["assessment_id"],
        "assessment_type": TEST_ASSESSMENT["assessment_type"],
        "chain_id": chain_id,
        "responses": {},  # Empty responses
        "user_id": TEST_ASSESSMENT["user_id"]
    }
    
    try:
        async with session.post(f"{BASE_URL}/api/follow-up/submit", json=payload) as response:
            if response.status == 400:
                print_success("Validation working - rejected empty responses")
            else:
                print_warning(f"Expected 400, got {response.status}")
                
    except Exception as e:
        print_error(f"Error testing validation: {str(e)}")

async def run_all_tests():
    """Run all follow-up system tests"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Assessment Follow-Up System Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Get follow-up questions
        questions_data = await test_get_follow_up_questions(session)
        if not questions_data:
            print_error("Cannot continue without questions data")
            return
        
        chain_id = questions_data["context"]["chain_id"]
        
        # Test 2: Submit follow-up
        follow_up_data = await test_submit_follow_up(session, chain_id)
        
        # Test 3: Submit with medical visit
        await test_submit_with_medical_visit(session, chain_id)
        
        # Test 4: Get follow-up chain
        await test_get_follow_up_chain(session, chain_id)
        
        # Test 5: Medical jargon translation
        await test_medical_jargon_translation(session)
        
        # Test 6: Validation
        await test_validation(session, chain_id)
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{GREEN}Test suite completed!{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def main():
    """Main entry point"""
    print(f"\n{YELLOW}Starting Follow-Up System Tests...{RESET}")
    print(f"Server URL: {BASE_URL}")
    print(f"Test User ID: {TEST_USER_ID}\n")
    
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Tests interrupted by user{RESET}")
    except Exception as e:
        print(f"\n{RED}Test suite failed: {str(e)}{RESET}")

if __name__ == "__main__":
    main()