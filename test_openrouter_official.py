#!/usr/bin/env python3
"""Test OpenRouter with official documentation approach"""
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Exactly as shown in OpenRouter docs
response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
    },
    data=json.dumps({
        "model": "openai/gpt-4o-mini",  # Using a model that should work
        "messages": [
            {
                "role": "user",
                "content": "What is the meaning of life?"
            }
        ]
    })
)

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"✅ Success!")
    print(f"Response: {result['choices'][0]['message']['content']}")
else:
    print(f"❌ Error: {response.text}")