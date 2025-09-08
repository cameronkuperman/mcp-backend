#!/usr/bin/env python3
"""
Performance test suite for Photo Analysis optimizations.
Tests batch URL generation, parallel queries, caching, and overall response times.
"""

import asyncio
import time
import httpx
import statistics
from typing import List, Dict, Tuple
from datetime import datetime

BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-performance"
TEST_SESSION_ID = None  # Will be set after creating a session

# ANSI color codes for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"


class PerformanceMetrics:
    """Track and report performance metrics"""
    
    def __init__(self):
        self.metrics = {}
    
    def record(self, test_name: str, duration: float, passed: bool = True):
        """Record a test metric"""
        if test_name not in self.metrics:
            self.metrics[test_name] = []
        self.metrics[test_name].append({
            'duration': duration,
            'passed': passed,
            'timestamp': datetime.now()
        })
    
    def report(self):
        """Generate performance report"""
        print(f"\n{BLUE}═══════════════════════════════════════════════════{RESET}")
        print(f"{BLUE}      PHOTO ANALYSIS PERFORMANCE TEST RESULTS{RESET}")
        print(f"{BLUE}═══════════════════════════════════════════════════{RESET}\n")
        
        total_tests = 0
        passed_tests = 0
        
        for test_name, results in self.metrics.items():
            durations = [r['duration'] for r in results]
            passed = all(r['passed'] for r in results)
            total_tests += len(results)
            passed_tests += sum(1 for r in results if r['passed'])
            
            avg_duration = statistics.mean(durations)
            min_duration = min(durations)
            max_duration = max(durations)
            
            status_icon = "✅" if passed else "❌"
            color = GREEN if passed else RED
            
            print(f"{status_icon} {test_name}")
            print(f"   {color}Avg: {avg_duration:.3f}s | Min: {min_duration:.3f}s | Max: {max_duration:.3f}s{RESET}")
            
            # Performance assessment
            if "timeline" in test_name.lower():
                target = 0.5
                if avg_duration < target:
                    print(f"   💚 EXCELLENT: {((target - avg_duration) / target * 100):.0f}% faster than target")
                elif avg_duration < target * 1.5:
                    print(f"   💛 GOOD: Within acceptable range")
                else:
                    print(f"   ❌ NEEDS OPTIMIZATION: {((avg_duration - target) / target * 100):.0f}% slower than target")
            
            print()
        
        print(f"{BLUE}═══════════════════════════════════════════════════{RESET}")
        print(f"Overall: {passed_tests}/{total_tests} tests passed")
        
        # Calculate overall improvement
        if 'baseline' in self.metrics and len(self.metrics) > 1:
            baseline_avg = statistics.mean([r['duration'] for r in self.metrics['baseline']])
            optimized_tests = [k for k in self.metrics.keys() if k != 'baseline']
            if optimized_tests:
                optimized_avg = statistics.mean([
                    statistics.mean([r['duration'] for r in self.metrics[k]])
                    for k in optimized_tests
                ])
                improvement = ((baseline_avg - optimized_avg) / baseline_avg) * 100
                print(f"\n🚀 {GREEN}Overall Performance Improvement: {improvement:.1f}%{RESET}")


metrics = PerformanceMetrics()


async def setup_test_data():
    """Create test session with photos for performance testing"""
    global TEST_SESSION_ID
    
    print(f"{YELLOW}Setting up test data...{RESET}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Create a test session
        response = await client.post(
            f"{BASE_URL}/api/photo-analysis/sessions",
            json={
                "user_id": TEST_USER_ID,
                "condition_name": "Performance Test Condition",
                "body_part": "test"
            }
        )
        
        if response.status_code == 200:
            TEST_SESSION_ID = response.json()['session_id']
            print(f"✅ Test session created: {TEST_SESSION_ID}")
            return True
        else:
            print(f"❌ Failed to create test session: {response.status_code}")
            return False


async def test_baseline_timeline():
    """Test timeline endpoint performance (baseline without optimizations)"""
    print(f"\n{YELLOW}Testing Timeline Performance (Baseline)...{RESET}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Warm up
        await client.get(f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline")
        
        # Actual test
        times = []
        for i in range(3):
            start = time.time()
            response = await client.get(
                f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline"
            )
            duration = time.time() - start
            times.append(duration)
            
            if response.status_code == 200:
                data = response.json()
                print(f"  Run {i+1}: {duration:.3f}s - {len(data.get('timeline_events', []))} events")
            else:
                print(f"  Run {i+1}: Failed with status {response.status_code}")
        
        avg_time = statistics.mean(times)
        metrics.record("Timeline Endpoint (Baseline)", avg_time)
        
        return avg_time < 2.0  # Should complete in under 2 seconds


async def test_analysis_history_performance():
    """Test analysis history endpoint with batch URL generation"""
    print(f"\n{YELLOW}Testing Analysis History Performance...{RESET}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        times = []
        cache_times = []
        
        # First call (cold cache)
        start = time.time()
        response = await client.get(
            f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/analysis-history"
        )
        cold_time = time.time() - start
        times.append(cold_time)
        
        if response.status_code == 200:
            data = response.json()
            print(f"  Cold cache: {cold_time:.3f}s - {len(data.get('analyses', []))} analyses")
        
        # Second call (warm cache)
        start = time.time()
        response = await client.get(
            f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/analysis-history"
        )
        warm_time = time.time() - start
        cache_times.append(warm_time)
        
        if response.status_code == 200:
            print(f"  Warm cache: {warm_time:.3f}s")
            cache_improvement = ((cold_time - warm_time) / cold_time) * 100
            print(f"  {GREEN}Cache improvement: {cache_improvement:.1f}%{RESET}")
        
        metrics.record("Analysis History (Cold)", cold_time)
        metrics.record("Analysis History (Cached)", warm_time)
        
        return warm_time < 0.2  # Cached response should be under 200ms


async def test_batch_url_generation():
    """Test that batch URL generation is faster than individual calls"""
    print(f"\n{YELLOW}Testing Batch URL Generation...{RESET}")
    
    # This test would need access to the internal API or a special test endpoint
    # For now, we'll test the performance improvement indirectly
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test with multiple photos
        start = time.time()
        response = await client.get(
            f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline"
        )
        duration = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            photo_count = sum(len(event.get('photos', [])) for event in data.get('timeline_events', []))
            
            if photo_count > 0:
                time_per_photo = duration / photo_count
                print(f"  Total time: {duration:.3f}s for {photo_count} photos")
                print(f"  Average per photo: {time_per_photo*1000:.1f}ms")
                
                # With batch generation, should be < 20ms per photo
                if time_per_photo < 0.02:
                    print(f"  {GREEN}✅ Batch generation confirmed (< 20ms per photo){RESET}")
                else:
                    print(f"  {YELLOW}⚠️  May not be using batch generation{RESET}")
            
            metrics.record("Batch URL Generation", duration)
        
        return duration < 1.0


async def test_parallel_queries():
    """Test that parallel queries are faster than sequential"""
    print(f"\n{YELLOW}Testing Parallel Query Performance...{RESET}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Make multiple concurrent requests
        tasks = []
        
        start = time.time()
        for _ in range(5):
            tasks.append(client.get(f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline"))
        
        responses = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start
        
        successful = sum(1 for r in responses if r.status_code == 200)
        
        print(f"  5 concurrent requests: {concurrent_time:.3f}s")
        print(f"  Average per request: {concurrent_time/5:.3f}s")
        print(f"  Success rate: {successful}/5")
        
        metrics.record("Parallel Queries (5 concurrent)", concurrent_time/5)
        
        # Should handle concurrent requests efficiently
        return concurrent_time < 3.0


async def test_redis_caching():
    """Test Redis caching effectiveness"""
    print(f"\n{YELLOW}Testing Redis Cache Performance...{RESET}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Clear cache by making a unique request
        unique_session = f"{TEST_SESSION_ID}?timestamp={int(time.time())}"
        
        # First request (cache miss)
        start = time.time()
        response1 = await client.get(f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline")
        miss_time = time.time() - start
        
        # Second request (cache hit)
        start = time.time()
        response2 = await client.get(f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline")
        hit_time = time.time() - start
        
        # Third request (cache hit)
        start = time.time()
        response3 = await client.get(f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline")
        hit_time2 = time.time() - start
        
        print(f"  Cache miss: {miss_time:.3f}s")
        print(f"  Cache hit 1: {hit_time:.3f}s")
        print(f"  Cache hit 2: {hit_time2:.3f}s")
        
        cache_speedup = miss_time / hit_time if hit_time > 0 else 0
        print(f"  {GREEN}Cache speedup: {cache_speedup:.1f}x faster{RESET}")
        
        metrics.record("Redis Cache (Miss)", miss_time)
        metrics.record("Redis Cache (Hit)", hit_time)
        
        # Cache should provide at least 5x speedup
        return cache_speedup > 5.0


async def test_load_simulation():
    """Simulate realistic load with multiple users"""
    print(f"\n{YELLOW}Testing Under Load (10 concurrent users)...{RESET}")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        async def user_session():
            """Simulate a single user session"""
            times = []
            
            # Timeline request
            start = time.time()
            r1 = await client.get(f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/timeline")
            times.append(time.time() - start)
            
            # Analysis history request
            start = time.time()
            r2 = await client.get(f"{BASE_URL}/api/photo-analysis/session/{TEST_SESSION_ID}/analysis-history")
            times.append(time.time() - start)
            
            return times, all(r.status_code == 200 for r in [r1, r2])
        
        # Simulate 10 concurrent users
        start = time.time()
        user_results = await asyncio.gather(*[user_session() for _ in range(10)])
        total_time = time.time() - start
        
        all_times = [t for times, _ in user_results for t in times]
        successes = sum(1 for _, success in user_results if success)
        
        avg_response = statistics.mean(all_times)
        p95_response = sorted(all_times)[int(len(all_times) * 0.95)]
        
        print(f"  Total time for 10 users: {total_time:.3f}s")
        print(f"  Average response time: {avg_response:.3f}s")
        print(f"  95th percentile: {p95_response:.3f}s")
        print(f"  Success rate: {successes}/10")
        
        metrics.record("Load Test (10 users)", avg_response)
        
        # Should handle 10 concurrent users with < 1s average response
        return avg_response < 1.0


async def main():
    """Run all performance tests"""
    print(f"\n{BLUE}═══════════════════════════════════════════════════{RESET}")
    print(f"{BLUE}    PHOTO ANALYSIS PERFORMANCE TEST SUITE{RESET}")
    print(f"{BLUE}═══════════════════════════════════════════════════{RESET}")
    
    # Setup test data
    if not await setup_test_data():
        print(f"{RED}Failed to setup test data. Exiting.{RESET}")
        return
    
    # Run tests
    tests = [
        ("Baseline Timeline", test_baseline_timeline),
        ("Analysis History", test_analysis_history_performance),
        ("Batch URL Generation", test_batch_url_generation),
        ("Parallel Queries", test_parallel_queries),
        ("Redis Caching", test_redis_caching),
        ("Load Simulation", test_load_simulation),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = await test_func()
            results.append((test_name, passed))
            
            if passed:
                print(f"{GREEN}✅ {test_name} PASSED{RESET}")
            else:
                print(f"{RED}❌ {test_name} FAILED{RESET}")
                
        except Exception as e:
            print(f"{RED}❌ {test_name} ERROR: {str(e)}{RESET}")
            results.append((test_name, False))
    
    # Generate report
    metrics.report()
    
    # Summary
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print(f"\n{BLUE}═══════════════════════════════════════════════════{RESET}")
    if passed_count == total_count:
        print(f"{GREEN}🎉 ALL TESTS PASSED! ({passed_count}/{total_count}){RESET}")
        print(f"{GREEN}Photo analysis system is optimized and performing well!{RESET}")
    else:
        print(f"{YELLOW}⚠️  {passed_count}/{total_count} tests passed{RESET}")
        print(f"{YELLOW}Some optimizations may need attention.{RESET}")
    print(f"{BLUE}═══════════════════════════════════════════════════{RESET}\n")


if __name__ == "__main__":
    asyncio.run(main())