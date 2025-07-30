#!/usr/bin/env python3
"""Test script for weekly AI predictions system"""
import asyncio
import httpx
import json
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-123"  # Replace with actual user ID

async def test_initial_generation():
    """Test initial prediction generation for new user"""
    print("\n🚀 Testing Initial Prediction Generation...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/ai/generate-initial/{TEST_USER_ID}",
                timeout=120.0  # 2 minute timeout for AI generation
            )
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data['status'] == 'success':
                    print("✅ Initial predictions generated successfully!")
                    print(f"   Prediction ID: {data['prediction_id']}")
                elif data['status'] == 'already_generated':
                    print("ℹ️  Initial predictions already exist for this user")
                else:
                    print(f"❌ Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_get_weekly_predictions():
    """Test fetching weekly predictions"""
    print("\n📊 Testing Get Weekly Predictions...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/ai/weekly/{TEST_USER_ID}")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Status: {data['status']}")
                
                if data['status'] == 'success' and data.get('predictions'):
                    predictions = data['predictions']
                    print("\n✅ Weekly predictions found!")
                    print(f"   Generated at: {predictions['generated_at']}")
                    print(f"   Data quality: {predictions.get('data_quality_score', 0)}%")
                    print(f"   Is current: {predictions['is_current']}")
                    
                    if predictions.get('dashboard_alert'):
                        print(f"\n   Dashboard Alert:")
                        alert = predictions['dashboard_alert']
                        print(f"     - {alert['title']}")
                        print(f"     - Severity: {alert['severity']}")
                        print(f"     - Confidence: {alert['confidence']}%")
                    
                    print(f"\n   Predictions: {len(predictions.get('predictions', []))} total")
                    print(f"   Pattern Questions: {len(predictions.get('pattern_questions', []))} total")
                    print(f"   Body Patterns: {len(predictions.get('body_patterns', {}).get('tendencies', []))} tendencies")
                    
                elif data['status'] == 'needs_initial':
                    print("ℹ️  User needs initial prediction generation")
                else:
                    print("ℹ️  No predictions found yet")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_get_alert_only():
    """Test fetching just the dashboard alert"""
    print("\n🚨 Testing Get Dashboard Alert Only...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{BASE_URL}/api/ai/weekly/{TEST_USER_ID}/alert")
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                if data.get('alert'):
                    alert = data['alert']
                    print("✅ Dashboard alert found!")
                    print(f"   Title: {alert['title']}")
                    print(f"   Description: {alert['description']}")
                    print(f"   Severity: {alert['severity']}")
                    print(f"   Confidence: {alert['confidence']}%")
                else:
                    print("ℹ️  No alert available")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def test_preferences():
    """Test user preferences management"""
    print("\n⚙️  Testing User Preferences...")
    
    async with httpx.AsyncClient() as client:
        # Get current preferences
        try:
            response = await client.get(f"{BASE_URL}/api/ai/preferences/{TEST_USER_ID}")
            print(f"GET Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                prefs = data['preferences']
                print("Current preferences:")
                print(f"   Enabled: {prefs['weekly_generation_enabled']}")
                print(f"   Day: {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'][prefs['preferred_day_of_week']]}")
                print(f"   Hour: {prefs['preferred_hour']}:00")
                print(f"   Timezone: {prefs['timezone']}")
                print(f"   Initial generated: {prefs['initial_predictions_generated']}")
        except Exception as e:
            print(f"❌ Error getting preferences: {str(e)}")
        
        # Update preferences
        print("\nUpdating preferences...")
        try:
            new_prefs = {
                "weekly_generation_enabled": True,
                "preferred_day_of_week": 5,  # Friday
                "preferred_hour": 18,  # 6 PM
                "timezone": "America/New_York"
            }
            
            response = await client.put(
                f"{BASE_URL}/api/ai/preferences/{TEST_USER_ID}",
                json=new_prefs
            )
            print(f"PUT Status: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Preferences updated successfully!")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error updating preferences: {str(e)}")


async def test_regenerate():
    """Test manual regeneration"""
    print("\n🔄 Testing Manual Regeneration...")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BASE_URL}/api/ai/regenerate/{TEST_USER_ID}",
                timeout=120.0
            )
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response: {json.dumps(data, indent=2)}")
                
                if data['status'] == 'success':
                    print("✅ Predictions regenerated successfully!")
                elif data['status'] == 'rate_limited':
                    print(f"⏳ Rate limited: {data['message']}")
                else:
                    print(f"❌ Error: {data.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")


async def main():
    """Run all tests"""
    print("🧪 Weekly AI Predictions Test Suite")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User ID: {TEST_USER_ID}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    
    # Run tests in sequence
    if len(sys.argv) > 1:
        if sys.argv[1] == "--initial":
            await test_initial_generation()
        elif sys.argv[1] == "--weekly":
            await test_get_weekly_predictions()
        elif sys.argv[1] == "--alert":
            await test_get_alert_only()
        elif sys.argv[1] == "--prefs":
            await test_preferences()
        elif sys.argv[1] == "--regenerate":
            await test_regenerate()
        else:
            print("Unknown option. Use: --initial, --weekly, --alert, --prefs, or --regenerate")
    else:
        # Run all tests
        await test_get_weekly_predictions()
        await test_get_alert_only()
        await test_preferences()
        print("\n💡 To test initial generation: python test_weekly_ai.py --initial")
        print("💡 To test regeneration: python test_weekly_ai.py --regenerate")
    
    print("\n✨ Test suite completed!")


if __name__ == "__main__":
    asyncio.run(main())