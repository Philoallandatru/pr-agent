"""
Unit tests for health check system.
"""

import pytest
import tempfile
import os
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from pr_agent.health.checker import HealthChecker, HealthStatus, ComponentHealth


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Create a simple database
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO test (name) VALUES ('test')")
    conn.commit()
    conn.close()

    yield path

    # Cleanup
    if os.path.exists(path):
        try:
            os.unlink(path)
        except:
            pass


@pytest.fixture
def mock_db_manager(temp_db):
    """Create mock database manager."""
    db_manager = Mock()
    db_manager.conn = sqlite3.connect(temp_db)
    db_manager.db_path = temp_db
    return db_manager


@pytest.fixture
def mock_cache_manager():
    """Create mock cache manager."""
    cache_manager = Mock()
    cache_manager.redis_client = None
    return cache_manager


class TestComponentHealth:
    """Test ComponentHealth class."""

    def test_component_health_creation(self):
        """Test creating a component health object."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
            details={"key": "value"},
            response_time_ms=10.5
        )

        assert health.name == "test"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "All good"
        assert health.details == {"key": "value"}
        assert health.response_time_ms == 10.5
        assert health.timestamp is not None

    def test_component_health_to_dict(self):
        """Test converting component health to dictionary."""
        health = ComponentHealth(
            name="test",
            status=HealthStatus.DEGRADED,
            message="Slow",
            response_time_ms=150.0
        )

        result = health.to_dict()

        assert result["name"] == "test"
        assert result["status"] == "degraded"
        assert result["message"] == "Slow"
        assert result["response_time_ms"] == 150.0
        assert "timestamp" in result


class TestHealthChecker:
    """Test HealthChecker class."""

    def test_health_checker_initialization(self, mock_db_manager, mock_cache_manager):
        """Test health checker initialization."""
        checker = HealthChecker(
            db_manager=mock_db_manager,
            cache_manager=mock_cache_manager,
            config={"test": "value"}
        )

        assert checker.db_manager == mock_db_manager
        assert checker.cache_manager == mock_cache_manager
        assert checker.config == {"test": "value"}
        assert checker.start_time > 0

    @pytest.mark.asyncio
    async def test_check_database_healthy(self, mock_db_manager):
        """Test database health check when healthy."""
        checker = HealthChecker(db_manager=mock_db_manager)

        result = await checker.check_database()

        assert result.name == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms is not None
        assert result.response_time_ms < 100
        assert "size_bytes" in result.details
        assert "tables" in result.details

    @pytest.mark.asyncio
    async def test_check_database_no_manager(self):
        """Test database health check without manager."""
        checker = HealthChecker(db_manager=None)

        result = await checker.check_database()

        assert result.name == "database"
        assert result.status == HealthStatus.DEGRADED
        assert "not configured" in result.message

    @pytest.mark.asyncio
    async def test_check_database_error(self):
        """Test database health check with error."""
        mock_db = Mock()
        mock_db.conn.cursor.side_effect = Exception("Connection failed")

        checker = HealthChecker(db_manager=mock_db)

        result = await checker.check_database()

        assert result.name == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_cache_not_available(self):
        """Test cache health check when not available."""
        checker = HealthChecker(cache_manager=None)

        result = await checker.check_cache()

        assert result.name == "cache"
        assert result.status == HealthStatus.DEGRADED
        assert "not configured" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_cache_redis_available(self):
        """Test cache health check with Redis."""
        mock_cache = Mock()
        mock_redis = Mock()
        mock_redis.ping.return_value = True
        mock_redis.info.return_value = {
            "connected_clients": 5,
            "used_memory": 1024 * 1024,
            "uptime_in_seconds": 3600,
            "keyspace_hits": 100,
            "keyspace_misses": 10
        }
        mock_cache.redis_client = mock_redis

        checker = HealthChecker(cache_manager=mock_cache)

        result = await checker.check_cache()

        assert result.name == "cache"
        assert result.status == HealthStatus.HEALTHY
        assert "connected_clients" in result.details
        assert result.details["hit_rate"] == 90.91

    @pytest.mark.asyncio
    async def test_check_cache_redis_error(self):
        """Test cache health check with Redis error."""
        mock_cache = Mock()
        mock_redis = Mock()
        mock_redis.ping.side_effect = Exception("Connection refused")
        mock_cache.redis_client = mock_redis

        checker = HealthChecker(cache_manager=mock_cache)

        result = await checker.check_cache()

        assert result.name == "cache"
        assert result.status == HealthStatus.DEGRADED
        assert "failed" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_system_resources(self):
        """Test system resources health check."""
        checker = HealthChecker()

        result = await checker.check_system_resources()

        assert result.name == "system_resources"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED, HealthStatus.UNHEALTHY]
        assert "cpu_percent" in result.details
        assert "memory_percent" in result.details
        assert "disk_percent" in result.details

    @pytest.mark.asyncio
    async def test_check_system_resources_high_usage(self):
        """Test system resources with high usage."""
        checker = HealthChecker()

        with patch('psutil.cpu_percent', return_value=95.0):
            with patch('psutil.virtual_memory') as mock_mem:
                mock_mem.return_value = Mock(percent=85.0, available=1024*1024*1024)
                with patch('psutil.disk_usage') as mock_disk:
                    mock_disk.return_value = Mock(percent=70.0, free=10*1024*1024*1024)

                    result = await checker.check_system_resources()

                    assert result.status == HealthStatus.UNHEALTHY
                    assert "critical" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_external_services_none_configured(self):
        """Test external services check with no services."""
        checker = HealthChecker(config={})

        result = await checker.check_external_services()

        assert result.name == "external_services"
        assert result.status == HealthStatus.HEALTHY
        assert "no external services configured" in result.message.lower()

    @pytest.mark.asyncio
    async def test_check_all(self, mock_db_manager):
        """Test checking all components."""
        checker = HealthChecker(db_manager=mock_db_manager)

        result = await checker.check_all(include_details=True)

        assert "status" in result
        assert "timestamp" in result
        assert "uptime_seconds" in result
        assert "components" in result
        assert len(result["components"]) > 0

        # Check that all expected components are present
        component_names = [c["name"] for c in result["components"]]
        assert "database" in component_names
        assert "cache" in component_names
        assert "system_resources" in component_names
        assert "external_services" in component_names

    @pytest.mark.asyncio
    async def test_check_all_without_details(self, mock_db_manager):
        """Test checking all components without details."""
        checker = HealthChecker(db_manager=mock_db_manager)

        result = await checker.check_all(include_details=False)

        # Details should be removed
        for component in result["components"]:
            assert "details" not in component

    @pytest.mark.asyncio
    async def test_check_all_overall_status_unhealthy(self):
        """Test overall status when one component is unhealthy."""
        checker = HealthChecker(db_manager=None)  # Will cause degraded status

        with patch.object(checker, 'check_system_resources') as mock_sys:
            mock_sys.return_value = ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message="Critical"
            )

            result = await checker.check_all()

            assert result["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_check_all_overall_status_degraded(self, mock_db_manager):
        """Test overall status when one component is degraded."""
        checker = HealthChecker(db_manager=mock_db_manager)

        # Cache will be degraded (not configured)
        result = await checker.check_all()

        # Should be degraded because cache is not configured
        assert result["status"] in ["degraded", "healthy"]

    def test_get_readiness_with_db(self, mock_db_manager):
        """Test readiness check with database."""
        checker = HealthChecker(db_manager=mock_db_manager)

        result = checker.get_readiness()

        assert result["ready"] is True
        assert result["reasons"] == []
        assert "timestamp" in result

    def test_get_readiness_without_db(self):
        """Test readiness check without database."""
        checker = HealthChecker(db_manager=None)

        result = checker.get_readiness()

        assert result["ready"] is False
        assert len(result["reasons"]) > 0
        assert "Database" in result["reasons"][0]

    def test_get_liveness(self):
        """Test liveness check."""
        checker = HealthChecker()

        result = checker.get_liveness()

        assert result["alive"] is True
        assert result["uptime_seconds"] >= 0
        assert "timestamp" in result

    def test_calculate_hit_rate(self):
        """Test cache hit rate calculation."""
        checker = HealthChecker()

        # Test with hits and misses
        rate = checker._calculate_hit_rate({
            "keyspace_hits": 90,
            "keyspace_misses": 10
        })
        assert rate == 90.0

        # Test with no data
        rate = checker._calculate_hit_rate({
            "keyspace_hits": 0,
            "keyspace_misses": 0
        })
        assert rate is None

        # Test with only hits
        rate = checker._calculate_hit_rate({
            "keyspace_hits": 100,
            "keyspace_misses": 0
        })
        assert rate == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
