#!/usr/bin/env python3
"""Direct test of OpenRouter with requests"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    print(f"API Key: {api_key[:20]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Say 'Hello, Oracle is working!'"}]
    }
    
    try:
        print("Making request to OpenRouter...")
        response = requests.post(
            "https://api.openrouter.ai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success! Response: {result['choices'][0]['message']['content']}")
        else:
            print(f"❌ Error: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_openrouter()