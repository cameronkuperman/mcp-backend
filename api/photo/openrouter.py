"""OpenRouter API integration for photo analysis"""
import asyncio
import httpx
from typing import Dict, List
from fastapi import HTTPException
from .core import OPENROUTER_API_KEY

async def call_openrouter(model: str, messages: List[Dict], max_tokens: int = 1000, temperature: float = 0.3) -> Dict:
    """Make API call to OpenRouter"""
    if not OPENROUTER_API_KEY:
        raise HTTPException(status_code=500, detail="OpenRouter API key not configured")
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {OPENROUTER_API_KEY}',
                'Content-Type': 'application/json',
                'X-Title': 'Health Oracle Photo Analysis'
            },
            json={
                'model': model,
                'messages': messages,
                'max_tokens': max_tokens,
                'temperature': temperature
            },
            timeout=60.0
        )
        
        if response.status_code != 200:
            detail = f"OpenRouter API error: {response.status_code}"
            if response.status_code == 429:
                detail = "Rate limit exceeded. Please try again in a moment."
            elif response.status_code == 401:
                detail = "Invalid API key"
            elif response.status_code == 400:
                detail = f"Bad request: {response.text}"
            
            print(f"OpenRouter error: {response.status_code} - {response.text}")
            raise HTTPException(status_code=response.status_code, detail=detail)
        
        return response.json()

async def call_openrouter_with_retry(model: str, messages: List[Dict], max_tokens: int = 1000, 
                                   temperature: float = 0.3, max_retries: int = 3) -> Dict:
    """Make API call to OpenRouter with retry logic"""
    last_error = None
    
    for attempt in range(max_retries):
        try:
            return await call_openrouter(model, messages, max_tokens, temperature)
        except HTTPException as e:
            last_error = e
            # Check if it's a rate limit error
            if e.status_code == 429:
                # For rate limit errors, wait longer
                wait_time = min(10 * (attempt + 1), 30)  # 10s, 20s, 30s max
                print(f"Rate limit hit (429), waiting {wait_time}s before retry...")
                # Try a different model on rate limit
                if attempt == 0:
                    if model == 'openai/gpt-5':
                        print("Switching to google/gemini-2.5-pro due to rate limit")
                        model = 'google/gemini-2.5-pro'
                    elif model == 'google/gemini-2.5-pro':
                        print("Switching to gemini-2.0-flash-exp:free due to rate limit")
                        model = 'google/gemini-2.0-flash-exp:free'
            else:
                # Regular exponential backoff for other errors
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(wait_time)
            else:
                print(f"All {max_retries} attempts failed")
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff for non-HTTP errors
                wait_time = 2 ** attempt
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                await asyncio.sleep(wait_time)
            else:
                print(f"All {max_retries} attempts failed")
    
    raise last_error