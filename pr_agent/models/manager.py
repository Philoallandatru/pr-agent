"""
AI Model Management System

Provides centralized management for AI models including:
- Model registration and versioning
- Performance monitoring and metrics
- A/B testing support
- Hot-swapping capabilities
- Model health checks
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger(__name__)


class ModelStatus(str, Enum):
    """Model status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    TESTING = "testing"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class ModelType(str, Enum):
    """Model type enumeration"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    CLASSIFICATION = "classification"


@dataclass
class ModelMetrics:
    """Model performance metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens: int = 0
    total_latency: float = 0.0
    avg_latency: float = 0.0
    error_rate: float = 0.0
    last_used: Optional[str] = None

    def update(self, success: bool, tokens: int, latency: float):
        """Update metrics with new request data"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_tokens += tokens
        self.total_latency += latency
        self.avg_latency = self.total_latency / self.total_requests
        self.error_rate = self.failed_requests / self.total_requests if self.total_requests > 0 else 0.0
        self.last_used = datetime.now(timezone.utc).isoformat()


@dataclass
class ModelConfig:
    """Model configuration"""
    model_id: str
    name: str
    provider: str  # openai, anthropic, ollama, etc.
    model_type: ModelType
    version: str
    status: ModelStatus
    config: Dict[str, Any]
    created_at: str
    updated_at: str
    metrics: ModelMetrics
    tags: List[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['model_type'] = self.model_type.value
        data['status'] = self.status.value
        return data


class ABTest:
    """A/B testing configuration"""

    def __init__(self, test_id: str, models: List[str], traffic_split: Dict[str, float]):
        """
        Initialize A/B test

        Args:
            test_id: Unique test identifier
            models: List of model IDs to test
            traffic_split: Traffic distribution (model_id -> percentage)
        """
        self.test_id = test_id
        self.models = models
        self.traffic_split = traffic_split
        self.metrics: Dict[str, ModelMetrics] = {
            model_id: ModelMetrics() for model_id in models
        }
        self.created_at = datetime.now(timezone.utc).isoformat()

        # Validate traffic split
        total = sum(traffic_split.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"Traffic split must sum to 1.0, got {total}")

    def select_model(self, request_id: str) -> str:
        """Select model based on traffic split"""
        import random
        rand = random.random()
        cumulative = 0.0
        for model_id, percentage in self.traffic_split.items():
            cumulative += percentage
            if rand <= cumulative:
                return model_id
        return self.models[-1]  # Fallback

    def record_result(self, model_id: str, success: bool, tokens: int, latency: float):
        """Record test result"""
        if model_id in self.metrics:
            self.metrics[model_id].update(success, tokens, latency)

    def get_results(self) -> Dict[str, Dict]:
        """Get test results"""
        return {
            "test_id": self.test_id,
            "models": self.models,
            "traffic_split": self.traffic_split,
            "created_at": self.created_at,
            "metrics": {
                model_id: asdict(metrics)
                for model_id, metrics in self.metrics.items()
            }
        }


class ModelManager:
    """Centralized AI model management"""

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize model manager

        Args:
            config_dir: Directory for model configurations
        """
        self.config_dir = config_dir or Path("./models")
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.models: Dict[str, ModelConfig] = {}
        self.active_model: Optional[str] = None
        self.ab_tests: Dict[str, ABTest] = {}
        self.health_checks: Dict[str, Callable] = {}

        self._load_models()

    def _load_models(self):
        """Load models from config directory"""
        config_file = self.config_dir / "models.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    for model_data in data.get("models", []):
                        metrics_data = model_data.pop("metrics", {})
                        metrics = ModelMetrics(**metrics_data)
                        model_data["metrics"] = metrics
                        model_data["model_type"] = ModelType(model_data["model_type"])
                        model_data["status"] = ModelStatus(model_data["status"])
                        model = ModelConfig(**model_data)
                        self.models[model.model_id] = model
                    self.active_model = data.get("active_model")
                logger.info(f"Loaded {len(self.models)} models from config")
            except Exception as e:
                logger.error(f"Failed to load models: {e}")

    def _save_models(self):
        """Save models to config directory"""
        config_file = self.config_dir / "models.json"
        try:
            data = {
                "models": [model.to_dict() for model in self.models.values()],
                "active_model": self.active_model
            }
            with open(config_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.models)} models to config")
        except Exception as e:
            logger.error(f"Failed to save models: {e}")

    def register_model(
        self,
        model_id: str,
        name: str,
        provider: str,
        model_type: ModelType,
        version: str,
        config: Dict[str, Any],
        tags: Optional[List[str]] = None
    ) -> ModelConfig:
        """
        Register a new model

        Args:
            model_id: Unique model identifier
            name: Human-readable name
            provider: Model provider
            model_type: Type of model
            version: Model version
            config: Model configuration
            tags: Optional tags

        Returns:
            ModelConfig: Registered model configuration
        """
        if model_id in self.models:
            raise ValueError(f"Model {model_id} already registered")

        now = datetime.now(timezone.utc).isoformat()
        model = ModelConfig(
            model_id=model_id,
            name=name,
            provider=provider,
            model_type=model_type,
            version=version,
            status=ModelStatus.INACTIVE,
            config=config,
            created_at=now,
            updated_at=now,
            metrics=ModelMetrics(),
            tags=tags or []
        )

        self.models[model_id] = model
        self._save_models()
        logger.info(f"Registered model: {model_id}")
        return model

    def update_model(self, model_id: str, **kwargs) -> ModelConfig:
        """Update model configuration"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        model = self.models[model_id]
        for key, value in kwargs.items():
            if hasattr(model, key) and key not in ['model_id', 'created_at', 'metrics']:
                setattr(model, key, value)

        model.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_models()
        logger.info(f"Updated model: {model_id}")
        return model

    def delete_model(self, model_id: str):
        """Delete a model"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        if self.active_model == model_id:
            self.active_model = None

        del self.models[model_id]
        self._save_models()
        logger.info(f"Deleted model: {model_id}")

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get model by ID"""
        return self.models.get(model_id)

    def list_models(
        self,
        status: Optional[ModelStatus] = None,
        model_type: Optional[ModelType] = None,
        provider: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[ModelConfig]:
        """
        List models with optional filtering

        Args:
            status: Filter by status
            model_type: Filter by type
            provider: Filter by provider
            tags: Filter by tags (any match)

        Returns:
            List of matching models
        """
        models = list(self.models.values())

        if status:
            models = [m for m in models if m.status == status]
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        if provider:
            models = [m for m in models if m.provider == provider]
        if tags:
            models = [m for m in models if any(tag in m.tags for tag in tags)]

        return models

    def set_active_model(self, model_id: str):
        """Set the active model"""
        if model_id not in self.models:
            raise ValueError(f"Model {model_id} not found")

        model = self.models[model_id]
        if model.status not in [ModelStatus.ACTIVE, ModelStatus.TESTING]:
            raise ValueError(f"Model {model_id} is not active or testing")

        old_model = self.active_model
        self.active_model = model_id
        model.status = ModelStatus.ACTIVE
        self._save_models()

        logger.info(f"Switched active model: {old_model} -> {model_id}")

    def get_active_model(self) -> Optional[ModelConfig]:
        """Get the currently active model"""
        if self.active_model:
            return self.models.get(self.active_model)
        return None

    def record_usage(self, model_id: str, success: bool, tokens: int, latency: float):
        """Record model usage metrics"""
        if model_id in self.models:
            self.models[model_id].metrics.update(success, tokens, latency)
            self._save_models()

    def get_metrics(self, model_id: str) -> Optional[ModelMetrics]:
        """Get model metrics"""
        model = self.models.get(model_id)
        return model.metrics if model else None

    def create_ab_test(
        self,
        test_id: str,
        models: List[str],
        traffic_split: Dict[str, float]
    ) -> ABTest:
        """
        Create an A/B test

        Args:
            test_id: Unique test identifier
            models: List of model IDs to test
            traffic_split: Traffic distribution

        Returns:
            ABTest: Created test
        """
        # Validate models exist
        for model_id in models:
            if model_id not in self.models:
                raise ValueError(f"Model {model_id} not found")

        test = ABTest(test_id, models, traffic_split)
        self.ab_tests[test_id] = test

        # Set models to testing status
        for model_id in models:
            self.models[model_id].status = ModelStatus.TESTING

        self._save_models()
        logger.info(f"Created A/B test: {test_id}")
        return test

    def get_ab_test(self, test_id: str) -> Optional[ABTest]:
        """Get A/B test by ID"""
        return self.ab_tests.get(test_id)

    def end_ab_test(self, test_id: str, winner_model_id: Optional[str] = None):
        """
        End an A/B test

        Args:
            test_id: Test identifier
            winner_model_id: Optional winner to set as active
        """
        if test_id not in self.ab_tests:
            raise ValueError(f"A/B test {test_id} not found")

        test = self.ab_tests[test_id]

        # Set winner as active first (while still in TESTING status)
        if winner_model_id:
            if winner_model_id not in test.models:
                raise ValueError(f"Winner {winner_model_id} not in test")
            self.set_active_model(winner_model_id)

        # Reset other model statuses
        for model_id in test.models:
            if model_id in self.models and model_id != winner_model_id:
                self.models[model_id].status = ModelStatus.INACTIVE

        del self.ab_tests[test_id]
        self._save_models()
        logger.info(f"Ended A/B test: {test_id}, winner: {winner_model_id}")

    def register_health_check(self, model_id: str, check_func: Callable):
        """Register a health check function for a model"""
        self.health_checks[model_id] = check_func

    async def check_health(self, model_id: str) -> Dict[str, Any]:
        """
        Check model health

        Returns:
            Health status dictionary
        """
        if model_id not in self.models:
            return {"status": "error", "message": "Model not found"}

        model = self.models[model_id]
        result = {
            "model_id": model_id,
            "status": model.status.value,
            "metrics": asdict(model.metrics),
            "healthy": True,
            "checks": {}
        }

        # Run custom health check if registered
        if model_id in self.health_checks:
            try:
                check_result = await self.health_checks[model_id]()
                result["checks"]["custom"] = check_result
                if not check_result.get("healthy", True):
                    result["healthy"] = False
            except Exception as e:
                result["checks"]["custom"] = {"healthy": False, "error": str(e)}
                result["healthy"] = False

        # Check error rate
        if model.metrics.error_rate > 0.1:  # 10% threshold
            result["healthy"] = False
            result["checks"]["error_rate"] = {
                "healthy": False,
                "value": model.metrics.error_rate,
                "threshold": 0.1
            }

        # Update model status if unhealthy
        if not result["healthy"] and model.status == ModelStatus.ACTIVE:
            model.status = ModelStatus.FAILED
            self._save_models()
            logger.warning(f"Model {model_id} marked as failed due to health check")

        return result


# Global model manager instance
_model_manager: Optional[ModelManager] = None


def get_model_manager() -> ModelManager:
    """Get global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager()
    return _model_manager
