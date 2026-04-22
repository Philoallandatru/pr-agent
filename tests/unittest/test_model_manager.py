"""
Unit tests for AI Model Management System
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from pr_agent.models import (
    ModelManager,
    ModelConfig,
    ModelMetrics,
    ModelStatus,
    ModelType,
    ABTest,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield Path(temp)
    shutil.rmtree(temp)


@pytest.fixture
def manager(temp_dir):
    """Create model manager instance"""
    return ModelManager(config_dir=temp_dir)


class TestModelManager:
    """Test ModelManager class"""

    def test_register_model(self, manager):
        """Test registering a new model"""
        model = manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={"temperature": 0.7},
            tags=["production"]
        )

        assert model.model_id == "gpt-4"
        assert model.name == "GPT-4"
        assert model.provider == "openai"
        assert model.status == ModelStatus.INACTIVE
        assert "production" in model.tags

    def test_register_duplicate_model(self, manager):
        """Test registering duplicate model raises error"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        with pytest.raises(ValueError, match="already registered"):
            manager.register_model(
                model_id="gpt-4",
                name="GPT-4",
                provider="openai",
                model_type=ModelType.CHAT,
                version="1.0",
                config={}
            )

    def test_update_model(self, manager):
        """Test updating model configuration"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        updated = manager.update_model("gpt-4", name="GPT-4 Turbo", version="2.0")
        assert updated.name == "GPT-4 Turbo"
        assert updated.version == "2.0"

    def test_update_nonexistent_model(self, manager):
        """Test updating nonexistent model raises error"""
        with pytest.raises(ValueError, match="not found"):
            manager.update_model("nonexistent", name="Test")

    def test_delete_model(self, manager):
        """Test deleting a model"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        manager.delete_model("gpt-4")
        assert manager.get_model("gpt-4") is None

    def test_delete_active_model(self, manager):
        """Test deleting active model clears active_model"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.update_model("gpt-4", status=ModelStatus.ACTIVE)
        manager.set_active_model("gpt-4")

        manager.delete_model("gpt-4")
        assert manager.active_model is None

    def test_get_model(self, manager):
        """Test getting model by ID"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        model = manager.get_model("gpt-4")
        assert model is not None
        assert model.model_id == "gpt-4"

    def test_list_models(self, manager):
        """Test listing all models"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.register_model(
            model_id="claude-3",
            name="Claude 3",
            provider="anthropic",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        models = manager.list_models()
        assert len(models) == 2

    def test_list_models_with_filters(self, manager):
        """Test listing models with filters"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={},
            tags=["production"]
        )
        manager.register_model(
            model_id="claude-3",
            name="Claude 3",
            provider="anthropic",
            model_type=ModelType.CHAT,
            version="1.0",
            config={},
            tags=["testing"]
        )

        # Filter by provider
        models = manager.list_models(provider="openai")
        assert len(models) == 1
        assert models[0].model_id == "gpt-4"

        # Filter by tags
        models = manager.list_models(tags=["production"])
        assert len(models) == 1
        assert models[0].model_id == "gpt-4"

    def test_set_active_model(self, manager):
        """Test setting active model"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.update_model("gpt-4", status=ModelStatus.ACTIVE)

        manager.set_active_model("gpt-4")
        assert manager.active_model == "gpt-4"
        assert manager.get_active_model().model_id == "gpt-4"

    def test_set_active_model_invalid_status(self, manager):
        """Test setting inactive model as active raises error"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        with pytest.raises(ValueError, match="not active or testing"):
            manager.set_active_model("gpt-4")

    def test_record_usage(self, manager):
        """Test recording model usage"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        manager.record_usage("gpt-4", success=True, tokens=100, latency=1.5)

        metrics = manager.get_metrics("gpt-4")
        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.total_tokens == 100
        assert metrics.avg_latency == 1.5

    def test_get_metrics(self, manager):
        """Test getting model metrics"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        metrics = manager.get_metrics("gpt-4")
        assert metrics is not None
        assert metrics.total_requests == 0

    def test_persistence(self, temp_dir):
        """Test model persistence across instances"""
        # Create first manager and register model
        manager1 = ModelManager(config_dir=temp_dir)
        manager1.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        # Create second manager and verify model exists
        manager2 = ModelManager(config_dir=temp_dir)
        model = manager2.get_model("gpt-4")
        assert model is not None
        assert model.name == "GPT-4"


class TestABTest:
    """Test A/B testing functionality"""

    def test_create_ab_test(self, manager):
        """Test creating an A/B test"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.register_model(
            model_id="claude-3",
            name="Claude 3",
            provider="anthropic",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        test = manager.create_ab_test(
            test_id="test-1",
            models=["gpt-4", "claude-3"],
            traffic_split={"gpt-4": 0.5, "claude-3": 0.5}
        )

        assert test.test_id == "test-1"
        assert len(test.models) == 2
        assert manager.models["gpt-4"].status == ModelStatus.TESTING

    def test_ab_test_invalid_traffic_split(self, manager):
        """Test A/B test with invalid traffic split"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.register_model(
            model_id="claude-3",
            name="Claude 3",
            provider="anthropic",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        with pytest.raises(ValueError, match="must sum to 1.0"):
            manager.create_ab_test(
                test_id="test-1",
                models=["gpt-4", "claude-3"],
                traffic_split={"gpt-4": 0.6, "claude-3": 0.6}
            )

    def test_ab_test_select_model(self, manager):
        """Test model selection in A/B test"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.register_model(
            model_id="claude-3",
            name="Claude 3",
            provider="anthropic",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        test = manager.create_ab_test(
            test_id="test-1",
            models=["gpt-4", "claude-3"],
            traffic_split={"gpt-4": 0.5, "claude-3": 0.5}
        )

        # Select model multiple times
        selections = [test.select_model(f"req-{i}") for i in range(100)]
        assert "gpt-4" in selections
        assert "claude-3" in selections

    def test_ab_test_record_result(self, manager):
        """Test recording A/B test results"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.register_model(
            model_id="claude-3",
            name="Claude 3",
            provider="anthropic",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        test = manager.create_ab_test(
            test_id="test-1",
            models=["gpt-4", "claude-3"],
            traffic_split={"gpt-4": 0.5, "claude-3": 0.5}
        )

        test.record_result("gpt-4", success=True, tokens=100, latency=1.5)

        results = test.get_results()
        assert results["metrics"]["gpt-4"]["total_requests"] == 1

    def test_end_ab_test(self, manager):
        """Test ending an A/B test"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.register_model(
            model_id="claude-3",
            name="Claude 3",
            provider="anthropic",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        manager.create_ab_test(
            test_id="test-1",
            models=["gpt-4", "claude-3"],
            traffic_split={"gpt-4": 0.5, "claude-3": 0.5}
        )

        manager.end_ab_test("test-1", winner_model_id="gpt-4")

        assert manager.active_model == "gpt-4"
        assert manager.get_ab_test("test-1") is None


class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_basic(self, manager):
        """Test basic health check"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        result = await manager.check_health("gpt-4")
        assert result["model_id"] == "gpt-4"
        assert result["healthy"] is True

    @pytest.mark.asyncio
    async def test_health_check_with_custom_check(self, manager):
        """Test health check with custom check function"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )

        async def custom_check():
            return {"healthy": True, "latency": 0.5}

        manager.register_health_check("gpt-4", custom_check)

        result = await manager.check_health("gpt-4")
        assert result["healthy"] is True
        assert result["checks"]["custom"]["latency"] == 0.5

    @pytest.mark.asyncio
    async def test_health_check_high_error_rate(self, manager):
        """Test health check detects high error rate"""
        manager.register_model(
            model_id="gpt-4",
            name="GPT-4",
            provider="openai",
            model_type=ModelType.CHAT,
            version="1.0",
            config={}
        )
        manager.update_model("gpt-4", status=ModelStatus.ACTIVE)

        # Record failures to increase error rate
        for _ in range(20):
            manager.record_usage("gpt-4", success=False, tokens=0, latency=0)

        result = await manager.check_health("gpt-4")
        assert result["healthy"] is False
        assert manager.models["gpt-4"].status == ModelStatus.FAILED


class TestModelMetrics:
    """Test ModelMetrics class"""

    def test_metrics_update(self):
        """Test updating metrics"""
        metrics = ModelMetrics()
        metrics.update(success=True, tokens=100, latency=1.5)

        assert metrics.total_requests == 1
        assert metrics.successful_requests == 1
        assert metrics.total_tokens == 100
        assert metrics.avg_latency == 1.5
        assert metrics.error_rate == 0.0

    def test_metrics_error_rate(self):
        """Test error rate calculation"""
        metrics = ModelMetrics()
        metrics.update(success=True, tokens=100, latency=1.0)
        metrics.update(success=False, tokens=0, latency=0.5)

        assert metrics.total_requests == 2
        assert metrics.error_rate == 0.5
