#!/usr/bin/env python3
"""
Test script for the enhanced retry system
Run this to verify all retry mechanisms work correctly
"""

import asyncio
import httpx
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.enhanced_retry_system import (
    RetryManager, RetryConfig, RetryStrategy,
    CircuitBreakerConfig, EnhancedBatchProcessor,
    ErrorClassifier
)

class TestScenarios:
    """Various failure scenarios to test retry logic"""
    
    def __init__(self):
        self.call_counts = {}
        self.failure_patterns = {}
    
    async def flaky_api_call(self, user_id: str, failure_pattern: str = "random"):
        """Simulates various API failure patterns"""
        
        # Track call count per user
        if user_id not in self.call_counts:
            self.call_counts[user_id] = 0
        self.call_counts[user_id] += 1
        
        attempt = self.call_counts[user_id]
        
        if failure_pattern == "rate_limit":
            # Fail with 429 for first 3 attempts
            if attempt <= 3:
                response = httpx.Response(429, json={"error": "Rate limited"})
                raise httpx.HTTPStatusError("Rate limited", request=None, response=response)
        
        elif failure_pattern == "timeout":
            # Timeout on first 2 attempts
            if attempt <= 2:
                raise httpx.TimeoutException("Request timed out")
        
        elif failure_pattern == "server_error":
            # 500 error on first attempt, 503 on second
            if attempt == 1:
                response = httpx.Response(500, json={"error": "Internal server error"})
                raise httpx.HTTPStatusError("Server error", request=None, response=response)
            elif attempt == 2:
                response = httpx.Response(503, json={"error": "Service unavailable"})
                raise httpx.HTTPStatusError("Service unavailable", request=None, response=response)
        
        elif failure_pattern == "permanent":
            # Always fail with 404
            response = httpx.Response(404, json={"error": "User not found"})
            raise httpx.HTTPStatusError("Not found", request=None, response=response)
        
        elif failure_pattern == "invalid_api_key":
            # Non-retryable error
            response = httpx.Response(401, json={"error": "Invalid API key"})
            raise httpx.HTTPStatusError("Invalid API key", request=None, response=response)
        
        elif failure_pattern == "json_error":
            # JSON decode error on first attempt
            if attempt == 1:
                raise json.JSONDecodeError("Invalid JSON", "", 0)
        
        elif failure_pattern == "connection_error":
            # Connection errors for first 2 attempts
            if attempt <= 2:
                raise httpx.ConnectError("Connection refused")
        
        elif failure_pattern == "random":
            # Random failures 50% of the time for first 3 attempts
            if attempt <= 3 and random.random() < 0.5:
                errors = [
                    httpx.TimeoutException("Timeout"),
                    httpx.ConnectError("Connection error"),
                    httpx.HTTPStatusError("Server error", request=None, 
                                        response=httpx.Response(500, json={"error": "Random error"}))
                ]
                raise random.choice(errors)
        
        elif failure_pattern == "circuit_breaker":
            # Fail consistently to trigger circuit breaker
            if attempt <= 10:
                response = httpx.Response(500, json={"error": "Consistent failure"})
                raise httpx.HTTPStatusError("Server consistently failing", request=None, response=response)
        
        # Success case
        return {
            "status": "success",
            "user_id": user_id,
            "data": f"Processed after {attempt} attempts",
            "pattern": failure_pattern
        }

async def test_basic_retry():
    """Test basic retry with timeout errors"""
    print("\n=== Testing Basic Retry with Timeouts ===")
    
    test = TestScenarios()
    retry_manager = RetryManager(
        config=RetryConfig(
            max_attempts=5,
            initial_delay=0.5,
            strategy=RetryStrategy.EXPONENTIAL
        )
    )
    
    result = await retry_manager.execute_with_retry(
        func=test.flaky_api_call,
        func_args=("user_123", "timeout"),
        operation_key="test_timeout"
    )
    
    print(f"Result: {result['status']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Final call count: {test.call_counts['user_123']}")
    
    assert result['status'] == 'success'
    assert result['attempts'] == 3  # Should succeed on 3rd attempt

async def test_rate_limiting():
    """Test aggressive retry for rate limiting"""
    print("\n=== Testing Rate Limit Handling ===")
    
    test = TestScenarios()
    retry_manager = RetryManager(
        config=RetryConfig(
            max_attempts=5,
            initial_delay=1.0,
            strategy=RetryStrategy.AGGRESSIVE
        )
    )
    
    result = await retry_manager.execute_with_retry(
        func=test.flaky_api_call,
        func_args=("user_456", "rate_limit"),
        operation_key="test_rate_limit"
    )
    
    print(f"Result: {result['status']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Retry history: {json.dumps(result['retry_history'], indent=2)}")

async def test_permanent_failure():
    """Test that permanent failures don't retry unnecessarily"""
    print("\n=== Testing Permanent Failure (404) ===")
    
    test = TestScenarios()
    retry_manager = RetryManager()
    
    result = await retry_manager.execute_with_retry(
        func=test.flaky_api_call,
        func_args=("user_789", "permanent"),
        operation_key="test_permanent"
    )
    
    print(f"Result: {result['status']}")
    print(f"Attempts: {result['attempts']}")
    print(f"Reason: {result.get('reason')}")
    
    assert result['status'] == 'permanent_failure'
    assert result['attempts'] == 1  # Should not retry

async def test_circuit_breaker():
    """Test circuit breaker activation"""
    print("\n=== Testing Circuit Breaker ===")
    
    test = TestScenarios()
    retry_manager = RetryManager(
        circuit_config=CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout=timedelta(seconds=5)
        )
    )
    
    # Make multiple calls that will fail
    users = [f"user_{i}" for i in range(5)]
    results = []
    
    for user in users:
        result = await retry_manager.execute_with_retry(
            func=test.flaky_api_call,
            func_args=(user, "circuit_breaker"),
            operation_key="test_circuit"  # Same key to share circuit breaker
        )
        results.append(result)
        print(f"User {user}: {result['status']}")
    
    # Check that circuit breaker opened
    circuit_open_count = sum(1 for r in results if r['status'] == 'circuit_breaker_open')
    print(f"Circuit breaker rejections: {circuit_open_count}")
    
    assert circuit_open_count > 0  # Some requests should be rejected

async def test_batch_processing():
    """Test batch processing with mixed failure patterns"""
    print("\n=== Testing Batch Processing ===")
    
    test = TestScenarios()
    processor = EnhancedBatchProcessor(batch_size=3, delay_between_batches=0.5)
    
    # Create users with different failure patterns
    users = [
        {"user_id": "batch_1", "pattern": "timeout"},
        {"user_id": "batch_2", "pattern": "server_error"},
        {"user_id": "batch_3", "pattern": "json_error"},
        {"user_id": "batch_4", "pattern": "permanent"},
        {"user_id": "batch_5", "pattern": "random"},
        {"user_id": "batch_6", "pattern": "connection_error"},
    ]
    
    async def process_user(user_id: str):
        # Find pattern for this user
        pattern = next((u["pattern"] for u in users if u["user_id"] == user_id), "random")
        return await test.flaky_api_call(user_id, pattern)
    
    summary = await processor.process_users(users, process_user, "test_batch")
    
    print(f"\nBatch Processing Summary:")
    print(f"Total users: {summary['total_users']}")
    print(f"Successful: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success rate: {summary['success_rate']:.1f}%")
    print(f"Circuit breaker rejections: {summary['circuit_breaker_rejections']}")
    
    if summary['dead_letter_queue']:
        print(f"\nDead Letter Queue Items:")
        for item in summary['dead_letter_queue']:
            print(f"  - {item['operation_key']}: {item['error_type']}")

async def test_error_classification():
    """Test error classification logic"""
    print("\n=== Testing Error Classification ===")
    
    test_errors = [
        (httpx.HTTPStatusError("", request=None, response=httpx.Response(429)), True, "Rate limit"),
        (httpx.HTTPStatusError("", request=None, response=httpx.Response(500)), True, "Server error"),
        (httpx.HTTPStatusError("", request=None, response=httpx.Response(404)), False, "Not found"),
        (httpx.TimeoutException("Timeout"), True, "Timeout"),
        (Exception("Invalid API key"), False, "API key"),
        (json.JSONDecodeError("", "", 0), True, "JSON error"),
        (ConnectionError("Connection refused"), True, "Connection"),
        (Exception("Out of memory"), False, "Memory"),
        (Exception("Random error"), True, "Unknown"),
    ]
    
    for error, expected_retry, description in test_errors:
        should_retry, reason = ErrorClassifier.should_retry(error)
        status = "✓" if should_retry == expected_retry else "✗"
        print(f"{status} {description}: retry={should_retry}, reason='{reason}'")

async def test_metrics_and_monitoring():
    """Test metrics collection and monitoring"""
    print("\n=== Testing Metrics and Monitoring ===")
    
    test = TestScenarios()
    retry_manager = RetryManager()
    
    # Run several operations with different outcomes
    patterns = ["timeout", "server_error", "permanent", "random", "json_error"]
    
    for i, pattern in enumerate(patterns):
        await retry_manager.execute_with_retry(
            func=test.flaky_api_call,
            func_args=(f"metrics_user_{i}", pattern),
            operation_key=f"metrics_op_{i}"
        )
    
    # Get metrics
    metrics = retry_manager.get_metrics()
    
    print(f"\nMetrics Summary:")
    print(f"Total operations: {metrics['total_operations']}")
    print(f"Total attempts: {metrics['total_attempts']}")
    print(f"Total successes: {metrics['total_successes']}")
    print(f"Total failures: {metrics['total_failures']}")
    print(f"Success rate: {metrics['success_rate']:.1f}%")
    print(f"Dead letter queue size: {metrics['dead_letter_queue_size']}")
    
    # Check circuit breakers
    if metrics['circuit_breakers']:
        print(f"\nCircuit Breakers:")
        for key, state in metrics['circuit_breakers'].items():
            print(f"  {key}: {state}")

async def run_all_tests():
    """Run all test scenarios"""
    print("=" * 60)
    print("ENHANCED RETRY SYSTEM TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Basic Retry", test_basic_retry),
        ("Rate Limiting", test_rate_limiting),
        ("Permanent Failures", test_permanent_failure),
        ("Circuit Breaker", test_circuit_breaker),
        ("Error Classification", test_error_classification),
        ("Batch Processing", test_batch_processing),
        ("Metrics & Monitoring", test_metrics_and_monitoring),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            await test_func()
            passed += 1
            print(f"\n✅ {name} - PASSED\n")
        except Exception as e:
            failed += 1
            print(f"\n❌ {name} - FAILED: {e}\n")
    
    print("=" * 60)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)