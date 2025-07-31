#!/usr/bin/env python3
"""
Test script for Health Intelligence endpoints
Run with: python test_intelligence.py [user-id]
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
            if "insights" in url and "/generate-" in url:
                insights = result.get('insights', [])
                print(f"  Insights Generated: {len(insights)}")
                if insights:
                    print(f"  First Insight: {insights[0].get('title', 'N/A')}")
                    print(f"  Type: {insights[0].get('insight_type', 'N/A')}")
                    
            elif "predictions" in url and "/generate-" in url:
                predictions = result.get('predictions', [])
                print(f"  Predictions Generated: {len(predictions)}")
                if predictions:
                    print(f"  First Prediction: {predictions[0].get('event_description', 'N/A')}")
                    print(f"  Probability: {predictions[0].get('probability', 'N/A')}%")
                    
            elif "shadow-patterns" in url and "/generate-" in url:
                patterns = result.get('shadow_patterns', [])
                print(f"  Shadow Patterns Found: {len(patterns)}")
                if patterns:
                    print(f"  First Pattern: {patterns[0].get('pattern_name', 'N/A')}")
                    print(f"  Significance: {patterns[0].get('significance', 'N/A')}")
                    
            elif "strategies" in url and "/generate-" in url:
                strategies = result.get('strategies', [])
                print(f"  Strategies Generated: {len(strategies)}")
                if strategies:
                    print(f"  First Strategy: {strategies[0].get('strategy', 'N/A')[:60]}...")
                    print(f"  Priority: {strategies[0].get('priority', 'N/A')}")
                    
            elif "generate-weekly-analysis" in url:
                print(f"  Story ID: {result.get('story_id', 'N/A')}")
                print(f"  Insights: {len(result.get('insights', []))}")
                print(f"  Predictions: {len(result.get('predictions', []))}")
                print(f"  Shadow Patterns: {len(result.get('shadow_patterns', []))}")
                print(f"  Strategies: {len(result.get('strategies', []))}")
                
            elif "health-analysis" in url:
                if result.get('insights') is not None:
                    print(f"  Stored Insights: {len(result.get('insights', []))}")
                    print(f"  Stored Predictions: {len(result.get('predictions', []))}")
                    print(f"  Stored Patterns: {len(result.get('shadow_patterns', []))}")
                    print(f"  Stored Strategies: {len(result.get('strategies', []))}")
            
            # Show status if available
            if 'status' in result:
                status_color = GREEN if result['status'] == 'success' else YELLOW
                print(f"  Status: {status_color}{result['status']}{RESET}")
                
            if 'message' in result:
                print(f"  Message: {result['message']}")
                
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
    print(f"{BLUE}=== Health Intelligence Endpoint Tests ==={RESET}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User: {TEST_USER_ID}")
    
    # Define all endpoints to test
    endpoints = [
        # Get stored data first
        ("GET", f"/api/health-analysis/{TEST_USER_ID}", "Get Stored Analysis"),
        
        # Individual generation endpoints
        ("POST", f"/api/generate-insights/{TEST_USER_ID}", "Generate Insights Only"),
        ("POST", f"/api/generate-predictions/{TEST_USER_ID}", "Generate Predictions Only"),
        ("POST", f"/api/generate-shadow-patterns/{TEST_USER_ID}", "Generate Shadow Patterns Only"),
        ("POST", f"/api/generate-strategies/{TEST_USER_ID}", "Generate Strategies Only"),
        
        # Complete weekly analysis
        ("POST", f"/api/generate-weekly-analysis", "Generate Complete Analysis", {
            "user_id": TEST_USER_ID,
            "force_refresh": False,
            "include_predictions": True,
            "include_patterns": True,
            "include_strategies": True
        }),
        
        # Get individual components
        ("GET", f"/api/insights/{TEST_USER_ID}", "Get Insights"),
        ("GET", f"/api/predictions/{TEST_USER_ID}", "Get Predictions"),
        ("GET", f"/api/shadow-patterns/{TEST_USER_ID}", "Get Shadow Patterns"),
        ("GET", f"/api/strategies/{TEST_USER_ID}", "Get Strategies"),
    ]
    
    success_count = 0
    total_count = len(endpoints)
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        for method, url, name, *args in endpoints:
            data = args[0] if args else None
            if await test_endpoint(client, method, url, name, data):
                success_count += 1
            await asyncio.sleep(1)  # Delay between requests to avoid rate limiting
    
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
        print("1. Ensure user has a health story generated for this week")
        print("2. Check if Gemini 2.5 Pro API is configured correctly")
        print("3. Verify database permissions for all tables")
        print("4. Check server logs for detailed error messages")
        print("5. Shadow patterns need historical data (>3 sessions)")

if __name__ == "__main__":
    # Get user ID from command line if provided
    if len(sys.argv) > 1:
        TEST_USER_ID = sys.argv[1]
        
    asyncio.run(main())