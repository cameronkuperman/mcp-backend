#!/usr/bin/env python3
"""Test synchronous OpenRouter call"""
import os
from dotenv import load_dotenv
from business_logic import get_user_data, get_llm_context, call_llm
import asyncio

load_dotenv()

async def test_sync():
    # Test the call_llm function directly
    messages = [
        {"role": "system", "content": "You are Oracle, a health assistant."},
        {"role": "user", "content": "I have a headache. What should I do?"}
    ]
    
    print("Testing call_llm function...")
    try:
        result = await call_llm(messages=messages, model="deepseek/deepseek-chat")
        print(f"✅ Success!")
        print(f"Model: {result['model']}")
        print(f"Response: {result['content'][:200]}...")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_sync())