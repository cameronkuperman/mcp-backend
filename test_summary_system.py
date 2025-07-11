#!/usr/bin/env python3
"""Test the summary generation system"""
import requests
import json
import uuid

# Generate UUIDs
user_id = str(uuid.uuid4())
conversation_id = str(uuid.uuid4())

print(f"User ID: {user_id}")
print(f"Conversation ID: {conversation_id}")
print("-" * 60)

# Send multiple messages to build a conversation
messages = [
    "I have chronic migraines that occur 15 times per month. They come with severe nausea and light sensitivity.",
    "I've tried ibuprofen but it doesn't help much. The migraines last 4-8 hours each time.",
    "I also get auras before the migraines - zigzag lines in my vision about 30 minutes before the pain starts.",
    "My mother also has migraines. I'm wondering if this is genetic?"
]

for i, msg in enumerate(messages):
    print(f"\nMessage {i+1}: {msg[:50]}...")
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "query": msg,
            "user_id": user_id,
            "conversation_id": conversation_id
        }
    )
    if response.status_code == 200:
        print("✅ Sent successfully")
    else:
        print(f"❌ Error: {response.status_code}")

# Generate summary
print("\n" + "="*60)
print("Generating conversation summary...")
summary_response = requests.post(
    "http://localhost:8000/api/generate_summary",
    json={
        "conversation_id": conversation_id,
        "user_id": user_id
    }
)

if summary_response.status_code == 200:
    result = summary_response.json()
    print("\n✅ Summary generated successfully!")
    print(f"\nSummary ({result.get('token_count', 0)} tokens):")
    print("-" * 60)
    print(result.get('summary', 'No summary'))
    print("-" * 60)
    print(f"Compression ratio: {result.get('compression_ratio', 0)}x")
else:
    print(f"\n❌ Error generating summary: {summary_response.json()}")