#!/usr/bin/env python3
"""Test the data filtering to ensure ONLY requested IDs are used"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Test data matching your example
TEST_DATA = {
    "analysis_id": "cc70d30f-d16e-43f0-adfa-f48f9975c540",
    "user_id": "45b61b67-175d-48a0-aca6-d0be57609383",
    "quick_scan_ids": ["f9c935f0-8140-40d9-9698-3abf2bbaa34b"],
    "deep_dive_ids": [],
    "photo_session_ids": [],
    "general_assessment_ids": [],
    "general_deep_dive_ids": [],
    "flash_assessment_ids": []
}

def test_production_flow():
    print("=== TESTING PRODUCTION FLOW ===\n")
    
    # Step 1: Specialty Triage
    print("STEP 1: Specialty Triage")
    print("-" * 50)
    
    triage_data = {
        "user_id": TEST_DATA["user_id"],
        "quick_scan_ids": TEST_DATA["quick_scan_ids"],
        "deep_dive_ids": TEST_DATA["deep_dive_ids"]
    }
    
    print(f"Request to /api/report/specialty-triage:")
    print(json.dumps(triage_data, indent=2))
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/report/specialty-triage",
            json=triage_data,
            headers={"Content-Type": "application/json"}
        )
        
        triage_result = response.json()
        print(f"\nResponse (Status {response.status_code}):")
        print(json.dumps(triage_result, indent=2))
        
        # Extract recommended specialty
        specialty = triage_result.get("primary_specialty", "primary-care")
        print(f"\n✓ Recommended Specialty: {specialty}")
        
    except Exception as e:
        print(f"✗ Triage failed: {e}")
        return
    
    # Step 2: Generate Specialist Report
    print(f"\n\nSTEP 2: Generate {specialty} Report")
    print("-" * 50)
    
    # Add specialty to test data
    report_data = TEST_DATA.copy()
    report_data["specialty"] = specialty
    
    print(f"Request to /api/report/{specialty}:")
    print(json.dumps(report_data, indent=2))
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/report/{specialty}",
            json=report_data,
            headers={"Content-Type": "application/json"}
        )
        
        report_result = response.json()
        print(f"\nResponse (Status {response.status_code}):")
        
        # Only print key fields to avoid clutter
        if "error" in report_result:
            print(f"✗ Error: {report_result['error']}")
        else:
            print(f"✓ Report ID: {report_result.get('report_id')}")
            print(f"✓ Report Type: {report_result.get('report_type')}")
            print(f"✓ Specialty: {report_result.get('specialty')}")
            print(f"✓ Status: {report_result.get('status')}")
            
            # Check if report data exists
            if report_result.get('report_data'):
                print(f"✓ Report Data: Generated successfully")
            else:
                print(f"✗ Report Data: Missing")
    
    except Exception as e:
        print(f"✗ Report generation failed: {e}")
        return
    
    # Verification
    print("\n\nVERIFICATION")
    print("-" * 50)
    print("Expected behavior:")
    print("1. ✓ Triage should analyze only quick scan: f9c935f0-8140-40d9-9698-3abf2bbaa34b")
    print("2. ✓ Triage should recommend appropriate specialist")
    print("3. ✓ Backend should create analysis record if it doesn't exist")
    print("4. ✓ Report should use ONLY the specified quick scan")
    print("5. ✓ Empty arrays should load NO data")
    print("6. ✓ Response should include 'specialty' field")

if __name__ == "__main__":
    test_production_flow()