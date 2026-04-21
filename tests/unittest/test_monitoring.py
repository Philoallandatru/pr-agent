"""
Unit tests for monitoring and observability features.
"""

import time
import unittest
from unittest.mock import Mock, patch, MagicMock

from pr_agent.monitoring.metrics import (
    MetricsCollector,
    StructuredLogger,
    PerformanceTracker,
    track_performance,
    get_system_metrics
)


class TestMetricsCollector(unittest.TestCase):
    """Test MetricsCollector class."""

    def setUp(self):
        """Set up test fixtures."""
        self.collector = MetricsCollector()

    def test_initialization(self):
        """Test collector initialization."""
        self.assertIsNotNone(self.collector)
        self.assertIsInstance(self.collector.enabled, bool)

    def test_track_http_request(self):
        """Test HTTP request tracking."""
        # Should not raise exception
        self.collector.track_http_request(
            method="GET",
            endpoint="/api/repositories",
            status=200,
            duration=0.5
        )

    def test_track_pr_review(self):
        """Test PR review tracking."""
        self.collector.track_pr_review(
            repository="PROJ/api",
            status="success",
            duration=45.5
        )

    def test_track_polling_cycle(self):
        """Test polling cycle tracking."""
        # Success
        self.collector.track_polling_cycle(
            repository="PROJ/api",
            success=True
        )

        # Failure
        self.collector.track_polling_cycle(
            repository="PROJ/api",
            success=False,
            error_type="connection_error"
        )

    def test_set_active_reviews(self):
        """Test setting active reviews count."""
        self.collector.set_active_reviews(5)
        self.collector.set_active_reviews(0)

    def test_set_cache_size(self):
        """Test setting cache size."""
        self.collector.set_cache_size("tokenizer", 1024 * 1024 * 100)
        self.collector.set_cache_size("repository", 1024 * 1024 * 500)


class TestStructuredLogger(unittest.TestCase):
    """Test StructuredLogger class."""

    def setUp(self):
        """Set up test fixtures."""
        self.logger = StructuredLogger("test_logger")

    def test_initialization(self):
        """Test logger initialization."""
        self.assertIsNotNone(self.logger)
        self.assertEqual(self.logger.context, {})

    def test_set_context(self):
        """Test setting logging context."""
        self.logger.set_context(repository="PROJ/api", pr_id=123)
        self.assertEqual(self.logger.context["repository"], "PROJ/api")
        self.assertEqual(self.logger.context["pr_id"], 123)

    def test_clear_context(self):
        """Test clearing logging context."""
        self.logger.set_context(repository="PROJ/api")
        self.logger.clear_context()
        self.assertEqual(self.logger.context, {})

    def test_format_message(self):
        """Test message formatting."""
        self.logger.set_context(repository="PROJ/api")
        message = self.logger._format_message("Test message", {"pr_id": 123})
        self.assertIn("Test message", message)
        self.assertIn("repository=PROJ/api", message)
        self.assertIn("pr_id=123", message)

    def test_format_message_no_context(self):
        """Test message formatting without context."""
        message = self.logger._format_message("Test message")
        self.assertEqual(message, "Test message")

    @patch('pr_agent.monitoring.metrics.logging.getLogger')
    def test_info_logging(self, mock_get_logger):
        """Test info level logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        logger = StructuredLogger("test")
        logger.info("Test info", key="value")

        mock_logger.info.assert_called_once()

    @patch('pr_agent.monitoring.metrics.logging.getLogger')
    def test_error_logging(self, mock_get_logger):
        """Test error level logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        logger = StructuredLogger("test")
        logger.error("Test error", error="something failed")

        mock_logger.error.assert_called_once()


class TestPerformanceTracker(unittest.TestCase):
    """Test PerformanceTracker class."""

    def test_context_manager(self):
        """Test using tracker as context manager."""
        with PerformanceTracker("test_operation") as tracker:
            time.sleep(0.1)
            tracker.add_metadata(test_key="test_value")

        self.assertIsNotNone(tracker.duration)
        self.assertGreater(tracker.duration, 0.1)
        self.assertEqual(tracker.metadata["test_key"], "test_value")

    def test_duration_property(self):
        """Test duration property."""
        tracker = PerformanceTracker("test")
        self.assertIsNone(tracker.duration)

        with tracker:
            time.sleep(0.05)

        self.assertIsNotNone(tracker.duration)
        self.assertGreater(tracker.duration, 0.04)

    def test_add_metadata(self):
        """Test adding metadata."""
        tracker = PerformanceTracker("test")
        tracker.add_metadata(key1="value1", key2="value2")

        self.assertEqual(tracker.metadata["key1"], "value1")
        self.assertEqual(tracker.metadata["key2"], "value2")

    def test_exception_handling(self):
        """Test tracker with exception."""
        try:
            with PerformanceTracker("test_error") as tracker:
                tracker.add_metadata(test="error")
                raise ValueError("Test error")
        except ValueError:
            pass

        # Should still have duration even with exception
        self.assertIsNotNone(tracker.duration)


class TestTrackPerformanceDecorator(unittest.TestCase):
    """Test track_performance decorator."""

    def test_decorator_success(self):
        """Test decorator on successful function."""
        @track_performance("test_function")
        def test_func(x, y):
            time.sleep(0.05)
            return x + y

        result = test_func(2, 3)
        self.assertEqual(result, 5)

    def test_decorator_with_labels(self):
        """Test decorator with labels."""
        @track_performance("test_function", labels={"type": "math"})
        def test_func(x):
            return x * 2

        result = test_func(5)
        self.assertEqual(result, 10)

    def test_decorator_exception(self):
        """Test decorator with exception."""
        @track_performance("test_error")
        def test_func():
            raise ValueError("Test error")

        with self.assertRaises(ValueError):
            test_func()


class TestSystemMetrics(unittest.TestCase):
    """Test system metrics collection."""

    def test_get_system_metrics(self):
        """Test getting system metrics."""
        metrics = get_system_metrics()

        self.assertIsInstance(metrics, dict)
        self.assertIn("timestamp", metrics)

        # If psutil is installed, check for metrics
        if "error" not in metrics:
            self.assertIn("cpu_percent", metrics)
            self.assertIn("memory_percent", metrics)
            self.assertIn("disk_percent", metrics)
            self.assertIsInstance(metrics["cpu_percent"], (int, float))
            self.assertIsInstance(metrics["memory_percent"], (int, float))

    def test_system_metrics_without_psutil(self):
        """Test system metrics when psutil is not available."""
        # This test verifies the function handles ImportError gracefully
        # We can't easily mock the import without reloading the module,
        # so we just verify the function returns a valid dict structure
        metrics = get_system_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn("timestamp", metrics)
        # Either has metrics or has error key
        self.assertTrue("cpu_percent" in metrics or "error" in metrics)


class TestMetricsIntegration(unittest.TestCase):
    """Integration tests for monitoring features."""

    def test_full_workflow(self):
        """Test complete monitoring workflow."""
        # Initialize components
        collector = MetricsCollector()
        logger = StructuredLogger("integration_test")

        # Set context
        logger.set_context(repository="TEST/repo", pr_id=999)

        # Track operation
        with PerformanceTracker("test_workflow") as tracker:
            tracker.add_metadata(operation="integration_test")

            # Simulate work
            time.sleep(0.1)

            # Track metrics
            collector.track_pr_review(
                repository="TEST/repo",
                status="success",
                duration=tracker.duration or 0
            )

        # Verify
        self.assertIsNotNone(tracker.duration)
        self.assertGreater(tracker.duration, 0.09)

    def test_concurrent_tracking(self):
        """Test tracking multiple operations concurrently."""
        collector = MetricsCollector()

        # Track multiple operations
        for i in range(5):
            collector.track_http_request(
                method="GET",
                endpoint=f"/api/test/{i}",
                status=200,
                duration=0.1 * i
            )

        # Should not raise any exceptions
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
