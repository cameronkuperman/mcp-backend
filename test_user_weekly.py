#!/usr/bin/env python3
"""Test all weekly AI endpoints for specific user"""
import asyncio
import httpx
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000"
USER_ID = "45b61b67-175d-48a0-aca6-d0be57609383"


async def test_all_endpoints():
    """Test all weekly AI endpoints"""
    print(f"🧪 Testing Weekly AI Endpoints for User: {USER_ID}")
    print(f"Base URL: {BASE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        
        # 1. Get current preferences
        print("\n1️⃣ GET /api/ai/preferences/{user_id}")
        print("-" * 40)
        try:
            response = await client.get(f"{BASE_URL}/api/ai/preferences/{USER_ID}")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # 2. Get weekly predictions
        print("\n\n2️⃣ GET /api/ai/weekly/{user_id}")
        print("-" * 40)
        try:
            response = await client.get(f"{BASE_URL}/api/ai/weekly/{USER_ID}")
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"Response Status: {data.get('status')}")
            
            if data.get('status') == 'success' and data.get('predictions'):
                pred = data['predictions']
                print(f"\nPrediction Details:")
                print(f"  - ID: {pred.get('id')}")
                print(f"  - Generated at: {pred.get('generated_at')}")
                print(f"  - Data quality score: {pred.get('data_quality_score')}%")
                print(f"  - Is current: {pred.get('is_current')}")
                print(f"  - Viewed at: {pred.get('viewed_at')}")
                
                # Dashboard alert
                if pred.get('dashboard_alert'):
                    alert = pred['dashboard_alert']
                    print(f"\n  Dashboard Alert:")
                    print(f"    - Title: {alert.get('title')}")
                    print(f"    - Severity: {alert.get('severity')}")
                    print(f"    - Confidence: {alert.get('confidence')}%")
                    print(f"    - Description: {alert.get('description')}")
                else:
                    print(f"\n  Dashboard Alert: None")
                
                # Predictions
                print(f"\n  Predictions: {len(pred.get('predictions', []))} total")
                for i, p in enumerate(pred.get('predictions', [])[:2]):
                    print(f"    {i+1}. {p.get('title')} ({p.get('confidence')}% confidence)")
                
                # Pattern questions
                print(f"\n  Pattern Questions: {len(pred.get('pattern_questions', []))} total")
                for i, q in enumerate(pred.get('pattern_questions', [])[:2]):
                    print(f"    {i+1}. {q.get('question')}")
                
                # Body patterns
                patterns = pred.get('body_patterns', {})
                print(f"\n  Body Patterns:")
                print(f"    - Tendencies: {len(patterns.get('tendencies', []))} found")
                print(f"    - Positive responses: {len(patterns.get('positiveResponses', []))} found")
            else:
                print(f"Full Response: {json.dumps(data, indent=2)}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # 3. Get dashboard alert only
        print("\n\n3️⃣ GET /api/ai/weekly/{user_id}/alert")
        print("-" * 40)
        try:
            response = await client.get(f"{BASE_URL}/api/ai/weekly/{USER_ID}/alert")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # 4. Test initial generation (if needed)
        print("\n\n4️⃣ POST /api/ai/generate-initial/{user_id}")
        print("-" * 40)
        try:
            response = await client.post(f"{BASE_URL}/api/ai/generate-initial/{USER_ID}")
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if data.get('status') == 'already_generated':
                print("✅ Initial predictions already exist")
            elif data.get('status') == 'success':
                print("✅ Initial predictions generated!")
            else:
                print(f"⚠️  Status: {data.get('status')}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # 5. Update preferences
        print("\n\n5️⃣ PUT /api/ai/preferences/{user_id}")
        print("-" * 40)
        try:
            new_prefs = {
                "weekly_generation_enabled": True,
                "preferred_day_of_week": 5,  # Friday
                "preferred_hour": 16,  # 4 PM
                "timezone": "America/New_York"
            }
            print(f"Updating preferences to: {json.dumps(new_prefs, indent=2)}")
            
            response = await client.put(
                f"{BASE_URL}/api/ai/preferences/{USER_ID}",
                json=new_prefs
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # 6. Get preferences again to confirm update
        print("\n\n6️⃣ GET /api/ai/preferences/{user_id} (After Update)")
        print("-" * 40)
        try:
            response = await client.get(f"{BASE_URL}/api/ai/preferences/{USER_ID}")
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # 7. Test regeneration
        print("\n\n7️⃣ POST /api/ai/regenerate/{user_id}")
        print("-" * 40)
        try:
            response = await client.post(f"{BASE_URL}/api/ai/regenerate/{USER_ID}")
            print(f"Status: {response.status_code}")
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2)}")
            
            if data.get('status') == 'rate_limited':
                print(f"⏳ Rate limited: {data.get('message')}")
            elif data.get('status') == 'success':
                print("✅ Predictions regenerated!")
            else:
                print(f"⚠️  Status: {data.get('status')}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        # 8. Get weekly predictions again (after potential regeneration)
        print("\n\n8️⃣ GET /api/ai/weekly/{user_id} (Final Check)")
        print("-" * 40)
        try:
            response = await client.get(f"{BASE_URL}/api/ai/weekly/{USER_ID}")
            print(f"Status: {response.status_code}")
            data = response.json()
            
            if data.get('status') == 'success' and data.get('predictions'):
                pred = data['predictions']
                print(f"✅ Predictions available!")
                print(f"   - Generated at: {pred.get('generated_at')}")
                print(f"   - Has alert: {'Yes' if pred.get('dashboard_alert') else 'No'}")
                print(f"   - Predictions count: {len(pred.get('predictions', []))}")
                print(f"   - Questions count: {len(pred.get('pattern_questions', []))}")
            else:
                print(f"Status: {data.get('status')}")
                print(f"Message: {data.get('message', 'No message')}")
                
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    print("\n" + "=" * 80)
    print("✨ All endpoint tests completed!")


if __name__ == "__main__":
    asyncio.run(test_all_endpoints())