#!/usr/bin/env python3
"""
Working OpenRouter Proxy - Uses the official endpoint that we know works
"""
import os
import requests
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

async def call_llm_working(messages: list, model: str = "deepseek/deepseek-chat", 
                          temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
    """Call OpenRouter using the approach that works"""
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found")
    
    # Use the official endpoint that we verified works
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        },
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        
        return {
            "content": content,
            "raw_content": content,
            "usage": result.get("usage", {}),
            "model": model,
            "finish_reason": result["choices"][0].get("finish_reason", "stop")
        }
    else:
        # Return a helpful error message
        return {
            "content": f"Error {response.status_code}: {response.text}",
            "raw_content": f"Error {response.status_code}: {response.text}",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "model": f"{model}-error",
            "finish_reason": "error"
        }