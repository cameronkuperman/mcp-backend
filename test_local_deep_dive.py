#!/usr/bin/env python3
"""Test Deep Dive locally to see debug output"""
import asyncio
import sys
sys.path.append('.')

from api.health_scan import complete_deep_dive
from models.requests import DeepDiveCompleteRequest
from supabase_client import supabase
from datetime import datetime, timezone
import uuid

async def test_local():
    # First, create a mock session in the database
    session_id = str(uuid.uuid4())
    
    session_data = {
        "id": session_id,
        "user_id": None,
        "body_part": "Reproductive Corpus Cavernosum Of Penis",
        "form_data": {
            "symptoms": "white filled pussy bumps that are painful",
            "painLevel": 7,
            "duration": "1 week"
        },
        "status": "in-progress",
        "questions": [
            {
                "question": "Have you noticed any tingling before the bumps?",
                "answer": "no hair follicles but yes some have developed into open sores",
                "question_number": 1
            }
        ],
        "final_confidence": 70,
        "internal_state": {
            "differential_diagnosis": [
                {"condition": "Herpes Simplex", "probability": 45},
                {"condition": "Folliculitis", "probability": 30}
            ]
        },
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Insert test session
    try:
        supabase.table("deep_dive_sessions").insert(session_data).execute()
        print(f"Created test session: {session_id}")
    except Exception as e:
        print(f"Error creating session: {e}")
    
    # Test the complete endpoint
    request = DeepDiveCompleteRequest(
        session_id=session_id,
        final_answer=None
    )
    
    print("\n=== Testing Deep Dive Complete ===")
    result = await complete_deep_dive(request)
    
    print(f"\nResult keys: {list(result.keys())}")
    if 'analysis' in result:
        analysis = result['analysis']
        print(f"\nAnalysis type: {type(analysis)}")
        print(f"Analysis keys: {list(analysis.keys()) if isinstance(analysis, dict) else 'Not a dict'}")
        print(f"\nPrimary Condition: {analysis.get('primaryCondition')}")
        print(f"Confidence: {analysis.get('confidence')}%")
        print(f"Differentials: {analysis.get('differentials')}")
        
        # Check if it's the fallback
        if "Analysis of" in str(analysis.get('primaryCondition', '')):
            print("\n❌ Got fallback response!")
        else:
            print("\n✅ Got real analysis!")
    
    # Clean up
    try:
        supabase.table("deep_dive_sessions").delete().eq("id", session_id).execute()
        print(f"\nCleaned up test session")
    except:
        pass

if __name__ == "__main__":
    asyncio.run(test_local())