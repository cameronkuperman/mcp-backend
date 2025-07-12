#!/usr/bin/env python3
"""Test summary generation and database insertion"""
import requests
import uuid
import json
from supabase_client import supabase

# Test with proper UUIDs
user_id = str(uuid.uuid4())
conversation_id = str(uuid.uuid4())

print(f"Test User ID: {user_id}")
print(f"Test Conversation ID: {conversation_id}")
print("-" * 60)

# First, create a user in the medical table (required for foreign key)
print("Creating user in medical table...")
medical_data = {
    "id": user_id,
    "created_at": "2025-01-17T12:00:00Z",
    "user_data": {"test": True, "name": "Test User"}
}
medical_response = supabase.table("medical").insert(medical_data).execute()
print(f"Medical user created: {bool(medical_response.data)}")

# First, create a conversation
print("Creating conversation...")
conv_data = {
    "id": conversation_id,
    "user_id": user_id,
    "title": "Test Health Chat",
    "ai_provider": "openrouter",
    "model_name": "deepseek/deepseek-chat",
    "conversation_type": "health_analysis",
    "status": "active",
    "message_count": 0,
    "total_tokens": 0
}
conv_response = supabase.table("conversations").insert(conv_data).execute()
print(f"Conversation created: {bool(conv_response.data)}")

# Insert some test messages directly
print("\nInserting test messages...")
messages = [
    {"role": "user", "content": "I have severe migraines"},
    {"role": "assistant", "content": "I understand you're experiencing severe migraines. How long have you had them?"},
    {"role": "user", "content": "For about 5 years, they happen 3 times a week"},
    {"role": "assistant", "content": "That's quite frequent. Have you tried any treatments?"}
]

for msg in messages:
    msg_data = {
        "conversation_id": conversation_id,
        "role": msg["role"],
        "content": msg["content"],
        "content_type": "text",
        "token_count": len(msg["content"].split())
    }
    msg_response = supabase.table("messages").insert(msg_data).execute()
    print(f"  - Inserted {msg['role']} message: {bool(msg_response.data)}")

# Now test summary generation
print("\n" + "="*60)
print("Testing summary generation...")

response = requests.post(
    "http://localhost:8000/api/generate_summary",
    json={
        "conversation_id": conversation_id,
        "user_id": user_id
    }
)

print(f"\nStatus Code: {response.status_code}")
result = response.json()
print(f"Response: {json.dumps(result, indent=2)}")

# Check if summary was saved
print("\n" + "="*60)
print("Checking if summary was saved to database...")
summary_check = supabase.table("llm_context").select("*").eq("conversation_id", conversation_id).execute()
if summary_check.data:
    print("✅ Summary found in database!")
    print(f"Summary: {summary_check.data[0]['llm_summary'][:200]}...")
else:
    print("❌ Summary NOT found in database!")
    
# Cleanup
print("\nCleaning up test data...")
supabase.table("messages").delete().eq("conversation_id", conversation_id).execute()
supabase.table("conversations").delete().eq("id", conversation_id).execute()
supabase.table("llm_context").delete().eq("conversation_id", conversation_id).execute()
supabase.table("medical").delete().eq("id", user_id).execute()
print("Done!")