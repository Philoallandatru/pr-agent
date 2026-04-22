"""
Load testing tool for PR Agent.

Simulates realistic user behavior and measures system performance under load.
"""

import asyncio
import time
import random
from typing import List, Dict, Any
from dataclasses import dataclass, field
import httpx
from datetime import datetime
import json


@dataclass
class LoadTestConfig:
    """Configuration for load test."""
    base_url: str = "http://localhost:8000"
    auth_token: str = None
    num_users: int = 10
    duration_seconds: int = 60
    ramp_up_seconds: int = 10
    think_time_min: float = 1.0
    think_time_max: float = 5.0


@dataclass
class LoadTestResult:
    """Results from load test."""
    config: LoadTestConfig
    start_time: datetime
    end_time: datetime
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    errors: Dict[str, int] = field(default_factory=dict)
    requests_per_endpoint: Dict[str, int] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return (self.end_time - self.start_time).total_seconds()

    @property
    def requests_per_second(self) -> float:
        return self.total_requests / self.duration if self.duration > 0 else 0

    @property
    def success_rate(self) -> float:
        return self.successful_requests / self.total_requests if self.total_requests > 0 else 0

    @property
    def average_response_time(self) -> float:
        return self.total_response_time / self.total_requests if self.total_requests > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'config': {
                'base_url': self.config.base_url,
                'num_users': self.config.num_users,
                'duration_seconds': self.config.duration_seconds,
                'ramp_up_seconds': self.config.ramp_up_seconds
            },
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'duration': self.duration,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'requests_per_second': self.requests_per_second,
            'success_rate': self.success_rate,
            'average_response_time': self.average_response_time,
            'errors': self.errors,
            'requests_per_endpoint': self.requests_per_endpoint
        }


class VirtualUser:
    """Simulates a single user interacting with the system."""

    def __init__(self, user_id: int, config: LoadTestConfig, result: LoadTestResult):
        self.user_id = user_id
        self.config = config
        self.result = result
        self.client = None

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.config.auth_token:
            headers["Authorization"] = f"Bearer {self.config.auth_token}"
        return headers

    async def _make_request(self, method: str, endpoint: str, **kwargs) -> bool:
        """Make a request and record metrics."""
        start_time = time.perf_counter()
        try:
            response = await self.client.request(
                method,
                f"{self.config.base_url}{endpoint}",
                headers=self._get_headers(),
                **kwargs
            )
            elapsed = time.perf_counter() - start_time

            self.result.total_requests += 1
            self.result.total_response_time += elapsed
            self.result.response_times.append(elapsed)
            self.result.requests_per_endpoint[endpoint] = \
                self.result.requests_per_endpoint.get(endpoint, 0) + 1

            if 200 <= response.status_code < 300:
                self.result.successful_requests += 1
                return True
            else:
                self.result.failed_requests += 1
                error_key = f"HTTP {response.status_code}"
                self.result.errors[error_key] = self.result.errors.get(error_key, 0) + 1
                return False

        except Exception as e:
            elapsed = time.perf_counter() - start_time
            self.result.total_requests += 1
            self.result.failed_requests += 1
            self.result.total_response_time += elapsed
            self.result.response_times.append(elapsed)

            error_key = type(e).__name__
            self.result.errors[error_key] = self.result.errors.get(error_key, 0) + 1
            return False

    async def _think(self):
        """Simulate user think time."""
        think_time = random.uniform(self.config.think_time_min, self.config.think_time_max)
        await asyncio.sleep(think_time)

    async def run_scenario(self, end_time: float):
        """Run user scenario until end time."""
        self.client = httpx.AsyncClient(timeout=30.0)

        try:
            while time.time() < end_time:
                # Scenario: Browse repositories and reviews
                await self._make_request("GET", "/api/health")
                await self._think()

                await self._make_request("GET", "/api/repositories")
                await self._think()

                await self._make_request("GET", "/api/reviews")
                await self._think()

                # Occasionally check analytics
                if random.random() < 0.3:
                    await self._make_request("GET", "/api/analytics/overview")
                    await self._think()

                # Occasionally check metrics
                if random.random() < 0.2:
                    await self._make_request("GET", "/metrics")
                    await self._think()

        finally:
            await self.client.aclose()


class LoadTester:
    """Load testing orchestrator."""

    def __init__(self, config: LoadTestConfig):
        self.config = config
        self.result = LoadTestResult(
            config=config,
            start_time=datetime.now(),
            end_time=datetime.now()
        )

    async def run(self):
        """Run the load test."""
        print("=" * 80)
        print("Load Test Starting")
        print("=" * 80)
        print(f"Base URL: {self.config.base_url}")
        print(f"Virtual Users: {self.config.num_users}")
        print(f"Duration: {self.config.duration_seconds}s")
        print(f"Ramp-up: {self.config.ramp_up_seconds}s")
        print()

        self.result.start_time = datetime.now()
        end_time = time.time() + self.config.duration_seconds

        # Create virtual users
        users = [VirtualUser(i, self.config, self.result) for i in range(self.config.num_users)]

        # Ramp up users gradually
        tasks = []
        ramp_up_delay = self.config.ramp_up_seconds / self.config.num_users

        for i, user in enumerate(users):
            await asyncio.sleep(ramp_up_delay)
            print(f"Starting user {i + 1}/{self.config.num_users}")
            tasks.append(asyncio.create_task(user.run_scenario(end_time)))

        # Wait for all users to complete
        print("\nAll users started, running test...")
        await asyncio.gather(*tasks, return_exceptions=True)

        self.result.end_time = datetime.now()

        # Print results
        self.print_results()

    def print_results(self):
        """Print load test results."""
        print("\n" + "=" * 80)
        print("Load Test Results")
        print("=" * 80)
        print(f"\nDuration: {self.result.duration:.2f}s")
        print(f"Total Requests: {self.result.total_requests}")
        print(f"Successful: {self.result.successful_requests}")
        print(f"Failed: {self.result.failed_requests}")
        print(f"Success Rate: {self.result.success_rate * 100:.1f}%")
        print(f"Requests/sec: {self.result.requests_per_second:.2f}")
        print(f"Avg Response Time: {self.result.average_response_time * 1000:.2f}ms")

        if self.result.response_times:
            sorted_times = sorted(self.result.response_times)
            p50 = sorted_times[len(sorted_times) // 2]
            p95 = sorted_times[int(len(sorted_times) * 0.95)]
            p99 = sorted_times[int(len(sorted_times) * 0.99)]

            print(f"\nResponse Time Percentiles:")
            print(f"  P50: {p50 * 1000:.2f}ms")
            print(f"  P95: {p95 * 1000:.2f}ms")
            print(f"  P99: {p99 * 1000:.2f}ms")

        if self.result.requests_per_endpoint:
            print(f"\nRequests per Endpoint:")
            for endpoint, count in sorted(self.result.requests_per_endpoint.items(),
                                         key=lambda x: x[1], reverse=True):
                print(f"  {endpoint}: {count}")

        if self.result.errors:
            print(f"\nErrors:")
            for error, count in sorted(self.result.errors.items(),
                                      key=lambda x: x[1], reverse=True):
                print(f"  {error}: {count}")

    def save_report(self, output_file: str):
        """Save results to JSON file."""
        with open(output_file, 'w') as f:
            json.dump(self.result.to_dict(), f, indent=2)
        print(f"\nReport saved to: {output_file}")


async def main():
    """Run load test."""
    import argparse

    parser = argparse.ArgumentParser(description='PR Agent Load Testing')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL')
    parser.add_argument('--token', help='Authentication token')
    parser.add_argument('--users', type=int, default=10, help='Number of virtual users')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--ramp-up', type=int, default=10, help='Ramp-up time in seconds')
    parser.add_argument('--output', help='Output file for JSON report')

    args = parser.parse_args()

    config = LoadTestConfig(
        base_url=args.url,
        auth_token=args.token,
        num_users=args.users,
        duration_seconds=args.duration,
        ramp_up_seconds=args.ramp_up
    )

    tester = LoadTester(config)

    try:
        await tester.run()

        if args.output:
            tester.save_report(args.output)

    except KeyboardInterrupt:
        print("\n\nLoad test interrupted by user")
        tester.result.end_time = datetime.now()
        tester.print_results()


if __name__ == '__main__':
    asyncio.run(main())
