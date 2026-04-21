"""
Monitoring and observability utilities for PR Agent.

Provides Prometheus metrics, structured logging, and performance tracking.
"""

import time
import logging
from typing import Dict, Any, Optional
from functools import wraps
from datetime import datetime

try:
    from prometheus_client import Counter, Histogram, Gauge, Info
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

logger = logging.getLogger(__name__)


# Prometheus Metrics (if available)
if PROMETHEUS_AVAILABLE:
    # Request metrics
    http_requests_total = Counter(
        'pr_agent_http_requests_total',
        'Total HTTP requests',
        ['method', 'endpoint', 'status']
    )

    http_request_duration_seconds = Histogram(
        'pr_agent_http_request_duration_seconds',
        'HTTP request duration in seconds',
        ['method', 'endpoint']
    )

    # PR processing metrics
    pr_reviews_total = Counter(
        'pr_agent_reviews_total',
        'Total PR reviews processed',
        ['repository', 'status']
    )

    pr_review_duration_seconds = Histogram(
        'pr_agent_review_duration_seconds',
        'PR review processing duration in seconds',
        ['repository']
    )

    # Polling metrics
    polling_cycles_total = Counter(
        'pr_agent_polling_cycles_total',
        'Total polling cycles executed',
        ['repository']
    )

    polling_errors_total = Counter(
        'pr_agent_polling_errors_total',
        'Total polling errors',
        ['repository', 'error_type']
    )

    # System metrics
    active_reviews = Gauge(
        'pr_agent_active_reviews',
        'Number of reviews currently in progress'
    )

    cache_size_bytes = Gauge(
        'pr_agent_cache_size_bytes',
        'Size of various caches in bytes',
        ['cache_type']
    )

    # Application info
    app_info = Info(
        'pr_agent_app',
        'Application information'
    )


class MetricsCollector:
    """Collects and exports metrics for monitoring."""

    def __init__(self):
        self.enabled = PROMETHEUS_AVAILABLE
        if self.enabled:
            app_info.info({
                'version': '1.0.0',
                'component': 'pr-agent-auto-review'
            })

    def track_http_request(self, method: str, endpoint: str, status: int, duration: float):
        """Track HTTP request metrics."""
        if not self.enabled:
            return

        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status)
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    def track_pr_review(self, repository: str, status: str, duration: float):
        """Track PR review metrics."""
        if not self.enabled:
            return

        pr_reviews_total.labels(
            repository=repository,
            status=status
        ).inc()

        pr_review_duration_seconds.labels(
            repository=repository
        ).observe(duration)

    def track_polling_cycle(self, repository: str, success: bool, error_type: Optional[str] = None):
        """Track polling cycle metrics."""
        if not self.enabled:
            return

        polling_cycles_total.labels(repository=repository).inc()

        if not success and error_type:
            polling_errors_total.labels(
                repository=repository,
                error_type=error_type
            ).inc()

    def set_active_reviews(self, count: int):
        """Set number of active reviews."""
        if not self.enabled:
            return
        active_reviews.set(count)

    def set_cache_size(self, cache_type: str, size_bytes: int):
        """Set cache size metric."""
        if not self.enabled:
            return
        cache_size_bytes.labels(cache_type=cache_type).set(size_bytes)


# Global metrics collector instance
metrics = MetricsCollector()


class StructuredLogger:
    """Structured logging with context."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context: Dict[str, Any] = {}

    def set_context(self, **kwargs):
        """Set logging context."""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear logging context."""
        self.context.clear()

    def _format_message(self, message: str, extra: Optional[Dict] = None) -> str:
        """Format message with context."""
        ctx = {**self.context}
        if extra:
            ctx.update(extra)

        if ctx:
            ctx_str = ' '.join(f'{k}={v}' for k, v in ctx.items())
            return f"{message} | {ctx_str}"
        return message

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(self._format_message(message, kwargs))

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(self._format_message(message, kwargs))

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(self._format_message(message, kwargs))

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(self._format_message(message, kwargs))


def track_performance(metric_name: str, labels: Optional[Dict[str, str]] = None):
    """Decorator to track function performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Log performance
                logger.debug(
                    f"Function {func.__name__} completed",
                    extra={
                        'metric': metric_name,
                        'duration': duration,
                        'labels': labels or {}
                    }
                )

                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(
                    f"Function {func.__name__} failed",
                    extra={
                        'metric': metric_name,
                        'duration': duration,
                        'error': str(e),
                        'labels': labels or {}
                    }
                )
                raise

        return wrapper
    return decorator


class PerformanceTracker:
    """Track performance of operations."""

    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = None
        self.end_time = None
        self.metadata: Dict[str, Any] = {}

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time

        if exc_type is None:
            logger.info(
                f"Operation completed: {self.operation}",
                extra={
                    'duration': duration,
                    'metadata': self.metadata
                }
            )
        else:
            logger.error(
                f"Operation failed: {self.operation}",
                extra={
                    'duration': duration,
                    'error': str(exc_val),
                    'metadata': self.metadata
                }
            )

    def add_metadata(self, **kwargs):
        """Add metadata to the tracker."""
        self.metadata.update(kwargs)

    @property
    def duration(self) -> Optional[float]:
        """Get operation duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        import psutil

        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_mb': memory.available / (1024 * 1024),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024 * 1024 * 1024),
            'timestamp': datetime.now().isoformat()
        }
    except ImportError:
        return {
            'error': 'psutil not installed',
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }
