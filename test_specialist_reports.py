#!/usr/bin/env python3
"""Test specialist reports with provided IDs"""

import asyncio
import json
from datetime import datetime, timezone
import uuid
from supabase_client import supabase
from utils.data_gathering import gather_selected_data

async def test_data_gathering():
    """Test data gathering for provided IDs"""
    
    # Test 1: First user
    print("=" * 60)
    print("TEST 1: First User Data Gathering")
    print("=" * 60)
    print(f"User ID: 45b61b67-175d-48a0-aca6-d0be57609383")
    print(f"Deep Dive ID: 057447a9-3369-42b2-b683-778d10ae5c8b")
    print()
    
    # Check if this is a deep dive
    deep_dive = supabase.table("deep_dive_sessions")\
        .select("*")\
        .eq("id", "057447a9-3369-42b2-b683-778d10ae5c8b")\
        .execute()
    
    if deep_dive.data:
        print("✅ Found Deep Dive Session:")
        session = deep_dive.data[0]
        print(f"  - Status: {session.get('status')}")
        print(f"  - Body Part: {session.get('body_part')}")
        print(f"  - Questions Answered: {len(session.get('questions', []))}")
        print(f"  - Created: {session.get('created_at')}")
        print(f"  - Has Final Analysis: {session.get('final_analysis') is not None}")
        print(f"  - Final Confidence: {session.get('final_confidence')}")
        print()
    
    # Gather all data for this user
    data1 = await gather_selected_data(
        user_id="45b61b67-175d-48a0-aca6-d0be57609383",
        deep_dive_ids=["057447a9-3369-42b2-b683-778d10ae5c8b"]
    )
    
    print("Data Summary:")
    print(f"  - Medical Profile: {'✅' if data1.get('medical_profile') else '❌'}")
    print(f"  - Deep Dives: {len(data1.get('deep_dives', []))}")
    print(f"  - Quick Scans: {len(data1.get('quick_scans', []))}")
    print(f"  - Symptom Tracking: {len(data1.get('symptom_tracking', []))}")
    print()
    
    # Test 2: Second user
    print("=" * 60)
    print("TEST 2: Second User Data Gathering")
    print("=" * 60)
    print(f"User ID: 323ce656-8d89-46ac-bea1-a6382cc86ce9")
    print(f"ID to check: 01398d26-9974-482e-867a-5e840ca67679")
    print()
    
    # Check what type of assessment this is
    # Try deep dive first
    deep_dive2 = supabase.table("deep_dive_sessions")\
        .select("*")\
        .eq("id", "01398d26-9974-482e-867a-5e840ca67679")\
        .execute()
    
    if deep_dive2.data:
        print("✅ Found Deep Dive Session:")
        session = deep_dive2.data[0]
        print(f"  - Status: {session.get('status')}")
        print(f"  - Body Part: {session.get('body_part')}")
        print(f"  - Questions Answered: {len(session.get('questions', []))}")
        print(f"  - Has Final Analysis: {session.get('final_analysis') is not None}")
    else:
        # Try quick scan
        quick_scan = supabase.table("quick_scans")\
            .select("*")\
            .eq("id", "01398d26-9974-482e-867a-5e840ca67679")\
            .execute()
        
        if quick_scan.data:
            print("✅ Found Quick Scan:")
            scan = quick_scan.data[0]
            print(f"  - Body Part: {scan.get('body_part')}")
            print(f"  - Urgency: {scan.get('urgency_level')}")
            print(f"  - Confidence: {scan.get('confidence_score')}")
            print(f"  - Created: {scan.get('created_at')}")
    
    # Create analysis records for testing
    print("\n" + "=" * 60)
    print("Creating Analysis Records for Testing")
    print("=" * 60)
    
    # Analysis for first user
    analysis1 = {
        "id": str(uuid.uuid4()),
        "user_id": "45b61b67-175d-48a0-aca6-d0be57609383",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Test neurology report",
        "recommended_type": "neurology",
        "confidence": 0.85,
        "report_config": {
            "time_range": {
                "start": "2025-01-01",
                "end": "2025-01-31"
            }
        }
    }
    
    try:
        supabase.table("report_analyses").insert(analysis1).execute()
        print(f"✅ Created analysis for user 1: {analysis1['id']}")
    except Exception as e:
        print(f"❌ Failed to create analysis: {e}")
    
    # Analysis for second user
    analysis2 = {
        "id": str(uuid.uuid4()),
        "user_id": "323ce656-8d89-46ac-bea1-a6382cc86ce9",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Test specialist report",
        "recommended_type": "specialist",
        "confidence": 0.75,
        "report_config": {
            "time_range": {
                "start": "2025-01-01",
                "end": "2025-01-31"
            }
        }
    }
    
    try:
        supabase.table("report_analyses").insert(analysis2).execute()
        print(f"✅ Created analysis for user 2: {analysis2['id']}")
    except Exception as e:
        print(f"❌ Failed to create analysis: {e}")
    
    return analysis1['id'], analysis2['id']

if __name__ == "__main__":
    analysis1_id, analysis2_id = asyncio.run(test_data_gathering())
    
    print("\n" + "=" * 60)
    print("CURL COMMANDS TO TEST:")
    print("=" * 60)
    
    print("\n1. Test Neurology Report for User 1:")
    print(f"""
curl -X POST http://localhost:8000/api/report/neurology \\
  -H "Content-Type: application/json" \\
  -d '{{
    "analysis_id": "{analysis1_id}",
    "user_id": "45b61b67-175d-48a0-aca6-d0be57609383",
    "deep_dive_ids": ["057447a9-3369-42b2-b683-778d10ae5c8b"]
  }}'
""")
    
    print("\n2. Test Specialist Report for User 2:")
    print(f"""
curl -X POST http://localhost:8000/api/report/specialist \\
  -H "Content-Type: application/json" \\
  -d '{{
    "analysis_id": "{analysis2_id}",
    "user_id": "323ce656-8d89-46ac-bea1-a6382cc86ce9",
    "quick_scan_ids": ["01398d26-9974-482e-867a-5e840ca67679"]
  }}'
""")