"""
Performance benchmarks for PR Agent API endpoints.

This module provides comprehensive performance testing for all API endpoints,
measuring response times, throughput, and resource usage under various load conditions.
"""

import asyncio
import time
import statistics
from typing import Dict, List, Any, Callable
from dataclasses import dataclass, field
import httpx
import psutil
import json
from datetime import datetime


@dataclass
class BenchmarkResult:
    """Results from a single benchmark run."""
    name: str
    total_requests: int
    duration: float
    requests_per_second: float
    mean_response_time: float
    median_response_time: float
    p95_response_time: float
    p99_response_time: float
    min_response_time: float
    max_response_time: float
    success_count: int
    error_count: int
    success_rate: float
    response_times: List[float] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'total_requests': self.total_requests,
            'duration': self.duration,
            'requests_per_second': self.requests_per_second,
            'mean_response_time': self.mean_response_time,
            'median_response_time': self.median_response_time,
            'p95_response_time': self.p95_response_time,
            'p99_response_time': self.p99_response_time,
            'min_response_time': self.min_response_time,
            'max_response_time': self.max_response_time,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'success_rate': self.success_rate
        }


class APIBenchmark:
    """Benchmark suite for API endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.results: List[BenchmarkResult] = []

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def _make_request(self, client: httpx.AsyncClient, method: str,
                           endpoint: str, **kwargs) -> tuple[float, bool, str]:
        """Make a single HTTP request and measure response time."""
        start_time = time.perf_counter()
        try:
            response = await client.request(method, f"{self.base_url}{endpoint}", **kwargs)
            elapsed = time.perf_counter() - start_time
            success = 200 <= response.status_code < 300
            error_msg = "" if success else f"HTTP {response.status_code}"
            return elapsed, success, error_msg
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return elapsed, False, str(e)

    async def _run_concurrent_requests(self, num_requests: int, num_concurrent: int,
                                      request_func: Callable) -> List[tuple[float, bool, str]]:
        """Run multiple requests concurrently."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            semaphore = asyncio.Semaphore(num_concurrent)

            async def limited_request():
                async with semaphore:
                    return await request_func(client)

            tasks = [limited_request() for _ in range(num_requests)]
            return await asyncio.gather(*tasks)

    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from a list of values."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]

    async def benchmark_endpoint(self, name: str, method: str, endpoint: str,
                                num_requests: int = 100, num_concurrent: int = 10,
                                **kwargs) -> BenchmarkResult:
        """Benchmark a single endpoint."""
        print(f"\nRunning benchmark: {name}")
        print(f"  Requests: {num_requests}, Concurrent: {num_concurrent}")

        async def request_func(client):
            return await self._make_request(client, method, endpoint,
                                           headers=self._get_headers(), **kwargs)

        start_time = time.perf_counter()
        results = await self._run_concurrent_requests(num_requests, num_concurrent, request_func)
        duration = time.perf_counter() - start_time

        response_times = [r[0] for r in results]
        successes = [r[1] for r in results]
        errors = [r[2] for r in results if not r[1]]

        success_count = sum(successes)
        error_count = len(results) - success_count

        result = BenchmarkResult(
            name=name,
            total_requests=num_requests,
            duration=duration,
            requests_per_second=num_requests / duration,
            mean_response_time=statistics.mean(response_times),
            median_response_time=statistics.median(response_times),
            p95_response_time=self._calculate_percentile(response_times, 95),
            p99_response_time=self._calculate_percentile(response_times, 99),
            min_response_time=min(response_times),
            max_response_time=max(response_times),
            success_count=success_count,
            error_count=error_count,
            success_rate=success_count / num_requests,
            response_times=response_times,
            errors=errors
        )

        self.results.append(result)
        self._print_result(result)
        return result

    def _print_result(self, result: BenchmarkResult):
        """Print benchmark result in a readable format."""
        print(f"\n  Results:")
        print(f"    Duration: {result.duration:.2f}s")
        print(f"    Requests/sec: {result.requests_per_second:.2f}")
        print(f"    Success rate: {result.success_rate * 100:.1f}%")
        print(f"    Response times:")
        print(f"      Mean: {result.mean_response_time * 1000:.2f}ms")
        print(f"      Median: {result.median_response_time * 1000:.2f}ms")
        print(f"      P95: {result.p95_response_time * 1000:.2f}ms")
        print(f"      P99: {result.p99_response_time * 1000:.2f}ms")
        print(f"      Min: {result.min_response_time * 1000:.2f}ms")
        print(f"      Max: {result.max_response_time * 1000:.2f}ms")
        if result.errors:
            print(f"    Errors: {result.error_count}")
            for error in set(result.errors[:5]):
                print(f"      - {error}")

    async def run_all_benchmarks(self, num_requests: int = 100, num_concurrent: int = 10):
        """Run benchmarks for all major endpoints."""
        print("=" * 80)
        print("PR Agent API Performance Benchmarks")
        print("=" * 80)

        # Health check
        await self.benchmark_endpoint(
            "Health Check",
            "GET",
            "/api/health",
            num_requests=num_requests,
            num_concurrent=num_concurrent
        )

        # Metrics endpoint
        await self.benchmark_endpoint(
            "Metrics",
            "GET",
            "/metrics",
            num_requests=num_requests,
            num_concurrent=num_concurrent
        )

        # List repositories
        await self.benchmark_endpoint(
            "List Repositories",
            "GET",
            "/api/repositories",
            num_requests=num_requests // 2,
            num_concurrent=num_concurrent
        )

        # List reviews
        await self.benchmark_endpoint(
            "List Reviews",
            "GET",
            "/api/reviews",
            num_requests=num_requests // 2,
            num_concurrent=num_concurrent
        )

        # Analytics overview
        await self.benchmark_endpoint(
            "Analytics Overview",
            "GET",
            "/api/analytics/overview",
            num_requests=num_requests // 4,
            num_concurrent=num_concurrent // 2
        )

        # Audit logs
        await self.benchmark_endpoint(
            "Audit Logs",
            "GET",
            "/api/audit/logs",
            num_requests=num_requests // 4,
            num_concurrent=num_concurrent // 2
        )

    def generate_report(self, output_file: str = None) -> Dict[str, Any]:
        """Generate a comprehensive benchmark report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'base_url': self.base_url,
            'system_info': {
                'cpu_count': psutil.cpu_count(),
                'memory_total': psutil.virtual_memory().total,
                'python_version': psutil.PYTHON
            },
            'benchmarks': [r.to_dict() for r in self.results],
            'summary': {
                'total_benchmarks': len(self.results),
                'total_requests': sum(r.total_requests for r in self.results),
                'total_duration': sum(r.duration for r in self.results),
                'average_rps': statistics.mean([r.requests_per_second for r in self.results]),
                'average_response_time': statistics.mean([r.mean_response_time for r in self.results]),
                'overall_success_rate': sum(r.success_count for r in self.results) /
                                       sum(r.total_requests for r in self.results)
            }
        }

        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\nReport saved to: {output_file}")

        return report

    def print_summary(self):
        """Print a summary of all benchmark results."""
        print("\n" + "=" * 80)
        print("BENCHMARK SUMMARY")
        print("=" * 80)

        total_requests = sum(r.total_requests for r in self.results)
        total_duration = sum(r.duration for r in self.results)
        avg_rps = statistics.mean([r.requests_per_second for r in self.results])
        avg_response = statistics.mean([r.mean_response_time for r in self.results])
        overall_success = sum(r.success_count for r in self.results) / total_requests

        print(f"\nTotal benchmarks: {len(self.results)}")
        print(f"Total requests: {total_requests}")
        print(f"Total duration: {total_duration:.2f}s")
        print(f"Average RPS: {avg_rps:.2f}")
        print(f"Average response time: {avg_response * 1000:.2f}ms")
        print(f"Overall success rate: {overall_success * 100:.1f}%")

        print("\nTop 5 fastest endpoints:")
        sorted_by_speed = sorted(self.results, key=lambda r: r.mean_response_time)
        for i, result in enumerate(sorted_by_speed[:5], 1):
            print(f"  {i}. {result.name}: {result.mean_response_time * 1000:.2f}ms")

        print("\nTop 5 slowest endpoints:")
        for i, result in enumerate(reversed(sorted_by_speed[-5:]), 1):
            print(f"  {i}. {result.name}: {result.mean_response_time * 1000:.2f}ms")


async def main():
    """Run the benchmark suite."""
    import argparse

    parser = argparse.ArgumentParser(description='PR Agent API Performance Benchmarks')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL')
    parser.add_argument('--token', help='Authentication token')
    parser.add_argument('--requests', type=int, default=100, help='Number of requests per benchmark')
    parser.add_argument('--concurrent', type=int, default=10, help='Number of concurrent requests')
    parser.add_argument('--output', help='Output file for JSON report')

    args = parser.parse_args()

    benchmark = APIBenchmark(base_url=args.url, auth_token=args.token)

    try:
        await benchmark.run_all_benchmarks(
            num_requests=args.requests,
            num_concurrent=args.concurrent
        )

        benchmark.print_summary()

        if args.output:
            benchmark.generate_report(args.output)

    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\n\nError running benchmarks: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
