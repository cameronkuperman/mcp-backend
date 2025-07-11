#!/usr/bin/env python3
"""Test the OpenRouter proxy approach"""
import asyncio
from openrouter_proxy import call_llm_with_proxy

async def test_proxy():
    messages = [
        {"role": "system", "content": "You are Oracle, a helpful health assistant."},
        {"role": "user", "content": "Hello, can you help me understand headaches?"}
    ]
    
    print("Testing OpenRouter proxy...")
    try:
        response = await call_llm_with_proxy(messages)
        print(f"✅ Success!")
        print(f"Endpoint used: {response.get('endpoint_used', 'unknown')}")
        print(f"Model: {response['model']}")
        print(f"Response: {response['content'][:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_proxy())