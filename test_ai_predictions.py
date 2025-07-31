#!/usr/bin/env python3
"""
Test script for AI predictions endpoints
Run with: python test_ai_predictions.py
"""
import httpx
import asyncio
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-123"  # Replace with a real user ID

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

async def test_endpoint(client: httpx.AsyncClient, method: str, url: str, name: str, data=None):
    """Test a single endpoint"""
    print(f"\n{BLUE}Testing: {name}{RESET}")
    print(f"  URL: {method} {url}")
    
    try:
        if method == "GET":
            response = await client.get(url)
        elif method == "POST":
            response = await client.post(url, json=data)
        else:
            print(f"{RED}  Unsupported method: {method}{RESET}")
            return False
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"{GREEN}  ✓ Success{RESET}")
            
            # Check for specific fields based on endpoint
            if "dashboard-alert" in url:
                if result.get("alert"):
                    print(f"  Alert: {result['alert'].get('title', 'No title')}")
                    print(f"  Severity: {result['alert'].get('severity', 'N/A')}")
                else:
                    print(f"  {YELLOW}No alert generated (may need more data){RESET}")
                    
            elif "predictions/immediate" in url:
                print(f"  Predictions: {len(result.get('predictions', []))}")
                print(f"  Data Quality: {result.get('data_quality_score', 0)}")
                
            elif "patterns" in url:
                tendencies = result.get('tendencies', [])
                positive = result.get('positive_responses', [])
                print(f"  Tendencies: {len(tendencies)}")
                print(f"  Positive Responses: {len(positive)}")
                if tendencies:
                    print(f"  Example: {tendencies[0][:50]}...")
                    
            elif "questions" in url:
                questions = result.get('questions', [])
                print(f"  Questions: {len(questions)}")
                if questions:
                    print(f"  Example: {questions[0].get('question', 'N/A')}")
                    
            elif "weekly" in url:
                if result.get('predictions'):
                    pred = result['predictions']
                    print(f"  Generation Status: {pred.get('generation_status', 'N/A')}")
                    print(f"  Has Alert: {'Yes' if pred.get('dashboard_alert') else 'No'}")
                    print(f"  Predictions: {len(pred.get('predictions', []))}")
                    print(f"  Patterns: {'Yes' if pred.get('body_patterns') else 'No'}")
            
            # Show status if available
            if 'status' in result:
                print(f"  Status: {result['status']}")
                
            return True
            
        else:
            print(f"{RED}  ✗ Failed with status {response.status_code}{RESET}")
            try:
                error_detail = response.json()
                print(f"  Error: {error_detail}")
            except:
                print(f"  Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"{RED}  ✗ Exception: {str(e)}{RESET}")
        return False

async def main():
    """Run all tests"""
    print(f"{BLUE}=== AI Predictions Endpoint Tests ==={RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User: {TEST_USER_ID}")
    
    # Define all endpoints to test
    endpoints = [
        # Weekly predictions (test this first to ensure record exists)
        ("GET", f"/api/ai/weekly/{TEST_USER_ID}", "Weekly Predictions"),
        
        # Individual endpoints
        ("GET", f"/api/ai/dashboard-alert/{TEST_USER_ID}", "Dashboard Alert"),
        ("GET", f"/api/ai/predictions/immediate/{TEST_USER_ID}", "Immediate Predictions"),
        ("GET", f"/api/ai/predictions/seasonal/{TEST_USER_ID}", "Seasonal Predictions"),
        ("GET", f"/api/ai/predictions/longterm/{TEST_USER_ID}", "Long-term Trajectory"),
        ("GET", f"/api/ai/patterns/{TEST_USER_ID}", "Body Patterns"),
        ("GET", f"/api/ai/questions/{TEST_USER_ID}", "Pattern Questions"),
        
        # Generate weekly (if needed)
        ("POST", f"/api/ai/generate-weekly/{TEST_USER_ID}", "Generate Weekly"),
        
        # Preferences
        ("GET", f"/api/ai/preferences/{TEST_USER_ID}", "Get Preferences"),
    ]
    
    success_count = 0
    total_count = len(endpoints)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        for method, url, name in endpoints:
            if await test_endpoint(client, method, url, name):
                success_count += 1
            await asyncio.sleep(0.5)  # Small delay between requests
    
    # Summary
    print(f"\n{BLUE}=== Test Summary ==={RESET}")
    print(f"Total Tests: {total_count}")
    print(f"{GREEN}Passed: {success_count}{RESET}")
    print(f"{RED}Failed: {total_count - success_count}{RESET}")
    
    if success_count == total_count:
        print(f"\n{GREEN}✓ All tests passed!{RESET}")
    else:
        print(f"\n{YELLOW}⚠ Some tests failed. Check the logs above.{RESET}")
        
    # Additional checks
    print(f"\n{BLUE}=== Recommendations ==={RESET}")
    if success_count < total_count:
        print("1. Check if the user has sufficient health data")
        print("2. Verify database connections are working")
        print("3. Check server logs for detailed error messages")
        print("4. Ensure AI API keys are configured correctly")

if __name__ == "__main__":
    # Get user ID from command line if provided
    if len(sys.argv) > 1:
        TEST_USER_ID = sys.argv[1]
        
    asyncio.run(main())