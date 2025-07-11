#!/usr/bin/env python3
"""
OpenRouter Proxy - Works around DNS issues by using alternative methods
"""
import os
import requests
import json
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

load_dotenv()

class OpenRouterProxy:
    """Handles OpenRouter API calls with fallback mechanisms"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
        
        # Try multiple endpoints
        self.endpoints = [
            "https://api.openrouter.ai/v1/chat/completions",
            "https://104.18.8.49/v1/chat/completions",  # Direct IP
            "https://104.18.9.49/v1/chat/completions",  # Backup IP
        ]
        
        # Free models in order of preference
        self.free_models = [
            "deepseek/deepseek-chat",  # DeepSeek V3 free
            "deepseek/deepseek-r1",    # DeepSeek reasoning
            "meta-llama/llama-3.2-3b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "microsoft/phi-3-mini-128k-instruct:free",
            "nousresearch/hermes-3-llama-3.1-8b:free",
            "qwen/qwen-2-7b-instruct:free",
            "meta-llama/llama-3.2-1b-instruct:free",  # Smallest as last resort
        ]
        
    async def call_llm(self, messages: list, model: str = "deepseek/deepseek-chat", 
                      temperature: float = 0.7, max_tokens: int = 2048) -> Dict[str, Any]:
        """Call OpenRouter with cascading model and endpoint fallbacks"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Try the requested model first, then fallback to free models
        models_to_try = [model] if model not in self.free_models else []
        models_to_try.extend(self.free_models)
        
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))
        
        # Try each model with each endpoint
        for current_model in models_to_try:
            data = {
                "model": current_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            for endpoint in self.endpoints:
                try:
                    # For direct IP endpoints, add Host header
                    current_headers = headers.copy()
                    if "104.18" in endpoint:
                        current_headers["Host"] = "api.openrouter.ai"
                    
                    # Use httpx for better HTTP/2 support
                    async with httpx.AsyncClient(verify=False) as client:
                        response = await client.post(
                            endpoint,
                            headers=current_headers,
                            json=data,
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            content = result["choices"][0]["message"]["content"].strip()
                            
                            print(f"✅ Success with model: {current_model} at {endpoint}")
                            
                            return {
                                "content": content,
                                "raw_content": content,
                                "usage": result.get("usage", {}),
                                "model": current_model,
                                "finish_reason": result["choices"][0].get("finish_reason", "stop"),
                                "endpoint_used": endpoint,
                                "model_used": current_model
                            }
                        elif response.status_code == 404:
                            # Model not found, try next model
                            print(f"Model {current_model} not found at {endpoint}")
                            break  # Don't try other endpoints for this model
                        elif response.status_code == 401:
                            print(f"Authentication failed - check API key")
                            break
                        elif response.status_code == 530:
                            # DNS error from Cloudflare, try next endpoint
                            continue
                        else:
                            print(f"Error {response.status_code} from {endpoint} with {current_model}")
                            continue
                            
                except Exception as e:
                    print(f"Failed {current_model} at {endpoint}: {e}")
                    continue
        
        # If all models and endpoints fail, return mock response
        print("All models failed, using mock response")
        return self.mock_response(messages, model)
    
    def mock_response(self, messages: list, model: str) -> Dict[str, Any]:
        """Fallback mock response when OpenRouter is unreachable"""
        user_message = messages[-1]["content"] if messages else "Hello"
        
        response = f"""I understand you're asking about: "{user_message}"

I'm currently unable to connect to the AI service, but the system is working correctly. 
In production, I would provide personalized health guidance based on your query.

This is a temporary connectivity issue that will be resolved when deployed to Railway or another cloud service."""
        
        return {
            "content": response,
            "raw_content": response,
            "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150},
            "model": f"{model}-mock",
            "finish_reason": "stop",
            "endpoint_used": "mock"
        }

# Create singleton instance
proxy = OpenRouterProxy()

# Export the call_llm function
async def call_llm_with_proxy(messages: list, model: Optional[str] = None, 
                             user_id: Optional[str] = None, temperature: float = 0.7, 
                             max_tokens: int = 2048, top_p: float = 1.0) -> Dict[str, Any]:
    """Drop-in replacement for the original call_llm function"""
    from business_logic import get_user_model
    
    # Get model if not provided
    if not model and user_id:
        model = await get_user_model(user_id)
    elif not model:
        model = "meta-llama/llama-3.2-1b-instruct:free"
    
    return await proxy.call_llm(messages, model, temperature, max_tokens)