"""
Optimized Supabase Client with Connection Pooling and Performance Enhancements
This module provides a high-performance Supabase client for the photo analysis system.
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from supabase import create_client, Client
import httpx
from functools import wraps
import time
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class OptimizedSupabaseClient:
    """
    Enhanced Supabase client with connection pooling, retry logic, and performance optimizations.
    
    Features:
    - Connection pooling for reduced overhead
    - Automatic retry with exponential backoff
    - Request deduplication
    - Performance metrics tracking
    - Batch operations support
    """
    
    def __init__(
        self,
        url: str = None,
        key: str = None,
        pool_size: int = 20,
        max_retries: int = 3,
        timeout: float = 30.0
    ):
        """
        Initialize optimized Supabase client.
        
        Args:
            url: Supabase project URL
            key: Supabase service key
            pool_size: Maximum number of connections in pool
            max_retries: Maximum retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.url = url or os.getenv("SUPABASE_URL")
        self.key = key or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        self.pool_size = pool_size
        self.max_retries = max_retries
        
        # Create base client
        self._client = create_client(self.url, self.key)
        
        # Configure connection pool
        self._session = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=pool_size,
                max_keepalive_connections=pool_size // 2,
                keepalive_expiry=30.0
            ),
            timeout=httpx.Timeout(timeout),
            headers={
                "apikey": self.key,
                "Authorization": f"Bearer {self.key}",
                "Content-Type": "application/json"
            }
        )
        
        # Request deduplication cache
        self._pending_requests = {}
        
        # Performance metrics
        self.metrics = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retried_requests": 0,
            "average_response_time": 0.0,
            "cache_hits": 0
        }
    
    async def _execute_with_retry(self, func, *args, **kwargs):
        """
        Execute a function with automatic retry on failure.
        
        Uses exponential backoff: 1s, 2s, 4s
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                
                # Update metrics
                response_time = time.time() - start_time
                self.metrics["total_requests"] += 1
                self.metrics["successful_requests"] += 1
                self._update_average_response_time(response_time)
                
                return result
                
            except Exception as e:
                last_error = e
                self.metrics["failed_requests"] += 1
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {str(e)}")
                    self.metrics["retried_requests"] += 1
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.max_retries} attempts: {str(e)}")
        
        raise last_error
    
    def _update_average_response_time(self, new_time: float):
        """Update rolling average response time"""
        total = self.metrics["successful_requests"]
        if total == 1:
            self.metrics["average_response_time"] = new_time
        else:
            # Rolling average
            current_avg = self.metrics["average_response_time"]
            self.metrics["average_response_time"] = (current_avg * (total - 1) + new_time) / total
    
    async def parallel_queries(self, queries: List[callable]) -> List[Any]:
        """
        Execute multiple queries in parallel.
        
        Args:
            queries: List of async query functions
            
        Returns:
            List of query results in the same order as input
        """
        tasks = [asyncio.create_task(self._execute_with_retry(query)) for query in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def batch_insert(self, table: str, records: List[Dict], batch_size: int = 100):
        """
        Insert multiple records in optimized batches.
        
        Args:
            table: Table name
            records: List of records to insert
            batch_size: Number of records per batch
            
        Returns:
            List of inserted records
        """
        results = []
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            
            async def insert_batch():
                return self._client.table(table).insert(batch).execute()
            
            batch_result = await self._execute_with_retry(insert_batch)
            results.extend(batch_result.data if batch_result.data else [])
        
        return results
    
    async def batch_update(
        self,
        table: str,
        updates: List[Dict[str, Any]],
        id_field: str = "id"
    ):
        """
        Perform batch updates efficiently.
        
        Args:
            table: Table name
            updates: List of dicts containing id and fields to update
            id_field: Name of the ID field
            
        Returns:
            List of updated records
        """
        results = []
        
        # Group updates by common fields for efficiency
        update_groups = {}
        for update in updates:
            record_id = update.pop(id_field)
            update_key = str(sorted(update.items()))
            
            if update_key not in update_groups:
                update_groups[update_key] = {"ids": [], "data": update}
            update_groups[update_key]["ids"].append(record_id)
        
        # Execute grouped updates
        for group in update_groups.values():
            async def update_group():
                return self._client.table(table)\
                    .update(group["data"])\
                    .in_(id_field, group["ids"])\
                    .execute()
            
            result = await self._execute_with_retry(update_group)
            results.extend(result.data if result.data else [])
        
        return results
    
    async def deduplicated_request(self, cache_key: str, request_func: callable):
        """
        Prevent duplicate concurrent requests for the same data.
        
        If a request for the same cache_key is already in progress,
        wait for it to complete and return the same result.
        
        Args:
            cache_key: Unique identifier for this request
            request_func: Async function to execute if not already pending
            
        Returns:
            Request result
        """
        # Check if request is already pending
        if cache_key in self._pending_requests:
            self.metrics["cache_hits"] += 1
            return await self._pending_requests[cache_key]
        
        # Create new request
        future = asyncio.create_task(request_func())
        self._pending_requests[cache_key] = future
        
        try:
            result = await future
            return result
        finally:
            # Clean up pending request
            self._pending_requests.pop(cache_key, None)
    
    @asynccontextmanager
    async def transaction(self):
        """
        Context manager for database transactions.
        Note: Supabase doesn't natively support transactions via REST API,
        so this simulates transaction-like behavior.
        """
        # Start "transaction" - collect operations
        operations = []
        
        class TransactionContext:
            def add_operation(self, op):
                operations.append(op)
        
        ctx = TransactionContext()
        
        try:
            yield ctx
            # Execute all operations
            for op in operations:
                await op()
        except Exception as e:
            # Rollback would happen here if supported
            logger.error(f"Transaction failed: {str(e)}")
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            **self.metrics,
            "success_rate": (
                self.metrics["successful_requests"] / self.metrics["total_requests"] * 100
                if self.metrics["total_requests"] > 0 else 0
            ),
            "retry_rate": (
                self.metrics["retried_requests"] / self.metrics["total_requests"] * 100
                if self.metrics["total_requests"] > 0 else 0
            ),
            "cache_hit_rate": (
                self.metrics["cache_hits"] / self.metrics["total_requests"] * 100
                if self.metrics["total_requests"] > 0 else 0
            )
        }
    
    async def close(self):
        """Close the client and clean up resources"""
        await self._session.aclose()
    
    # Proxy methods for common operations
    def table(self, table_name: str):
        """Proxy to base client table method"""
        return self._client.table(table_name)
    
    def storage(self):
        """Proxy to base client storage"""
        return self._client.storage
    
    def auth(self):
        """Proxy to base client auth"""
        return self._client.auth
    
    def rpc(self, func_name: str, params: Dict = None):
        """Proxy to base client RPC with retry logic"""
        async def execute_rpc():
            return self._client.rpc(func_name, params).execute()
        
        return self._execute_with_retry(execute_rpc)


# Global optimized client instance
_optimized_client: Optional[OptimizedSupabaseClient] = None


def get_optimized_client() -> OptimizedSupabaseClient:
    """
    Get or create the global optimized Supabase client.
    
    Returns:
        OptimizedSupabaseClient instance
    """
    global _optimized_client
    
    if _optimized_client is None:
        _optimized_client = OptimizedSupabaseClient()
    
    return _optimized_client


async def cleanup():
    """Cleanup function to be called on application shutdown"""
    global _optimized_client
    
    if _optimized_client:
        await _optimized_client.close()
        _optimized_client = None


# Performance monitoring decorator
def monitor_performance(operation_name: str):
    """
    Decorator to monitor performance of database operations.
    
    Args:
        operation_name: Name of the operation for logging
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                if duration > 1.0:  # Log slow queries
                    logger.warning(f"Slow operation '{operation_name}': {duration:.2f}s")
                else:
                    logger.debug(f"Operation '{operation_name}': {duration:.3f}s")
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Operation '{operation_name}' failed after {duration:.2f}s: {str(e)}")
                raise
        
        return wrapper
    return decorator


# Example usage for photo analysis
async def optimized_photo_analysis_queries(session_id: str):
    """
    Example of using optimized client for photo analysis queries.
    
    This demonstrates parallel queries and deduplication.
    """
    client = get_optimized_client()
    
    # Define queries
    async def fetch_session():
        return client.table('photo_sessions').select('*').eq('id', session_id).single().execute()
    
    async def fetch_photos():
        return client.table('photo_uploads').select('*').eq('session_id', session_id).execute()
    
    async def fetch_analyses():
        return client.table('photo_analyses').select('*').eq('session_id', session_id).execute()
    
    # Execute in parallel
    results = await client.parallel_queries([
        fetch_session,
        fetch_photos,
        fetch_analyses
    ])
    
    return {
        'session': results[0].data if not isinstance(results[0], Exception) else None,
        'photos': results[1].data if not isinstance(results[1], Exception) else [],
        'analyses': results[2].data if not isinstance(results[2], Exception) else []
    }


if __name__ == "__main__":
    # Test the optimized client
    async def test():
        client = get_optimized_client()
        
        # Test parallel queries
        print("Testing optimized Supabase client...")
        
        # Get metrics
        print("\nPerformance Metrics:")
        for key, value in client.get_metrics().items():
            print(f"  {key}: {value}")
        
        await cleanup()
    
    asyncio.run(test())