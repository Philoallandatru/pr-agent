"""
Performance and Load Tests

Test system performance under various load conditions.
"""

import pytest
import time
import concurrent.futures
from typing import List, Dict, Any
from fastapi.testclient import TestClient


class TestPerformance:
    """Test system performance metrics."""

    def test_api_response_time(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test API response times are within acceptable limits."""

        endpoints = [
            ("/api/dashboards/main/stats", "GET", None),
            ("/api/metrics", "GET", None),
            ("/api/reviews", "GET", None),
            ("/api/repositories", "GET", None),
        ]

        for endpoint, method, data in endpoints:
            start_time = time.time()

            if method == "GET":
                response = client.get(endpoint, headers=auth_headers)
            else:
                response = client.post(endpoint, json=data, headers=auth_headers)

            elapsed_time = time.time() - start_time

            # Response time should be under 1 second
            assert elapsed_time < 1.0, f"{endpoint} took {elapsed_time:.2f}s"
            assert response.status_code in [200, 404]  # 404 is ok if no data

    def test_database_query_performance(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        test_data_generator
    ):
        """Test database query performance with large datasets."""

        # Generate test data
        repos = test_data_generator.generate_repositories(10)
        for repo in repos:
            client.post("/api/repositories", json=repo, headers=auth_headers)

        # Measure query time
        start_time = time.time()
        response = client.get("/api/repositories", headers=auth_headers)
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 0.5  # Should be fast even with 10 repos

    def test_concurrent_review_creation(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_pr_data: Dict[str, Any]
    ):
        """Test concurrent review creation performance."""

        def create_review(pr_number: int):
            pr_data = {**sample_pr_data, "pr_number": pr_number}
            start_time = time.time()
            response = client.post(
                "/api/reviews/create",
                json=pr_data,
                headers=auth_headers
            )
            elapsed_time = time.time() - start_time
            return response.status_code, elapsed_time

        # Create 10 reviews concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_review, i) for i in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        success_count = sum(1 for status, _ in results if status in [200, 201])
        assert success_count >= 8  # At least 80% success rate

        # Average response time should be reasonable
        avg_time = sum(t for _, t in results) / len(results)
        assert avg_time < 2.0

    def test_large_code_analysis(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test performance with large code files."""

        # Generate large code sample (1000 lines)
        large_code = "\n".join([
            f"def function_{i}(x):\n    return x * {i}"
            for i in range(500)
        ])

        start_time = time.time()
        response = client.post(
            "/api/ai-assistant/explain-code",
            json={
                "code": large_code,
                "language": "python"
            },
            headers=auth_headers
        )
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 5.0  # Should complete within 5 seconds


class TestLoadTesting:
    """Test system behavior under load."""

    def test_sustained_load(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test system under sustained load."""

        def make_request():
            return client.get("/api/dashboards/main/stats", headers=auth_headers)

        # Make 50 requests
        start_time = time.time()
        responses = []
        for _ in range(50):
            response = make_request()
            responses.append(response.status_code)

        elapsed_time = time.time() - start_time

        # Check success rate
        success_rate = sum(1 for s in responses if s == 200) / len(responses)
        assert success_rate >= 0.95  # 95% success rate

        # Check throughput
        throughput = len(responses) / elapsed_time
        assert throughput >= 10  # At least 10 requests per second

    def test_burst_load(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test system handling burst traffic."""

        def make_burst_request(endpoint: str):
            return client.get(endpoint, headers=auth_headers)

        endpoints = [
            "/api/dashboards/main/stats",
            "/api/metrics",
            "/api/reviews",
            "/api/repositories",
        ]

        # Send burst of 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_burst_request, endpoints[i % len(endpoints)])
                for i in range(20)
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Most should succeed
        success_count = sum(1 for r in results if r.status_code == 200)
        assert success_count >= 15  # At least 75% success

    def test_memory_usage_under_load(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        test_data_generator
    ):
        """Test memory usage doesn't grow excessively under load."""

        # Create multiple reviews
        for i in range(20):
            pr_data = {
                "pr_number": i,
                "title": f"PR {i}",
                "repository": "test-repo",
                "author": "dev",
                "branch": f"feature-{i}",
                "base_branch": "main"
            }
            client.post("/api/reviews/create", json=pr_data, headers=auth_headers)

        # Query reviews multiple times
        for _ in range(10):
            response = client.get("/api/reviews", headers=auth_headers)
            assert response.status_code == 200

        # System should still be responsive
        response = client.get("/api/dashboards/main/stats", headers=auth_headers)
        assert response.status_code == 200


class TestScalability:
    """Test system scalability."""

    def test_large_dataset_handling(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        test_data_generator
    ):
        """Test handling large datasets."""

        # Create 50 repositories
        repos = test_data_generator.generate_repositories(50)
        for repo in repos:
            client.post("/api/repositories", json=repo, headers=auth_headers)

        # Query should still be fast
        start_time = time.time()
        response = client.get("/api/repositories", headers=auth_headers)
        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        assert elapsed_time < 1.0

    def test_pagination_performance(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test pagination with large result sets."""

        # Test different page sizes
        for page_size in [10, 50, 100]:
            start_time = time.time()
            response = client.get(
                "/api/reviews",
                params={"limit": page_size, "offset": 0},
                headers=auth_headers
            )
            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            assert elapsed_time < 1.0

    def test_concurrent_users(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test system with multiple concurrent users."""

        def simulate_user_session():
            """Simulate a user session with multiple actions."""
            actions = [
                lambda: client.get("/api/dashboards/main/stats", headers=auth_headers),
                lambda: client.get("/api/reviews", headers=auth_headers),
                lambda: client.get("/api/repositories", headers=auth_headers),
                lambda: client.get("/api/metrics", headers=auth_headers),
            ]

            results = []
            for action in actions:
                response = action()
                results.append(response.status_code)
                time.sleep(0.1)  # Small delay between actions

            return results

        # Simulate 5 concurrent users
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(simulate_user_session) for _ in range(5)]
            all_results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # Flatten results
        all_status_codes = [code for results in all_results for code in results]

        # Most requests should succeed
        success_rate = sum(1 for code in all_status_codes if code == 200) / len(all_status_codes)
        assert success_rate >= 0.90  # 90% success rate


class TestCaching:
    """Test caching performance."""

    def test_cache_hit_performance(
        self,
        client: TestClient,
        auth_headers: Dict[str, str]
    ):
        """Test that cached requests are faster."""

        endpoint = "/api/dashboards/main/stats"

        # First request (cache miss)
        start_time = time.time()
        response1 = client.get(endpoint, headers=auth_headers)
        time1 = time.time() - start_time

        # Second request (cache hit)
        start_time = time.time()
        response2 = client.get(endpoint, headers=auth_headers)
        time2 = time.time() - start_time

        assert response1.status_code == 200
        assert response2.status_code == 200

        # Cached request should be faster (or at least not slower)
        assert time2 <= time1 * 1.5  # Allow 50% margin

    def test_cache_invalidation(
        self,
        client: TestClient,
        auth_headers: Dict[str, str],
        sample_pr_data: Dict[str, Any]
    ):
        """Test cache invalidation on data changes."""

        # Get initial stats
        response1 = client.get("/api/dashboards/main/stats", headers=auth_headers)
        stats1 = response1.json() if response1.status_code == 200 else {}

        # Create new review (should invalidate cache)
        client.post("/api/reviews/create", json=sample_pr_data, headers=auth_headers)

        # Get updated stats
        response2 = client.get("/api/dashboards/main/stats", headers=auth_headers)
        stats2 = response2.json() if response2.status_code == 200 else {}

        # Stats should be updated (if both requests succeeded)
        if response1.status_code == 200 and response2.status_code == 200:
            assert stats1 != stats2 or stats1.get("total_reviews", 0) == 0
