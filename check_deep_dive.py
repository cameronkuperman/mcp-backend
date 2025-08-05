"""Check if the deep dive exists"""
import asyncio
from supabase_client import supabase
import json

async def check_deep_dive():
    deep_dive_id = "276125e5-b159-4c8f-b199-4744ad0ed6d5"
    user_id = "45b61b67-175d-48a0-aca6-d0be57609383"
    
    # Check if deep dive exists at all
    result = supabase.table("deep_dive_sessions")\
        .select("*")\
        .eq("id", deep_dive_id)\
        .execute()
    
    if result.data:
        dive = result.data[0]
        print(f"Deep Dive Found!")
        print(f"ID: {dive.get('id')}")
        print(f"User ID: {dive.get('user_id')}")
        print(f"Status: {dive.get('status')}")
        print(f"Body Part: {dive.get('body_part')}")
        print(f"Created: {dive.get('created_at')}")
        print(f"User ID matches: {dive.get('user_id') == user_id}")
        
        # Save full record
        with open('deep_dive_record.json', 'w') as f:
            json.dump(dive, f, indent=2, default=str)
        print("\nFull record saved to deep_dive_record.json")
    else:
        print(f"Deep dive {deep_dive_id} not found!")
        
    # Also check any deep dives for this user
    print(f"\n=== All Deep Dives for User {user_id} ===")
    user_dives = supabase.table("deep_dive_sessions")\
        .select("id, body_part, status, created_at")\
        .eq("user_id", user_id)\
        .order("created_at.desc")\
        .limit(10)\
        .execute()
    
    if user_dives.data:
        for dive in user_dives.data:
            print(f"- {dive['id']} | {dive['body_part']} | {dive['status']} | {dive['created_at'][:19]}")
    else:
        print("No deep dives found for this user")

asyncio.run(check_deep_dive())