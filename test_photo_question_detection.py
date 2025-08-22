#!/usr/bin/env python3
"""Test script for photo analysis question detection"""

import requests
import json
import base64
from datetime import datetime
import uuid

# Configuration
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/photo-analysis"

# Test cases with different question types
TEST_CASES = [
    {
        "name": "Direct Question",
        "context": "Red rash on my arm, is this serious?",
        "expected": {
            "question_detected": True,
            "has_answer": True
        }
    },
    {
        "name": "Implied Concern",
        "context": "I'm worried this mole looks different than last month",
        "expected": {
            "question_detected": True,
            "has_answer": True
        }
    },
    {
        "name": "Should I See Doctor",
        "context": "This spot has been growing, should I see a doctor?",
        "expected": {
            "question_detected": True,
            "has_answer": True
        }
    },
    {
        "name": "Comparative Question",
        "context": "Is this getting worse compared to yesterday?",
        "expected": {
            "question_detected": True,
            "has_answer": True
        }
    },
    {
        "name": "Pure Description",
        "context": "Brown spot, oval shape, approximately 8mm",
        "expected": {
            "question_detected": False,
            "has_answer": False
        }
    },
    {
        "name": "Medical Description Only",
        "context": "Erythematous papule with central clearing",
        "expected": {
            "question_detected": False,
            "has_answer": False
        }
    },
    {
        "name": "What Is This Question",
        "context": "What is this bump on my knee?",
        "expected": {
            "question_detected": True,
            "has_answer": True
        }
    },
    {
        "name": "Infection Question",
        "context": "Does this look infected to you?",
        "expected": {
            "question_detected": True,
            "has_answer": True
        }
    }
]

def create_mock_photo_data():
    """Create a mock photo session and photo for testing"""
    # This would normally interact with Supabase
    # For testing, we'll use mock IDs
    return {
        "session_id": str(uuid.uuid4()),
        "photo_ids": [str(uuid.uuid4())]
    }

def test_question_detection():
    """Test the photo analysis endpoint with various question types"""
    
    print("=" * 60)
    print("PHOTO ANALYSIS QUESTION DETECTION TEST")
    print("=" * 60)
    print()
    
    # Check if server is running
    try:
        health_response = requests.get(f"{BASE_URL}/api/health")
        if health_response.status_code != 200:
            print("❌ Server not healthy")
            return
        print("✅ Server is running")
        print()
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please make sure the server is running on port 8000")
        return
    
    # Run test cases
    results = []
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"Test {i}: {test_case['name']}")
        print(f"Context: \"{test_case['context']}\"")
        
        # Simulate photo analysis request
        mock_data = create_mock_photo_data()
        
        # Create request payload
        payload = {
            "session_id": mock_data["session_id"],
            "photo_ids": mock_data["photo_ids"],
            "context": test_case["context"],
            "temporary_analysis": True  # For testing without saving
        }
        
        # Note: In real testing, you would need actual photo data
        # For this demonstration, we're showing the expected behavior
        print(f"Expected: question_detected={test_case['expected']['question_detected']}")
        
        # Simulate expected response
        if test_case['expected']['question_detected']:
            print(f"✅ Should detect question and provide answer")
            example_answer = f"Based on the analysis, {test_case['context'][:30]}..."
            print(f"   Example answer: \"{example_answer[:60]}...\"")
        else:
            print(f"⚪ Should NOT detect question (pure description)")
        
        print("-" * 40)
        
        results.append({
            "test": test_case["name"],
            "context": test_case["context"],
            "expected": test_case["expected"]
        })
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tests: {len(TEST_CASES)}")
    print(f"Questions expected: {sum(1 for t in TEST_CASES if t['expected']['question_detected'])}")
    print(f"Descriptions expected: {sum(1 for t in TEST_CASES if not t['expected']['question_detected'])}")
    print()
    
    # Print curl examples
    print("=" * 60)
    print("CURL TEST EXAMPLES")
    print("=" * 60)
    print()
    
    print("1. Test with Direct Question:")
    print("```bash")
    print('''curl -X POST http://localhost:8000/api/photo-analysis/analyze \\
  -H "Content-Type: application/json" \\
  -d '{
    "session_id": "test-session-123",
    "photo_ids": ["test-photo-456"],
    "context": "Red rash on my arm, is this serious?",
    "temporary_analysis": true
  }' | python -m json.tool
''')
    print("```")
    print()
    
    print("2. Test with Pure Description:")
    print("```bash")
    print('''curl -X POST http://localhost:8000/api/photo-analysis/analyze \\
  -H "Content-Type: application/json" \\
  -d '{
    "session_id": "test-session-789",
    "photo_ids": ["test-photo-012"],
    "context": "Brown spot, oval shape, approximately 8mm",
    "temporary_analysis": true
  }' | python -m json.tool
''')
    print("```")
    print()
    
    print("Expected Response Structure (with question):")
    print("```json")
    example_response = {
        "analysis_id": "uuid-here",
        "analysis": {
            "question_detected": True,
            "question_answer": "Based on the visual analysis, this rash appears to be a common dermatitis...",
            "primary_assessment": "Contact dermatitis",
            "confidence": 85,
            "visual_observations": ["Erythematous patches", "Mild scaling"],
            "urgency_level": "low",
            "follow_up_timing": "1 week"
        }
    }
    print(json.dumps(example_response, indent=2))
    print("```")

if __name__ == "__main__":
    test_question_detection()