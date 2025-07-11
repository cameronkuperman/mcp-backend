#!/usr/bin/env python3
"""Test OpenRouter connection"""
import asyncio
from business_logic import call_llm
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    print("Testing OpenRouter connection...")
    print(f"API Key exists: {bool(os.getenv('OPENROUTER_API_KEY'))}")
    
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, OpenRouter is working!'"}
        ]
        
        result = await call_llm(messages, user_id="test-user")
        print(f"✅ Success! Response: {result['content']}")
        print(f"Model used: {result['model']}")
        print(f"Tokens: {result['usage']}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())