"""Performance optimization utilities for multi-part selection and general system performance"""
import asyncio
from typing import List, Dict, Any, Optional, TypeVar, Callable
from functools import lru_cache, wraps
import hashlib
import json
import time
from datetime import datetime, timedelta
import redis
from contextlib import asynccontextmanager

# Type definitions
T = TypeVar('T')
CacheKey = str

class PerformanceOptimizer:
    """FAANG-level performance optimizations for the health scan system"""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize performance optimizer with optional Redis connection"""
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            except Exception as e:
                print(f"Redis connection failed, falling back to in-memory cache: {e}")
    
    # === Caching Layer ===
    
    def cache_key_generator(self, prefix: str, **kwargs) -> CacheKey:
        """Generate consistent cache keys from parameters"""
        # Sort kwargs for consistent key generation
        sorted_params = json.dumps(kwargs, sort_keys=True)
        hash_digest = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_digest}"
    
    def cache_multi_part_analysis(self, ttl_seconds: int = 900):
        """Decorator to cache multi-part analysis results (15 min default TTL)"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(body_parts: List[str], form_data: Dict, user_id: Optional[str] = None, **kwargs):
                # Generate cache key
                cache_key = self.cache_key_generator(
                    "multi_part_analysis",
                    body_parts=sorted(body_parts),  # Sort for consistency
                    symptoms=form_data.get("symptoms", ""),
                    pain_level=form_data.get("painLevel", 0)
                )
                
                # Try Redis cache first
                if self.redis_client:
                    try:
                        cached = self.redis_client.get(cache_key)
                        if cached:
                            return json.loads(cached)
                    except Exception:
                        pass  # Fall through to compute
                
                # Compute result
                result = await func(body_parts, form_data, user_id, **kwargs)
                
                # Store in cache
                if self.redis_client and result:
                    try:
                        self.redis_client.setex(
                            cache_key,
                            ttl_seconds,
                            json.dumps(result)
                        )
                    except Exception:
                        pass  # Cache write failure is non-critical
                
                return result
            
            return wrapper
        return decorator
    
    # === Batch Processing ===
    
    async def batch_analyze_parts(
        self,
        parts: List[str],
        analyze_func: Callable,
        max_parallel: int = 3
    ) -> List[Any]:
        """
        Batch analyze multiple body parts with controlled parallelism
        Prevents overwhelming the LLM API with too many concurrent requests
        """
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def analyze_with_limit(part: str) -> Any:
            async with semaphore:
                return await analyze_func(part)
        
        tasks = [analyze_with_limit(part) for part in parts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return valid results
        return [r for r in results if not isinstance(r, Exception)]
    
    # === Connection Pooling ===
    
    class DatabaseConnectionPool:
        """Database connection pool for efficient query execution"""
        
        def __init__(self, dsn: str, min_size: int = 5, max_size: int = 20):
            self.dsn = dsn
            self.min_size = min_size
            self.max_size = max_size
            self._pool = None
        
        async def initialize(self):
            """Initialize the connection pool"""
            try:
                import asyncpg
                self._pool = await asyncpg.create_pool(
                    self.dsn,
                    min_size=self.min_size,
                    max_size=self.max_size,
                    max_inactive_connection_lifetime=300
                )
            except ImportError:
                print("asyncpg not installed, connection pooling disabled")
            except Exception as e:
                print(f"Failed to create connection pool: {e}")
        
        @asynccontextmanager
        async def acquire(self):
            """Acquire a connection from the pool"""
            if not self._pool:
                yield None
                return
            
            async with self._pool.acquire() as conn:
                yield conn
        
        async def close(self):
            """Close the connection pool"""
            if self._pool:
                await self._pool.close()
    
    # === Query Optimization ===
    
    @staticmethod
    def build_batch_query(table: str, user_ids: List[str], fields: List[str]) -> str:
        """
        Build optimized batch query to prevent N+1 queries
        
        Example:
            SELECT * FROM medical_data 
            WHERE user_id = ANY($1::text[])
            AND created_at > NOW() - INTERVAL '30 days'
        """
        field_list = ", ".join(fields) if fields else "*"
        return f"""
            SELECT {field_list}
            FROM {table}
            WHERE user_id = ANY($1::text[])
            ORDER BY created_at DESC
        """
    
    @lru_cache(maxsize=128)
    def get_related_body_parts(self, parts: tuple) -> Dict[str, List[str]]:
        """
        Cached computation of related body parts for a given selection
        Uses tuple for hashability in lru_cache
        """
        BODY_SYSTEMS = {
            "cardiac": ["chest", "left arm", "left shoulder", "jaw", "neck"],
            "neurological": ["head", "eyes", "face", "neck", "spine"],
            "digestive": ["abdomen", "stomach", "chest", "throat"],
            "musculoskeletal": ["back", "neck", "shoulders", "hips", "knees"],
            "respiratory": ["chest", "throat", "nose", "lungs"],
            "circulatory": ["legs", "feet", "hands", "arms"]
        }
        
        parts_list = list(parts)
        related = {"primary": parts_list, "suggested": [], "system": None}
        
        # Find which systems these parts belong to
        for system, system_parts in BODY_SYSTEMS.items():
            overlap = set(p.lower() for p in parts_list) & set(system_parts)
            if len(overlap) >= 2:
                related["system"] = system
                related["suggested"] = [
                    p for p in system_parts 
                    if p not in [pt.lower() for pt in parts_list]
                ][:3]  # Limit suggestions to 3
                break
        
        return related
    
    # === Request Deduplication ===
    
    class RequestDeduplicator:
        """Prevent duplicate concurrent requests for same data"""
        
        def __init__(self):
            self._pending: Dict[str, asyncio.Future] = {}
        
        async def deduplicate(
            self,
            key: str,
            compute_func: Callable,
            *args,
            **kwargs
        ) -> Any:
            """
            Ensure only one request for the same key is in flight at a time
            Subsequent requests wait for the first to complete
            """
            if key in self._pending:
                # Wait for existing request
                return await self._pending[key]
            
            # Create new future for this request
            future = asyncio.get_event_loop().create_future()
            self._pending[key] = future
            
            try:
                # Compute result
                result = await compute_func(*args, **kwargs)
                future.set_result(result)
                return result
            except Exception as e:
                future.set_exception(e)
                raise
            finally:
                # Clean up
                del self._pending[key]
    
    # === Performance Monitoring ===
    
    class PerformanceMonitor:
        """Monitor and log performance metrics"""
        
        def __init__(self):
            self.metrics: Dict[str, List[float]] = {}
        
        @asynccontextmanager
        async def measure(self, operation: str):
            """Context manager to measure operation duration"""
            start = time.perf_counter()
            try:
                yield
            finally:
                duration = time.perf_counter() - start
                if operation not in self.metrics:
                    self.metrics[operation] = []
                self.metrics[operation].append(duration)
                
                # Log slow operations
                if duration > 1.0:
                    print(f"SLOW OPERATION: {operation} took {duration:.2f}s")
        
        def get_stats(self, operation: str) -> Dict[str, float]:
            """Get performance statistics for an operation"""
            if operation not in self.metrics or not self.metrics[operation]:
                return {}
            
            times = self.metrics[operation]
            return {
                "count": len(times),
                "mean": sum(times) / len(times),
                "min": min(times),
                "max": max(times),
                "p95": sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times)
            }

# === Utility Functions ===

def optimize_prompt_for_multi_parts(parts: List[str], max_tokens_per_part: int = 200) -> str:
    """
    Optimize prompt length when dealing with multiple body parts
    Ensures we don't exceed token limits
    """
    if len(parts) <= 2:
        return ", ".join(parts)
    elif len(parts) <= 4:
        return f"{', '.join(parts[:2])} and {len(parts)-2} other area(s)"
    else:
        return f"multiple areas ({len(parts)} total) including {', '.join(parts[:2])}"

async def parallel_fetch_medical_data(
    user_ids: List[str],
    data_types: List[str],
    supabase_client: Any
) -> Dict[str, Dict[str, Any]]:
    """
    Fetch multiple types of medical data in parallel
    Prevents sequential queries that slow down response time
    """
    async def fetch_data(user_id: str, data_type: str):
        try:
            response = await supabase_client.table(data_type).select("*").eq("user_id", user_id).execute()
            return (user_id, data_type, response.data)
        except Exception as e:
            print(f"Failed to fetch {data_type} for user {user_id}: {e}")
            return (user_id, data_type, None)
    
    # Create all fetch tasks
    tasks = [
        fetch_data(user_id, data_type)
        for user_id in user_ids
        for data_type in data_types
    ]
    
    # Execute in parallel with limited concurrency
    semaphore = asyncio.Semaphore(10)
    async def fetch_with_limit(task_coro):
        async with semaphore:
            return await task_coro
    
    results = await asyncio.gather(*[fetch_with_limit(task) for task in tasks])
    
    # Organize results by user_id
    organized: Dict[str, Dict[str, Any]] = {}
    for user_id, data_type, data in results:
        if user_id not in organized:
            organized[user_id] = {}
        organized[user_id][data_type] = data
    
    return organized

# === Circuit Breaker for External Services ===

class CircuitBreaker:
    """Prevent cascading failures when external services are down"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        
        # Check if circuit should be reset
        if self.state == "open":
            if (datetime.now() - self.last_failure_time).seconds > self.recovery_timeout:
                self.state = "half-open"
                self.failure_count = 0
            else:
                raise Exception(f"Circuit breaker is open for {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == "half-open":
                self.state = "closed"
            self.failure_count = 0
            
            return result
            
        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
                print(f"Circuit breaker opened for {func.__name__} after {self.failure_count} failures")
            
            raise e

# === Export singleton instance ===
performance_optimizer = PerformanceOptimizer()