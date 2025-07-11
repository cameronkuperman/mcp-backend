#!/usr/bin/env python3
"""Comprehensive test script"""
import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

async def test_openrouter_direct():
    """Test OpenRouter API directly"""
    print("\n1. Testing OpenRouter directly...")
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ No API key found!")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...")
    
    try:
        # Simple test request
        url = "https://api.openrouter.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "openai/gpt-3.5-turbo",  # Use a known working model
            "messages": [
                {"role": "user", "content": "Say 'Hello'"}
            ]
        }
        
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, json=data, ssl=False) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ OpenRouter works! Response: {result['choices'][0]['message']['content']}")
                    return True
                else:
                    error = await resp.text()
                    print(f"❌ OpenRouter error {resp.status}: {error}")
                    return False
                    
    except Exception as e:
        print(f"❌ Connection error: {type(e).__name__}: {e}")
        return False

async def test_server_health():
    """Test if server is running"""
    print("\n2. Testing server health...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/api/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ Server is healthy: {data}")
                    return True
                else:
                    print(f"❌ Server returned {resp.status}")
                    return False
    except Exception as e:
        print(f"❌ Server not running: {e}")
        return False

async def test_chat_endpoint():
    """Test the chat endpoint"""
    print("\n3. Testing chat endpoint...")
    
    try:
        async with aiohttp.ClientSession() as session:
            data = {
                "query": "Hello, are you working?",
                "user_id": "test-user",
                "conversation_id": "test-conv-123",
                "category": "health-scan"
            }
            
            async with session.post("http://localhost:8000/api/chat", json=data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Chat endpoint works!")
                    print(f"   Response preview: {str(result.get('response', ''))[:100]}...")
                    return True
                else:
                    error = await resp.text()
                    print(f"❌ Chat endpoint error {resp.status}: {error}")
                    return False
                    
    except Exception as e:
        print(f"❌ Chat endpoint failed: {e}")
        return False

async def main():
    print("🔍 Oracle Backend Test Suite")
    print("=" * 50)
    
    # Test OpenRouter first
    openrouter_ok = await test_openrouter_direct()
    
    # Test server
    server_ok = await test_server_health()
    
    if server_ok:
        # Test chat endpoint
        chat_ok = await test_chat_endpoint()
    else:
        print("\n⚠️  Server not running. Start it with:")
        print("   uv run python working_server.py")
        chat_ok = False
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"   OpenRouter: {'✅' if openrouter_ok else '❌'}")
    print(f"   Server Health: {'✅' if server_ok else '❌'}")
    print(f"   Chat Endpoint: {'✅' if chat_ok else '❌'}")
    
    if all([openrouter_ok, server_ok, chat_ok]):
        print("\n🎉 All tests passed! Your setup is working!")
    else:
        print("\n❌ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())