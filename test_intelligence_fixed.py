#!/usr/bin/env python3
"""
Test script for Health Intelligence endpoints - FIXED VERSION
Tests insights and shadow patterns with proper UUID handling

Run with: python test_intelligence_fixed.py [user-uuid]
Example: python test_intelligence_fixed.py 123e4567-e89b-12d3-a456-426614174000
"""
import httpx
import asyncio
import json
import sys
import uuid
from datetime import datetime
from typing import Optional

# Configuration
BASE_URL = "http://localhost:8000"

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
MAGENTA = '\033[95m'
RESET = '\033[0m'

class IntelligenceTester:
    def __init__(self, user_id: str):
        # Validate UUID format
        try:
            uuid.UUID(user_id)
            self.user_id = user_id
            print(f"{GREEN}✓ Valid UUID: {user_id}{RESET}")
        except ValueError:
            print(f"{RED}✗ Invalid UUID format: {user_id}{RESET}")
            print(f"{YELLOW}Using a generated UUID instead...{RESET}")
            self.user_id = str(uuid.uuid4())
            print(f"{GREEN}Generated UUID: {self.user_id}{RESET}")
        
        self.client = None
        self.results = {}
    
    async def test_insights_generation(self) -> dict:
        """Test the insights generation endpoint"""
        print(f"\n{BLUE}=== Testing Insights Generation ==={RESET}")
        
        # Test without force refresh first
        print(f"\n{MAGENTA}1. Testing without force_refresh:{RESET}")
        url = f"{BASE_URL}/api/generate-insights/{self.user_id}"
        
        try:
            response = await self.client.post(url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"{GREEN}   ✓ Success!{RESET}")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Insights Count: {data.get('count', 0)}")
                
                insights = data.get('insights', [])
                if insights:
                    print(f"\n   {YELLOW}Sample Insights:{RESET}")
                    for i, insight in enumerate(insights[:2]):  # Show first 2
                        print(f"   {i+1}. {insight.get('title', 'No title')}")
                        print(f"      Type: {insight.get('insight_type', 'unknown')}")
                        print(f"      Confidence: {insight.get('confidence', 0)}%")
                        print(f"      Description: {insight.get('description', 'No description')[:100]}...")
                
                self.results['insights_without_refresh'] = data
                return data
            else:
                print(f"{RED}   ✗ Failed with status {response.status_code}{RESET}")
                error = response.json() if response.text else "No error details"
                print(f"   Error: {error}")
                return {"error": error, "status_code": response.status_code}
                
        except Exception as e:
            print(f"{RED}   ✗ Exception: {str(e)}{RESET}")
            return {"error": str(e)}
    
    async def test_insights_force_refresh(self) -> dict:
        """Test insights with force refresh"""
        print(f"\n{MAGENTA}2. Testing with force_refresh=true:{RESET}")
        url = f"{BASE_URL}/api/generate-insights/{self.user_id}?force_refresh=true"
        
        try:
            response = await self.client.post(url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"{GREEN}   ✓ Success with force refresh!{RESET}")
                print(f"   Fresh insights generated: {data.get('count', 0)}")
                self.results['insights_force_refresh'] = data
                return data
            else:
                print(f"{RED}   ✗ Failed with status {response.status_code}{RESET}")
                error = response.json() if response.text else "No error details"
                print(f"   Error: {error}")
                return {"error": error}
                
        except Exception as e:
            print(f"{RED}   ✗ Exception: {str(e)}{RESET}")
            return {"error": str(e)}
    
    async def test_shadow_patterns_generation(self) -> dict:
        """Test the shadow patterns generation endpoint"""
        print(f"\n{BLUE}=== Testing Shadow Patterns Generation ==={RESET}")
        
        print(f"\n{MAGENTA}1. Testing without force_refresh:{RESET}")
        url = f"{BASE_URL}/api/generate-shadow-patterns/{self.user_id}"
        
        try:
            response = await self.client.post(url)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"{GREEN}   ✓ Success!{RESET}")
                print(f"   Status: {data.get('status', 'unknown')}")
                print(f"   Shadow Patterns Count: {data.get('count', 0)}")
                
                patterns = data.get('shadow_patterns', [])
                if patterns:
                    print(f"\n   {YELLOW}Sample Shadow Patterns:{RESET}")
                    for i, pattern in enumerate(patterns[:2]):  # Show first 2
                        print(f"   {i+1}. {pattern.get('pattern_name', 'No name')}")
                        print(f"      Category: {pattern.get('pattern_category', 'unknown')}")
                        print(f"      Significance: {pattern.get('significance', 'unknown')}")
                        print(f"      Last Seen: {pattern.get('last_seen_description', 'No description')[:100]}...")
                        print(f"      Days Missing: {pattern.get('days_missing', 0)}")
                
                self.results['shadow_patterns'] = data
                return data
            else:
                print(f"{RED}   ✗ Failed with status {response.status_code}{RESET}")
                error = response.json() if response.text else "No error details"
                print(f"   Error: {error}")
                
                # Check if it's because no historical data
                if "no_data" in str(error).lower() or "empty" in str(error).lower():
                    print(f"{YELLOW}   ℹ Shadow patterns need historical data to compare against.{RESET}")
                    print(f"   Tip: Shadow patterns work best after tracking health for 2+ weeks.")
                
                return {"error": error, "status_code": response.status_code}
                
        except Exception as e:
            print(f"{RED}   ✗ Exception: {str(e)}{RESET}")
            return {"error": str(e)}
    
    async def test_get_endpoints(self) -> dict:
        """Test the GET endpoints for retrieving stored data"""
        print(f"\n{BLUE}=== Testing GET Endpoints ==={RESET}")
        
        endpoints = [
            ("insights", f"/api/insights/{self.user_id}"),
            ("shadow-patterns", f"/api/shadow-patterns/{self.user_id}"),
        ]
        
        for name, url in endpoints:
            print(f"\n{MAGENTA}Testing GET {name}:{RESET}")
            try:
                response = await self.client.get(url)
                print(f"   Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get(name.replace('-', '_'), [])
                    print(f"{GREEN}   ✓ Retrieved {len(items)} {name}{RESET}")
                    self.results[f'get_{name}'] = data
                else:
                    print(f"{RED}   ✗ Failed with status {response.status_code}{RESET}")
                    
            except Exception as e:
                print(f"{RED}   ✗ Exception: {str(e)}{RESET}")
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Health Intelligence Endpoint Tests - Fixed Version{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        print(f"Base URL: {BASE_URL}")
        print(f"User ID: {self.user_id}")
        print(f"User ID Type: {type(self.user_id).__name__}")
        
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
            self.client = client
            
            # Run tests
            await self.test_insights_generation()
            await asyncio.sleep(1)  # Small delay between tests
            
            await self.test_insights_force_refresh()
            await asyncio.sleep(1)
            
            await self.test_shadow_patterns_generation()
            await asyncio.sleep(1)
            
            await self.test_get_endpoints()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary and recommendations"""
        print(f"\n{BLUE}{'='*60}{RESET}")
        print(f"{BLUE}Test Summary{RESET}")
        print(f"{BLUE}{'='*60}{RESET}")
        
        # Count successes
        successes = sum(1 for k, v in self.results.items() 
                       if isinstance(v, dict) and 'error' not in v)
        total = len(self.results)
        
        print(f"Total Tests Run: {total}")
        print(f"{GREEN}Passed: {successes}{RESET}")
        print(f"{RED}Failed: {total - successes}{RESET}")
        
        # Recommendations
        print(f"\n{YELLOW}=== Recommendations ==={RESET}")
        
        if 'insights_without_refresh' in self.results:
            data = self.results['insights_without_refresh']
            if data.get('status') == 'no_data':
                print("1. No health data found - Start tracking symptoms in Oracle chat")
                print("2. Use Quick Scan or Deep Dive to generate health data")
            elif data.get('count', 0) == 0:
                print("1. Insights generation returned empty - Check AI service logs")
                print("2. Verify OpenRouter API key is configured")
        
        if 'shadow_patterns' in self.results:
            data = self.results['shadow_patterns']
            if 'error' in data or data.get('count', 0) == 0:
                print("3. Shadow patterns need historical data (2+ weeks)")
                print("4. They detect what you STOPPED mentioning")
                print("5. Track consistently for better shadow pattern detection")
        
        print(f"\n{YELLOW}=== Frontend Implementation Notes ==={RESET}")
        print("1. Always use valid UUID format for user_id")
        print("2. Handle 'no_data' status gracefully")
        print("3. Shadow patterns may be empty for new users")
        print("4. Insights work without health stories (uses Oracle context)")
        print("5. Check 'cached_from' field to show data freshness")

async def main():
    """Main test runner"""
    # Get user ID from command line or use default
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        # Generate a sample UUID
        user_id = str(uuid.uuid4())
        print(f"{YELLOW}No user ID provided. Using generated UUID: {user_id}{RESET}")
        print(f"Usage: python {sys.argv[0]} <user-uuid>")
        print(f"Example: python {sys.argv[0]} 123e4567-e89b-12d3-a456-426614174000\n")
    
    tester = IntelligenceTester(user_id)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())