"""
Production-Ready Retry System with Circuit Breaker and Dead Letter Queue
Implements comprehensive error handling for background jobs
"""

import asyncio
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
import httpx
import json
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib

logger = logging.getLogger(__name__)

# Retryable HTTP status codes
RETRYABLE_HTTP_CODES: Set[int] = {
    408,  # Request Timeout
    425,  # Too Early
    429,  # Too Many Requests
    500,  # Internal Server Error
    502,  # Bad Gateway
    503,  # Service Unavailable
    504,  # Gateway Timeout
    507,  # Insufficient Storage
    509,  # Bandwidth Limit Exceeded
}

# Permanent failure HTTP codes (don't retry)
PERMANENT_FAILURE_CODES: Set[int] = {
    400,  # Bad Request
    401,  # Unauthorized
    403,  # Forbidden
    404,  # Not Found
    405,  # Method Not Allowed
    409,  # Conflict
    410,  # Gone
    422,  # Unprocessable Entity
}

# Retryable exception types
RETRYABLE_EXCEPTIONS: Tuple[type, ...] = (
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.NetworkError,
    httpx.PoolTimeout,
    httpx.RemoteProtocolError,
    asyncio.TimeoutError,
    ConnectionError,
    ConnectionResetError,
    json.JSONDecodeError,
)

# Non-retryable error patterns in exception messages
NON_RETRYABLE_PATTERNS = [
    "invalid api key",
    "api key not found",
    "quota exceeded",
    "billing",
    "payment required",
    "subscription expired",
    "account suspended",
    "invalid credentials",
    "authentication failed",
    "out of memory",
    "disk full",
]

class RetryStrategy(Enum):
    """Different retry strategies for different error types"""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIBONACCI = "fibonacci"
    AGGRESSIVE = "aggressive"  # For critical operations

@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 5
    initial_delay: float = 1.0
    max_delay: float = 300.0  # 5 minutes
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: Tuple[float, float] = (0.0, 1.0)
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    
@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 2  # Successes before closing
    timeout: timedelta = timedelta(minutes=5)  # Time before half-open
    half_open_requests: int = 3  # Requests to try in half-open state

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered

@dataclass
class CircuitBreaker:
    """Circuit breaker implementation"""
    config: CircuitBreakerConfig
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    half_open_attempts: int = 0
    
    def record_success(self):
        """Record a successful operation"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.reset_counts()
                logger.info("Circuit breaker closed after recovery")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed operation"""
        self.last_failure_time = datetime.now(timezone.utc)
        
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN
                logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
        elif self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self.reset_counts()
            logger.warning("Circuit breaker reopened after half-open failure")
    
    def should_attempt(self) -> bool:
        """Check if we should attempt the operation"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            if self.last_failure_time:
                time_since_failure = datetime.now(timezone.utc) - self.last_failure_time
                if time_since_failure > self.config.timeout:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_attempts = 0
                    logger.info("Circuit breaker entering half-open state")
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            if self.half_open_attempts < self.config.half_open_requests:
                self.half_open_attempts += 1
                return True
            return False
        
        return False
    
    def reset_counts(self):
        """Reset internal counters"""
        self.failure_count = 0
        self.success_count = 0
        self.half_open_attempts = 0

class ErrorClassifier:
    """Classify errors to determine retry behavior"""
    
    @staticmethod
    def should_retry(error: Exception) -> Tuple[bool, str]:
        """
        Determine if an error should be retried
        
        Returns:
            Tuple of (should_retry, reason)
        """
        error_str = str(error).lower()
        
        # Check for non-retryable patterns
        for pattern in NON_RETRYABLE_PATTERNS:
            if pattern in error_str:
                return False, f"Non-retryable pattern: {pattern}"
        
        # Check HTTP errors
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            
            if status_code in PERMANENT_FAILURE_CODES:
                return False, f"Permanent failure code: {status_code}"
            
            if status_code in RETRYABLE_HTTP_CODES:
                return True, f"Retryable HTTP code: {status_code}"
            
            # Default for unknown codes
            if 400 <= status_code < 500:
                return False, f"Client error: {status_code}"
            else:
                return True, f"Server error: {status_code}"
        
        # Check exception types
        if isinstance(error, RETRYABLE_EXCEPTIONS):
            return True, f"Retryable exception: {type(error).__name__}"
        
        # Check for specific error messages that indicate retry
        retry_patterns = [
            "timeout", "timed out",
            "connection reset", "connection refused",
            "temporary", "unavailable",
            "rate limit", "too many requests",
            "gateway", "proxy",
            "dns", "resolve",
        ]
        
        for pattern in retry_patterns:
            if pattern in error_str:
                return True, f"Retryable pattern: {pattern}"
        
        # Default to retry for unknown errors (conservative approach)
        return True, "Unknown error - defaulting to retry"
    
    @staticmethod
    def get_retry_strategy(error: Exception) -> RetryStrategy:
        """Determine the best retry strategy for an error"""
        if isinstance(error, httpx.HTTPStatusError):
            if error.response.status_code == 429:
                return RetryStrategy.AGGRESSIVE  # Rate limiting needs aggressive backoff
            elif error.response.status_code >= 500:
                return RetryStrategy.EXPONENTIAL
        
        if isinstance(error, (httpx.TimeoutException, asyncio.TimeoutError)):
            return RetryStrategy.LINEAR  # Timeouts might resolve quickly
        
        return RetryStrategy.EXPONENTIAL  # Default

class RetryManager:
    """Manages retry logic with circuit breaker and dead letter queue"""
    
    def __init__(self, 
                 config: Optional[RetryConfig] = None,
                 circuit_config: Optional[CircuitBreakerConfig] = None):
        self.config = config or RetryConfig()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.circuit_config = circuit_config or CircuitBreakerConfig()
        self.dead_letter_queue: List[Dict[str, Any]] = []
        self.retry_metrics = defaultdict(lambda: {"attempts": 0, "successes": 0, "failures": 0})
    
    def get_circuit_breaker(self, key: str) -> CircuitBreaker:
        """Get or create circuit breaker for a key"""
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = CircuitBreaker(self.circuit_config)
        return self.circuit_breakers[key]
    
    def calculate_delay(self, attempt: int, strategy: RetryStrategy) -> float:
        """Calculate delay for next retry attempt"""
        if strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.exponential_base ** attempt)
        elif strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * attempt
        elif strategy == RetryStrategy.FIBONACCI:
            # Fibonacci sequence for delay
            if attempt <= 1:
                delay = self.config.initial_delay
            else:
                a, b = self.config.initial_delay, self.config.initial_delay
                for _ in range(attempt - 1):
                    a, b = b, a + b
                delay = b
        elif strategy == RetryStrategy.AGGRESSIVE:
            # More aggressive backoff for rate limiting
            delay = self.config.initial_delay * (3 ** attempt)
        else:
            delay = self.config.initial_delay
        
        # Apply max delay cap
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if configured
        if self.config.jitter:
            jitter_min, jitter_max = self.config.jitter_range
            jitter = random.uniform(jitter_min * delay, jitter_max * delay)
            delay += jitter
        
        return delay
    
    async def execute_with_retry(self,
                                 func: callable,
                                 func_args: tuple = (),
                                 func_kwargs: dict = None,
                                 operation_key: str = None) -> Dict[str, Any]:
        """
        Execute a function with comprehensive retry logic
        
        Args:
            func: Async function to execute
            func_args: Positional arguments for func
            func_kwargs: Keyword arguments for func
            operation_key: Unique key for this operation (for circuit breaker)
        
        Returns:
            Dict with status, result, and metadata
        """
        func_kwargs = func_kwargs or {}
        operation_key = operation_key or self._generate_operation_key(func, func_args)
        circuit_breaker = self.get_circuit_breaker(operation_key)
        
        attempt = 0
        last_error = None
        retry_history = []
        
        while attempt < self.config.max_attempts:
            # Check circuit breaker
            if not circuit_breaker.should_attempt():
                logger.warning(f"Circuit breaker OPEN for {operation_key}, skipping attempt")
                return {
                    "status": "circuit_breaker_open",
                    "error": "Service unavailable due to repeated failures",
                    "attempts": attempt,
                    "retry_history": retry_history
                }
            
            attempt += 1
            start_time = datetime.now(timezone.utc)
            
            try:
                # Execute the function
                result = await func(*func_args, **func_kwargs)
                
                # Record success
                circuit_breaker.record_success()
                self.retry_metrics[operation_key]["successes"] += 1
                
                return {
                    "status": "success",
                    "result": result,
                    "attempts": attempt,
                    "retry_history": retry_history
                }
                
            except Exception as error:
                last_error = error
                duration = (datetime.now(timezone.utc) - start_time).total_seconds()
                
                # Classify the error
                should_retry, reason = ErrorClassifier.should_retry(error)
                
                retry_history.append({
                    "attempt": attempt,
                    "error": str(error),
                    "error_type": type(error).__name__,
                    "duration": duration,
                    "should_retry": should_retry,
                    "reason": reason,
                    "timestamp": start_time.isoformat()
                })
                
                logger.warning(f"Attempt {attempt} failed for {operation_key}: {error}")
                
                if not should_retry:
                    logger.error(f"Non-retryable error for {operation_key}: {reason}")
                    circuit_breaker.record_failure()
                    self.retry_metrics[operation_key]["failures"] += 1
                    
                    # Add to dead letter queue
                    self.add_to_dead_letter_queue(operation_key, error, retry_history)
                    
                    return {
                        "status": "permanent_failure",
                        "error": str(error),
                        "reason": reason,
                        "attempts": attempt,
                        "retry_history": retry_history
                    }
                
                # Check if we have more attempts
                if attempt >= self.config.max_attempts:
                    logger.error(f"Max retries exceeded for {operation_key}")
                    circuit_breaker.record_failure()
                    self.retry_metrics[operation_key]["failures"] += 1
                    
                    # Add to dead letter queue
                    self.add_to_dead_letter_queue(operation_key, error, retry_history)
                    
                    return {
                        "status": "max_retries_exceeded",
                        "error": str(error),
                        "attempts": attempt,
                        "retry_history": retry_history
                    }
                
                # Calculate delay for next attempt
                strategy = ErrorClassifier.get_retry_strategy(error)
                delay = self.calculate_delay(attempt - 1, strategy)
                
                logger.info(f"Retrying {operation_key} in {delay:.2f}s (attempt {attempt}/{self.config.max_attempts})")
                await asyncio.sleep(delay)
                
                self.retry_metrics[operation_key]["attempts"] += 1
        
        # Should not reach here, but just in case
        return {
            "status": "unknown_failure",
            "error": str(last_error) if last_error else "Unknown error",
            "attempts": attempt,
            "retry_history": retry_history
        }
    
    def add_to_dead_letter_queue(self, operation_key: str, error: Exception, retry_history: List[Dict]):
        """Add failed operation to dead letter queue for manual review"""
        dlq_entry = {
            "operation_key": operation_key,
            "error": str(error),
            "error_type": type(error).__name__,
            "retry_history": retry_history,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "id": hashlib.sha256(f"{operation_key}{datetime.now()}".encode()).hexdigest()[:16]
        }
        
        self.dead_letter_queue.append(dlq_entry)
        logger.error(f"Added to dead letter queue: {operation_key}")
        
        # Trigger alert if queue is getting large
        if len(self.dead_letter_queue) > 100:
            logger.critical(f"Dead letter queue size critical: {len(self.dead_letter_queue)} items")
    
    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get current dead letter queue"""
        return self.dead_letter_queue.copy()
    
    def clear_dead_letter_queue(self, ids: Optional[List[str]] = None):
        """Clear dead letter queue or specific items"""
        if ids:
            self.dead_letter_queue = [
                item for item in self.dead_letter_queue 
                if item["id"] not in ids
            ]
        else:
            self.dead_letter_queue.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry metrics for monitoring"""
        total_attempts = sum(m["attempts"] for m in self.retry_metrics.values())
        total_successes = sum(m["successes"] for m in self.retry_metrics.values())
        total_failures = sum(m["failures"] for m in self.retry_metrics.values())
        
        return {
            "total_operations": len(self.retry_metrics),
            "total_attempts": total_attempts,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": (total_successes / (total_successes + total_failures) * 100) if (total_successes + total_failures) > 0 else 0,
            "circuit_breakers": {
                key: {
                    "state": cb.state.value,
                    "failure_count": cb.failure_count,
                    "success_count": cb.success_count
                }
                for key, cb in self.circuit_breakers.items()
            },
            "dead_letter_queue_size": len(self.dead_letter_queue)
        }
    
    def _generate_operation_key(self, func: callable, args: tuple) -> str:
        """Generate a unique key for an operation"""
        func_name = func.__name__ if hasattr(func, '__name__') else str(func)
        args_str = str(args)[:100]  # Limit length
        return f"{func_name}_{hashlib.md5(args_str.encode()).hexdigest()[:8]}"

# Example usage with the background jobs
class EnhancedBatchProcessor:
    """Enhanced batch processor with production-ready retry logic"""
    
    def __init__(self, batch_size: int = 10, delay_between_batches: float = 5.0):
        self.batch_size = batch_size
        self.delay_between_batches = delay_between_batches
        self.retry_manager = RetryManager(
            config=RetryConfig(
                max_attempts=5,
                initial_delay=2.0,
                max_delay=300.0,
                jitter=True,
                strategy=RetryStrategy.EXPONENTIAL
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=timedelta(minutes=10)
            )
        )
        self.http_client = httpx.AsyncClient(timeout=300.0)
    
    async def process_single_user_with_retry(self, user_id: str, process_func: callable, job_name: str) -> Dict:
        """Process a single user with comprehensive retry logic"""
        
        async def wrapped_process():
            """Wrapper to handle the actual processing"""
            return await process_func(user_id)
        
        result = await self.retry_manager.execute_with_retry(
            func=wrapped_process,
            operation_key=f"{job_name}_{user_id}"
        )
        
        return {
            "user_id": user_id,
            "job_name": job_name,
            **result
        }
    
    async def process_users(self, users: List[Dict], process_func: callable, job_name: str) -> Dict:
        """Process users in batches with enhanced retry logic"""
        total_users = len(users)
        results = []
        
        logger.info(f"[{job_name}] Starting enhanced batch processing for {total_users} users")
        
        # Process in batches
        for i in range(0, total_users, self.batch_size):
            batch = users[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (total_users + self.batch_size - 1) // self.batch_size
            
            logger.info(f"[{job_name}] Processing batch {batch_num}/{total_batches}")
            
            # Process batch concurrently
            tasks = []
            for user in batch:
                user_id = user.get('user_id') or user.get('id')
                task = asyncio.create_task(
                    self.process_single_user_with_retry(user_id, process_func, job_name)
                )
                tasks.append(task)
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Unexpected error in batch processing: {result}")
                    results.append({
                        "status": "unexpected_error",
                        "error": str(result)
                    })
                else:
                    results.append(result)
            
            # Delay between batches
            if i + self.batch_size < total_users:
                await asyncio.sleep(self.delay_between_batches)
        
        # Calculate summary statistics
        successful = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") in ["permanent_failure", "max_retries_exceeded"])
        circuit_broken = sum(1 for r in results if r.get("status") == "circuit_breaker_open")
        
        # Get metrics
        metrics = self.retry_manager.get_metrics()
        dlq = self.retry_manager.get_dead_letter_queue()
        
        summary = {
            "status": "completed",
            "total_users": total_users,
            "successful": successful,
            "failed": failed,
            "circuit_breaker_rejections": circuit_broken,
            "success_rate": (successful / total_users * 100) if total_users > 0 else 0,
            "metrics": metrics,
            "dead_letter_queue": dlq[:10] if dlq else [],  # First 10 items
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Alert if failure rate is high
        if summary["success_rate"] < 80:
            logger.critical(f"[{job_name}] High failure rate: {100 - summary['success_rate']:.2f}%")
        
        return summary
    
    async def close(self):
        """Clean up resources"""
        await self.http_client.aclose()

# Testing utilities
async def test_retry_system():
    """Test the retry system with various failure scenarios"""
    
    # Simulate different types of failures
    call_count = {"count": 0}
    
    async def flaky_function(user_id: str):
        """Simulates a flaky API call"""
        call_count["count"] += 1
        
        if call_count["count"] <= 2:
            # Simulate timeout on first 2 attempts
            raise httpx.TimeoutException("Request timed out")
        elif call_count["count"] == 3:
            # Simulate rate limit on 3rd attempt
            response = httpx.Response(429, json={"error": "Rate limited"})
            raise httpx.HTTPStatusError("Rate limited", request=None, response=response)
        else:
            # Success on 4th attempt
            return {"status": "success", "data": f"Processed {user_id}"}
    
    # Test with retry manager
    retry_manager = RetryManager()
    result = await retry_manager.execute_with_retry(
        func=flaky_function,
        func_args=("test_user_123",),
        operation_key="test_operation"
    )
    
    print(f"Result: {result}")
    print(f"Metrics: {retry_manager.get_metrics()}")
    
    return result

if __name__ == "__main__":
    # Run test
    asyncio.run(test_retry_system())