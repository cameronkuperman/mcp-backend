"""Async HTTP client with connection pooling for optimal performance"""
import httpx
import asyncio
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Global client instance for connection pooling
_http_client: Optional[httpx.AsyncClient] = None

async def get_http_client() -> httpx.AsyncClient:
    """Get or create the global HTTP client with connection pooling"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=240.0,  # Total timeout
                connect=10.0,   # Connection timeout
                read=60.0,      # Read timeout
                write=30.0      # Write timeout
            ),
            limits=httpx.Limits(
                max_keepalive_connections=50,
                max_connections=100,
                keepalive_expiry=30
            ),
            http2=True  # Enable HTTP/2 for better performance
        )
    return _http_client

async def close_http_client():
    """Close the global HTTP client (call on app shutdown)"""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None

async def make_async_post(url: str, headers: Dict[str, str], json_data: Dict[str, Any], timeout: int = 240) -> Dict[str, Any]:
    """Make an async POST request with connection reuse"""
    client = await get_http_client()
    
    try:
        response = await client.post(
            url,
            headers=headers,
            json=json_data,
            timeout=timeout
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"HTTP error {response.status_code}: {response.text[:500]}")
            raise Exception(f"HTTP error {response.status_code}: {response.text[:200]}")
            
    except httpx.TimeoutException as e:
        logger.error(f"Request timeout: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        raise

async def make_async_post_with_retry(
    url: str, 
    headers: Dict[str, str], 
    json_data: Dict[str, Any], 
    max_retries: int = 3,
    timeout: int = 240
) -> Dict[str, Any]:
    """Make async POST with exponential backoff retry logic"""
    for attempt in range(max_retries):
        try:
            return await make_async_post(url, headers, json_data, timeout)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            
            # Exponential backoff: 1s, 2s, 4s
            wait_time = 2 ** attempt
            logger.info(f"Retry {attempt + 1}/{max_retries} after {wait_time}s")
            await asyncio.sleep(wait_time)
    
    raise Exception(f"Failed after {max_retries} retries")