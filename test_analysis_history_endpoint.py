#!/usr/bin/env python3
"""
Test script for the new analysis history endpoint
"""

import asyncio
import httpx
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_SESSION_ID = "test-session-123"  # Replace with a real session ID
TEST_ANALYSIS_ID = "test-analysis-456"  # Replace with a real analysis ID

async def test_analysis_history():
    """Test the analysis history endpoint"""
    async with httpx.AsyncClient() as client:
        # Test 1: Basic request without current_analysis_id
        print("Test 1: Basic analysis history request")
        try:
            response = await client.get(
                f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/analysis-history"
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Found {len(data.get('analyses', []))} analyses")
                print(f"   Session: {data.get('session_info', {}).get('condition_name')}")
                print(f"   Date range: {data.get('session_info', {}).get('date_range')}")
                
                # Show first analysis if available
                if data.get('analyses'):
                    first = data['analyses'][0]
                    print(f"\n   First analysis:")
                    print(f"   - Date: {first.get('date')}")
                    print(f"   - Assessment: {first.get('primary_assessment')}")
                    print(f"   - Confidence: {first.get('confidence')}%")
                    print(f"   - Has photo URL: {'photo_url' in first and first['photo_url'] is not None}")
                    print(f"   - Trend: {first.get('trend')}")
                    print(f"   - Urgency: {first.get('urgency_level')}")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        print("\n" + "="*60 + "\n")
        
        # Test 2: Request with current_analysis_id
        print("Test 2: Analysis history with current_analysis_id")
        try:
            response = await client.get(
                f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/analysis-history",
                params={"current_analysis_id": TEST_ANALYSIS_ID}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Current index: {data.get('current_index')}")
                
                # Verify current_index matches the analysis
                if data.get('current_index') is not None:
                    current_idx = data['current_index']
                    if current_idx < len(data.get('analyses', [])):
                        current_analysis = data['analyses'][current_idx]
                        if current_analysis.get('id') == TEST_ANALYSIS_ID:
                            print(f"   ✅ Current analysis ID matches!")
                        else:
                            print(f"   ❌ Current analysis ID mismatch")
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        print("\n" + "="*60 + "\n")
        
        # Test 3: Non-existent session
        print("Test 3: Non-existent session (should return 404)")
        try:
            response = await client.get(
                f"{BASE_URL}/api/photo-analysis/session/non-existent-session/analysis-history"
            )
            
            if response.status_code == 404:
                print(f"✅ Correctly returned 404 for non-existent session")
            else:
                print(f"❌ Unexpected status code: {response.status_code}")
        except Exception as e:
            print(f"❌ Request failed: {e}")

def main():
    """Run the tests"""
    print("Testing Analysis History Endpoint")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test Session ID: {TEST_SESSION_ID}")
    print(f"Test Analysis ID: {TEST_ANALYSIS_ID}")
    print("=" * 60 + "\n")
    
    asyncio.run(test_analysis_history())
    
    print("\n" + "=" * 60)
    print("Testing complete!")
    print("\nNOTE: Replace TEST_SESSION_ID and TEST_ANALYSIS_ID with real values")
    print("from your database to see actual results.")

if __name__ == "__main__":
    main()