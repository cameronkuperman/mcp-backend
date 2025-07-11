#!/usr/bin/env python3
"""Test OpenRouter with free DeepSeek model"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Test with DeepSeek free model
response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
    },
    data=json.dumps({
        "model": "deepseek/deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": "Hello Oracle, I have a headache. What should I do?"
            }
        ]
    })
)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✅ Success with DeepSeek!")
    print(f"Response: {result['choices'][0]['message']['content'][:200]}...")
else:
    print(f"❌ Error: {response.text}")