"""Test script to verify specialist report data gathering"""
import asyncio
import json
from utils.data_gathering import gather_selected_data
import os
from dotenv import load_dotenv

load_dotenv()

async def test_data_gathering():
    """Test the data gathering with provided IDs"""
    
    user_id = "45b61b67-175d-48a0-aca6-d0be57609383"
    deep_dive_id = "276125e5-b159-4c8f-b199-4744ad0ed6d5"
    
    print(f"Testing data gathering for:")
    print(f"User ID: {user_id}")
    print(f"Deep Dive ID: {deep_dive_id}")
    print("-" * 50)
    
    try:
        # Call gather_selected_data with just the deep dive ID
        data = await gather_selected_data(
            user_id=user_id,
            deep_dive_ids=[deep_dive_id]
        )
        
        # Print summary
        print("\n=== DATA SUMMARY ===")
        print(f"Medical Profile: {'Found' if data.get('medical_profile') else 'Not Found'}")
        if data.get('medical_profile'):
            profile = data['medical_profile']
            print(f"  - Name: {profile.get('name', 'N/A')}")
            print(f"  - Age: {profile.get('age', 'N/A')}")
            print(f"  - Gender: {'Male' if profile.get('is_male') else 'Female' if profile.get('is_male') is False else 'N/A'}")
            print(f"  - Medications: {len(profile.get('medications', [])) if profile.get('medications') else 0}")
            print(f"  - Allergies: {len(profile.get('allergies', [])) if profile.get('allergies') else 0}")
            print(f"  - Family History: {len(profile.get('family_history', [])) if profile.get('family_history') else 0}")
        
        print(f"\nPrimary Interactions:")
        print(f"  - Quick Scans: {len(data.get('quick_scans', []))}")
        print(f"  - Deep Dives: {len(data.get('deep_dives', []))}")
        print(f"  - General Assessments: {len(data.get('general_assessments', []))}")
        print(f"  - Photo Analyses: {len(data.get('photo_analyses', []))}")
        
        print(f"\nSupplementary Data:")
        print(f"  - Symptom Tracking: {len(data.get('symptom_tracking', []))}")
        print(f"  - Chat Summaries: {len(data.get('llm_summaries', []))}")
        
        # Print deep dive details
        if data.get('deep_dives'):
            print("\n=== DEEP DIVE DETAILS ===")
            for dive in data['deep_dives']:
                print(f"ID: {dive.get('id')}")
                print(f"Body Part: {dive.get('body_part')}")
                print(f"Status: {dive.get('status')}")
                print(f"Created: {dive.get('created_at', '')[:19]}")
                print(f"Questions Asked: {len(dive.get('questions', []))}")
                if dive.get('form_data'):
                    print(f"Initial Symptoms: {json.dumps(dive['form_data'], indent=2)}")
                if dive.get('final_analysis'):
                    print(f"Has Final Analysis: Yes")
                    print(f"Final Confidence: {dive.get('final_confidence')}")
        
        # Save full data to file for inspection
        with open('test_data_output.json', 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"\nFull data saved to test_data_output.json")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_data_gathering())