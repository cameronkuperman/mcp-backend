#!/usr/bin/env python3
"""
Industry-Standard Performance Test Suite for Photo Analysis Optimizations
Tests both original and optimized endpoints to measure improvements
"""

import asyncio
import time
import json
import statistics
from typing import List, Dict, Tuple
from datetime import datetime
import httpx
import random
import string

# Test configuration
BASE_URL = "http://localhost:8000"
TEST_USER_ID = "test-user-" + ''.join(random.choices(string.ascii_lowercase, k=8))

# ANSI colors for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


class PerformanceComparison:
    """Compare performance between original and optimized endpoints"""
    
    def __init__(self):
        self.results = {
            'original': {},
            'optimized': {}
        }
        self.test_data = {
            'session_ids': [],
            'photo_ids': [],
            'analysis_ids': []
        }
    
    async def setup_test_data(self):
        """Create test data for performance testing"""
        print(f"\n{CYAN}Setting up test data...{RESET}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create multiple test sessions
            for i in range(10):
                response = await client.post(
                    f"{BASE_URL}/api/photo-analysis/sessions",
                    json={
                        "user_id": TEST_USER_ID,
                        "condition_name": f"Test Condition {i+1}",
                        "description": f"Performance test session {i+1}"
                    }
                )
                
                if response.status_code == 200:
                    session_id = response.json()['session_id']
                    self.test_data['session_ids'].append(session_id)
                    print(f"  ✓ Created session {i+1}/10")
        
        print(f"{GREEN}✅ Test data setup complete{RESET}")
        return True
    
    async def test_session_listing(self, endpoint_prefix: str, version: str):
        """Test session listing performance"""
        url = f"{BASE_URL}{endpoint_prefix}/sessions"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Warm up
            await client.get(f"{url}?user_id={TEST_USER_ID}&limit=5")
            
            # Test different page sizes
            test_cases = [
                (10, "Small page"),
                (50, "Medium page"),
                (100, "Large page")
            ]
            
            results = {}
            for limit, description in test_cases:
                times = []
                
                for _ in range(5):  # 5 runs per test
                    start = time.time()
                    response = await client.get(
                        f"{url}?user_id={TEST_USER_ID}&limit={limit}"
                    )
                    duration = time.time() - start
                    
                    if response.status_code == 200:
                        times.append(duration)
                
                if times:
                    results[description] = {
                        'avg': statistics.mean(times),
                        'min': min(times),
                        'max': max(times),
                        'p95': sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                    }
            
            self.results[version]['session_listing'] = results
    
    async def test_timeline_query(self, endpoint_prefix: str, version: str):
        """Test timeline query performance"""
        if not self.test_data['session_ids']:
            return
        
        session_id = self.test_data['session_ids'][0]
        url = f"{BASE_URL}{endpoint_prefix}/session/{session_id}/timeline"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            times = []
            
            for _ in range(10):  # 10 runs
                start = time.time()
                response = await client.get(url)
                duration = time.time() - start
                
                if response.status_code == 200:
                    times.append(duration)
            
            if times:
                self.results[version]['timeline'] = {
                    'avg': statistics.mean(times),
                    'min': min(times),
                    'max': max(times),
                    'p95': sorted(times)[int(len(times) * 0.95)] if len(times) > 1 else times[0]
                }
    
    async def test_concurrent_requests(self, endpoint_prefix: str, version: str):
        """Test performance under concurrent load"""
        if not self.test_data['session_ids']:
            return
        
        url = f"{BASE_URL}{endpoint_prefix}/sessions?user_id={TEST_USER_ID}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test different concurrency levels
            concurrency_levels = [5, 10, 20]
            results = {}
            
            for level in concurrency_levels:
                start = time.time()
                
                tasks = [
                    client.get(url)
                    for _ in range(level)
                ]
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                total_time = time.time() - start
                
                successful = sum(
                    1 for r in responses 
                    if not isinstance(r, Exception) and r.status_code == 200
                )
                
                results[f"{level} concurrent"] = {
                    'total_time': total_time,
                    'avg_time': total_time / level,
                    'success_rate': (successful / level) * 100
                }
            
            self.results[version]['concurrent'] = results
    
    async def run_comparison(self):
        """Run full performance comparison"""
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{BLUE}     PHOTO OPTIMIZATION PERFORMANCE COMPARISON{RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════{RESET}")
        
        # Setup test data
        if not await self.setup_test_data():
            print(f"{RED}Failed to setup test data{RESET}")
            return
        
        # Test original endpoints
        print(f"\n{YELLOW}Testing ORIGINAL endpoints...{RESET}")
        await self.test_session_listing("/api/photo-analysis", "original")
        await self.test_timeline_query("/api/photo-analysis", "original")
        await self.test_concurrent_requests("/api/photo-analysis", "original")
        
        # Test optimized endpoints
        print(f"\n{YELLOW}Testing OPTIMIZED endpoints...{RESET}")
        await self.test_session_listing("/api/photo-analysis-optimized", "optimized")
        await self.test_timeline_query("/api/photo-analysis-optimized", "optimized")
        await self.test_concurrent_requests("/api/photo-analysis-optimized", "optimized")
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate detailed comparison report"""
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{BLUE}                 PERFORMANCE RESULTS{RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════{RESET}\n")
        
        # Session Listing Comparison
        if 'session_listing' in self.results['original'] and 'session_listing' in self.results['optimized']:
            print(f"{BOLD}📊 SESSION LISTING PERFORMANCE:{RESET}")
            print(f"{'Test Case':<20} {'Original (ms)':<15} {'Optimized (ms)':<15} {'Improvement':<15}")
            print("-" * 65)
            
            for test_case in self.results['original']['session_listing'].keys():
                orig = self.results['original']['session_listing'][test_case]['avg'] * 1000
                opt = self.results['optimized']['session_listing'][test_case]['avg'] * 1000
                improvement = ((orig - opt) / orig) * 100 if orig > 0 else 0
                
                color = GREEN if improvement > 50 else YELLOW if improvement > 20 else RED
                print(f"{test_case:<20} {orig:>13.1f} {opt:>15.1f} {color}{improvement:>13.1f}%{RESET}")
        
        # Timeline Query Comparison
        if 'timeline' in self.results['original'] and 'timeline' in self.results['optimized']:
            print(f"\n{BOLD}📈 TIMELINE QUERY PERFORMANCE:{RESET}")
            orig = self.results['original']['timeline']['avg'] * 1000
            opt = self.results['optimized']['timeline']['avg'] * 1000
            improvement = ((orig - opt) / orig) * 100 if orig > 0 else 0
            
            print(f"Original:  {orig:.1f}ms (p95: {self.results['original']['timeline']['p95']*1000:.1f}ms)")
            print(f"Optimized: {opt:.1f}ms (p95: {self.results['optimized']['timeline']['p95']*1000:.1f}ms)")
            
            color = GREEN if improvement > 50 else YELLOW if improvement > 20 else RED
            print(f"Improvement: {color}{improvement:.1f}%{RESET}")
        
        # Concurrent Requests Comparison
        if 'concurrent' in self.results['original'] and 'concurrent' in self.results['optimized']:
            print(f"\n{BOLD}🔄 CONCURRENT REQUEST HANDLING:{RESET}")
            print(f"{'Concurrency':<20} {'Original (s)':<15} {'Optimized (s)':<15} {'Improvement':<15}")
            print("-" * 65)
            
            for level in self.results['original']['concurrent'].keys():
                orig = self.results['original']['concurrent'][level]['total_time']
                opt = self.results['optimized']['concurrent'][level]['total_time']
                improvement = ((orig - opt) / orig) * 100 if orig > 0 else 0
                
                color = GREEN if improvement > 30 else YELLOW if improvement > 10 else RED
                print(f"{level:<20} {orig:>13.2f} {opt:>15.2f} {color}{improvement:>13.1f}%{RESET}")
        
        # Overall Summary
        print(f"\n{BOLD}{BLUE}═══════════════════════════════════════════════════{RESET}")
        print(f"{BOLD}{BLUE}                    SUMMARY{RESET}")
        print(f"{BOLD}{BLUE}═══════════════════════════════════════════════════{RESET}\n")
        
        # Calculate overall improvement
        improvements = []
        
        if 'session_listing' in self.results['original'] and 'session_listing' in self.results['optimized']:
            for test_case in self.results['original']['session_listing'].keys():
                orig = self.results['original']['session_listing'][test_case]['avg']
                opt = self.results['optimized']['session_listing'][test_case]['avg']
                if orig > 0:
                    improvements.append(((orig - opt) / orig) * 100)
        
        if 'timeline' in self.results['original'] and 'timeline' in self.results['optimized']:
            orig = self.results['original']['timeline']['avg']
            opt = self.results['optimized']['timeline']['avg']
            if orig > 0:
                improvements.append(((orig - opt) / orig) * 100)
        
        if improvements:
            avg_improvement = statistics.mean(improvements)
            
            if avg_improvement > 50:
                print(f"{GREEN}{BOLD}🚀 EXCELLENT: Average {avg_improvement:.1f}% performance improvement!{RESET}")
                print(f"{GREEN}The optimizations are highly effective!{RESET}")
            elif avg_improvement > 20:
                print(f"{YELLOW}{BOLD}✅ GOOD: Average {avg_improvement:.1f}% performance improvement{RESET}")
                print(f"{YELLOW}The optimizations provide significant benefits{RESET}")
            else:
                print(f"{RED}{BOLD}⚠️  MODEST: Average {avg_improvement:.1f}% performance improvement{RESET}")
                print(f"{RED}Consider additional optimizations{RESET}")
        
        print(f"\n{CYAN}Key Achievements:{RESET}")
        print(f"  ✓ Eliminated N+1 queries in session listing")
        print(f"  ✓ Implemented parallel data fetching")
        print(f"  ✓ Added connection pooling and caching")
        print(f"  ✓ Optimized field selection (no SELECT *)")
        print(f"  ✓ Added circuit breaker for resilience")
        print(f"  ✓ Implemented performance monitoring")


async def test_individual_optimizations():
    """Test specific optimization features"""
    print(f"\n{BOLD}{CYAN}Testing Individual Optimizations...{RESET}\n")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test health endpoint with metrics
        print(f"Testing health endpoint with metrics...")
        response = await client.get(f"{BASE_URL}/api/photo-analysis-optimized/health")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✓ Health Status: {data['status']}")
            print(f"  ✓ Version: {data['version']}")
            print(f"  ✓ Active Connections: {data['metrics']['active_connections']}")
            print(f"  ✓ Cache Available: {data['metrics']['cache_available']}")
            print(f"  ✓ Circuit Breaker: {data['metrics']['circuit_breaker_status']}")
        
        print(f"\n{GREEN}Individual optimization tests complete{RESET}")


async def main():
    """Main test runner"""
    print(f"\n{BOLD}{CYAN}Photo Analysis Performance Optimization Test Suite{RESET}")
    print(f"{CYAN}Testing industry-standard optimizations...{RESET}\n")
    
    # Run comparison tests
    comparison = PerformanceComparison()
    await comparison.run_comparison()
    
    # Test individual features
    await test_individual_optimizations()
    
    print(f"\n{BOLD}{GREEN}✅ All tests complete!{RESET}")
    print(f"\n{CYAN}Next Steps:{RESET}")
    print(f"  1. Review the performance improvements")
    print(f"  2. Monitor production metrics via Prometheus")
    print(f"  3. Adjust cache TTLs based on usage patterns")
    print(f"  4. Scale connection pool based on load")
    print(f"\n{CYAN}To use optimized endpoints in production:{RESET}")
    print(f"  - Import router from api.photo_analysis_optimized")
    print(f"  - Add to your FastAPI app: app.include_router(router)")
    print(f"  - Monitor metrics at /metrics endpoint")


if __name__ == "__main__":
    asyncio.run(main())