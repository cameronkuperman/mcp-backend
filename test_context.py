"""Test script to debug context building"""
import asyncio
from supabase_client import supabase
from utils.context_builder import get_enhanced_llm_context

async def test_context():
    # First, let's see what users have data
    print("=== Checking for users with llm_context data ===")
    llm_users = supabase.table("llm_context").select("user_id").limit(10).execute()
    if llm_users.data:
        print(f"Found {len(llm_users.data)} llm_context records")
        unique_users = list(set(u['user_id'] for u in llm_users.data if u.get('user_id')))
        print(f"Unique users with llm_context: {unique_users[:5]}")
        
        if unique_users:
            test_user = unique_users[0]
            print(f"\n=== Testing with user: {test_user} ===")
            
            # Test the enhanced context function
            context = await get_enhanced_llm_context(test_user, "test-conv-id", "test query")
            print(f"Enhanced context result:")
            print(f"Length: {len(context)}")
            print(f"Content preview: {context[:500] if context else 'EMPTY'}")
    else:
        print("No llm_context data found")
    
    print("\n=== Checking for users with quick_scans ===")
    scan_users = supabase.table("quick_scans").select("user_id").limit(10).execute()
    if scan_users.data:
        print(f"Found {len(scan_users.data)} quick_scan records")
        unique_scan_users = list(set(u['user_id'] for u in scan_users.data if u.get('user_id')))
        print(f"Unique users with quick_scans: {unique_scan_users[:5]}")

if __name__ == "__main__":
    asyncio.run(test_context())