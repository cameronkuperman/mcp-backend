#!/usr/bin/env python3
"""Test script for AI predictions endpoints"""
import asyncio
import httpx
import json
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-123"  # Replace with actual user ID for testing

async def test_dashboard_alert():
    """Test the dashboard alert endpoint"""
    print("\n🔍 Testing Dashboard Alert Endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/ai/dashboard-alert/{TEST_USER_ID}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data.get("alert"):
                    print("✅ Alert generated successfully!")
                    print(f"   - Severity: {data['alert']['severity']}")
                    print(f"   - Title: {data['alert']['title']}")
                    print(f"   - Confidence: {data['alert']['confidence']}%")
                else:
                    print("ℹ️  No alert generated (insufficient data or no patterns)")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_predictions():
    """Test the predictions endpoint"""
    print("\n🔮 Testing Predictions Endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/ai/predictions/{TEST_USER_ID}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Predictions count: {len(data.get('predictions', []))}")
                print(f"Data quality score: {data.get('data_quality_score', 0)}")
                
                for pred in data.get('predictions', [])[:3]:  # Show first 3
                    print(f"\n📊 {pred['type'].upper()} Prediction:")
                    print(f"   - Title: {pred['title']}")
                    print(f"   - Severity: {pred['severity']}")
                    print(f"   - Confidence: {pred['confidence']}%")
                    print(f"   - Pattern: {pred['pattern']}")
                
                print("\n✅ Predictions generated successfully!")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_pattern_questions():
    """Test the pattern questions endpoint"""
    print("\n❓ Testing Pattern Questions Endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/ai/pattern-questions/{TEST_USER_ID}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                questions = data.get('questions', [])
                print(f"Questions generated: {len(questions)}")
                
                for q in questions[:2]:  # Show first 2
                    print(f"\n💭 Question: {q['question']}")
                    print(f"   - Category: {q['category']}")
                    print(f"   - Relevance: {q['relevanceScore']}%")
                    print(f"   - Answer: {q['answer']}")
                
                print("\n✅ Pattern questions generated successfully!")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_body_patterns():
    """Test the body patterns endpoint"""
    print("\n🧬 Testing Body Patterns Endpoint...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/ai/body-patterns/{TEST_USER_ID}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                patterns = data.get('patterns', {})
                
                print(f"\n🔴 Tendencies ({len(patterns.get('tendencies', []))}):")
                for tendency in patterns.get('tendencies', [])[:2]:
                    print(f"   - {tendency}")
                
                print(f"\n🟢 Positive Responses ({len(patterns.get('positiveResponses', []))}):")
                for positive in patterns.get('positiveResponses', [])[:2]:
                    print(f"   - {positive}")
                
                print(f"\nData points analyzed: {data.get('dataPoints', 0)}")
                print("✅ Body patterns analyzed successfully!")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def create_test_data():
    """Create some test data for the user"""
    print("\n📝 Creating test data...")
    
    async with httpx.AsyncClient() as client:
        # Create a quick scan
        scan_data = {
            "body_part": "head",
            "form_data": {
                "symptoms": "Headache, sensitivity to light",
                "painLevel": 7,
                "duration": "2 hours"
            },
            "user_id": TEST_USER_ID
        }
        
        try:
            response = await client.post(f"{BASE_URL}/api/quick-scan", json=scan_data)
            if response.status_code == 200:
                print("✅ Test quick scan created")
            else:
                print(f"❌ Failed to create quick scan: {response.text}")
        except Exception as e:
            print(f"❌ Error creating test data: {str(e)}")


async def main():
    """Run all tests"""
    print("🚀 Starting AI Predictions API Tests")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User ID: {TEST_USER_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Check if we should create test data
    if len(sys.argv) > 1 and sys.argv[1] == "--create-data":
        await create_test_data()
    
    # Run all tests
    await test_dashboard_alert()
    await test_predictions()
    await test_pattern_questions()
    await test_body_patterns()
    
    print("\n✨ All tests completed!")
    print("\nNote: If you see 'insufficient data' messages, run with --create-data flag")
    print("Example: python test_ai_predictions.py --create-data")


if __name__ == "__main__":
    asyncio.run(main())