"""
Health check system for monitoring service status and dependencies.

This module provides comprehensive health checks for all system components
including database, cache, external services, and system resources.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
import psutil
import aiohttp

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class HealthStatus(str, Enum):
    """Health check status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth:
    """Health status for a single component."""

    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[float] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time_ms = response_time_ms
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp
        }
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        if self.response_time_ms is not None:
            result["response_time_ms"] = round(self.response_time_ms, 2)
        return result


class HealthChecker:
    """
    Comprehensive health checker for all system components.

    Checks:
    - Database connectivity and performance
    - Redis cache availability
    - External service connectivity (Bitbucket, webhooks)
    - System resources (CPU, memory, disk)
    - Application metrics
    """

    def __init__(
        self,
        db_manager=None,
        cache_manager=None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize health checker.

        Args:
            db_manager: Database manager instance
            cache_manager: Cache manager instance
            config: Configuration dictionary
        """
        self.db_manager = db_manager
        self.cache_manager = cache_manager
        self.config = config or {}
        self.start_time = time.time()

    async def check_all(self, include_details: bool = True) -> Dict[str, Any]:
        """
        Run all health checks.

        Args:
            include_details: Include detailed information in response

        Returns:
            Dictionary with overall health status and component details
        """
        checks = await asyncio.gather(
            self.check_database(),
            self.check_cache(),
            self.check_system_resources(),
            self.check_external_services(),
            return_exceptions=True
        )

        components = []
        for check in checks:
            if isinstance(check, ComponentHealth):
                components.append(check)
            elif isinstance(check, Exception):
                components.append(ComponentHealth(
                    name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(check)}"
                ))

        # Determine overall status
        statuses = [c.status for c in components]
        if any(s == HealthStatus.UNHEALTHY for s in statuses):
            overall_status = HealthStatus.UNHEALTHY
        elif any(s == HealthStatus.DEGRADED for s in statuses):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        result = {
            "status": overall_status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": int(time.time() - self.start_time),
            "components": [c.to_dict() for c in components]
        }

        if not include_details:
            # Remove detailed information for lightweight checks
            for component in result["components"]:
                component.pop("details", None)

        return result

    async def check_database(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        if not self.db_manager:
            return ComponentHealth(
                name="database",
                status=HealthStatus.DEGRADED,
                message="Database manager not configured"
            )

        start = time.time()
        try:
            # Simple query to check connectivity
            cursor = self.db_manager.conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()

            response_time = (time.time() - start) * 1000

            # Check database size
            cursor.execute("""
                SELECT page_count * page_size as size
                FROM pragma_page_count(), pragma_page_size()
            """)
            db_size = cursor.fetchone()[0]

            # Check table counts
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]

            details = {
                "size_bytes": db_size,
                "size_mb": round(db_size / 1024 / 1024, 2),
                "tables": len(tables)
            }

            # Determine status based on response time
            if response_time < 100:
                status = HealthStatus.HEALTHY
                message = "Database is healthy"
            elif response_time < 500:
                status = HealthStatus.DEGRADED
                message = "Database response time is slow"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Database response time is critical"

            return ComponentHealth(
                name="database",
                status=status,
                message=message,
                details=details,
                response_time_ms=response_time
            )

        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database check failed: {str(e)}",
                response_time_ms=(time.time() - start) * 1000
            )

    async def check_cache(self) -> ComponentHealth:
        """Check Redis cache availability."""
        if not REDIS_AVAILABLE or not self.cache_manager:
            return ComponentHealth(
                name="cache",
                status=HealthStatus.DEGRADED,
                message="Cache not configured or Redis not available"
            )

        start = time.time()
        try:
            # Try to ping Redis
            if hasattr(self.cache_manager, 'redis_client'):
                self.cache_manager.redis_client.ping()

                # Get Redis info
                info = self.cache_manager.redis_client.info()

                response_time = (time.time() - start) * 1000

                details = {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
                    "uptime_seconds": info.get("uptime_in_seconds", 0),
                    "hit_rate": self._calculate_hit_rate(info)
                }

                return ComponentHealth(
                    name="cache",
                    status=HealthStatus.HEALTHY,
                    message="Cache is healthy",
                    details=details,
                    response_time_ms=response_time
                )
            else:
                # Fallback to memory cache
                return ComponentHealth(
                    name="cache",
                    status=HealthStatus.DEGRADED,
                    message="Using in-memory cache (Redis unavailable)",
                    details={"backend": "memory"}
                )

        except Exception as e:
            return ComponentHealth(
                name="cache",
                status=HealthStatus.DEGRADED,
                message=f"Cache check failed, using fallback: {str(e)}",
                response_time_ms=(time.time() - start) * 1000
            )

    async def check_system_resources(self) -> ComponentHealth:
        """Check system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            details = {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_available_mb": round(memory.available / 1024 / 1024, 2),
                "disk_percent": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2)
            }

            # Determine status based on resource usage
            if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Critical resource usage"
            elif cpu_percent > 75 or memory.percent > 75 or disk.percent > 80:
                status = HealthStatus.DEGRADED
                message = "High resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "System resources are healthy"

            return ComponentHealth(
                name="system_resources",
                status=status,
                message=message,
                details=details
            )

        except Exception as e:
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.DEGRADED,
                message=f"Resource check failed: {str(e)}"
            )

    async def check_external_services(self) -> ComponentHealth:
        """Check connectivity to external services."""
        services_status = []

        # Check Bitbucket Server
        bitbucket_url = self.config.get("bitbucket_server", {}).get("url")
        if bitbucket_url:
            bitbucket_health = await self._check_http_endpoint(
                "bitbucket",
                f"{bitbucket_url}/status"
            )
            services_status.append(bitbucket_health)

        # Determine overall external services status
        if not services_status:
            return ComponentHealth(
                name="external_services",
                status=HealthStatus.HEALTHY,
                message="No external services configured"
            )

        unhealthy = sum(1 for s in services_status if s["status"] == "unhealthy")
        degraded = sum(1 for s in services_status if s["status"] == "degraded")

        if unhealthy > 0:
            status = HealthStatus.UNHEALTHY
            message = f"{unhealthy} service(s) unreachable"
        elif degraded > 0:
            status = HealthStatus.DEGRADED
            message = f"{degraded} service(s) slow"
        else:
            status = HealthStatus.HEALTHY
            message = "All external services are healthy"

        return ComponentHealth(
            name="external_services",
            status=status,
            message=message,
            details={"services": services_status}
        )

    async def _check_http_endpoint(
        self,
        name: str,
        url: str,
        timeout: int = 5
    ) -> Dict[str, Any]:
        """Check HTTP endpoint availability."""
        start = time.time()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    response_time = (time.time() - start) * 1000

                    if response.status == 200:
                        status = "healthy"
                    elif response.status < 500:
                        status = "degraded"
                    else:
                        status = "unhealthy"

                    return {
                        "name": name,
                        "status": status,
                        "response_time_ms": round(response_time, 2),
                        "status_code": response.status
                    }

        except asyncio.TimeoutError:
            return {
                "name": name,
                "status": "unhealthy",
                "error": "Timeout",
                "response_time_ms": timeout * 1000
            }
        except Exception as e:
            return {
                "name": name,
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": (time.time() - start) * 1000
            }

    def _calculate_hit_rate(self, redis_info: Dict[str, Any]) -> Optional[float]:
        """Calculate cache hit rate from Redis info."""
        hits = redis_info.get("keyspace_hits", 0)
        misses = redis_info.get("keyspace_misses", 0)
        total = hits + misses

        if total == 0:
            return None

        return round((hits / total) * 100, 2)

    def get_readiness(self) -> Dict[str, Any]:
        """
        Get readiness status (can the service handle requests?).

        Returns:
            Dictionary with readiness status
        """
        # Service is ready if critical components are available
        ready = True
        reasons = []

        if not self.db_manager:
            ready = False
            reasons.append("Database not initialized")

        return {
            "ready": ready,
            "reasons": reasons,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_liveness(self) -> Dict[str, Any]:
        """
        Get liveness status (is the service running?).

        Returns:
            Dictionary with liveness status
        """
        return {
            "alive": True,
            "uptime_seconds": int(time.time() - self.start_time),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
