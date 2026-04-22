# AI Model Management Guide

Complete guide for managing AI models in PR-Agent.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Model Registration](#model-registration)
- [Model Configuration](#model-configuration)
- [Performance Monitoring](#performance-monitoring)
- [A/B Testing](#ab-testing)
- [Health Checks](#health-checks)
- [API Reference](#api-reference)
- [Best Practices](#best-practices)

## Overview

The AI Model Management system provides centralized control over AI models used in PR-Agent, including:

- **Model Registry**: Register and manage multiple AI models
- **Version Control**: Track model versions and configurations
- **Performance Monitoring**: Real-time metrics and analytics
- **A/B Testing**: Compare models with traffic splitting
- **Health Checks**: Automated model health monitoring
- **Hot-Swapping**: Switch models without downtime

## Features

### Model Registry

- Register models from multiple providers (OpenAI, Anthropic, Ollama, etc.)
- Version tracking and configuration management
- Tag-based organization
- Status management (active, inactive, testing, deprecated, failed)

### Performance Monitoring

- Request count and success rate
- Token usage tracking
- Latency measurements
- Error rate monitoring
- Last used timestamp

### A/B Testing

- Traffic splitting between models
- Per-model metrics collection
- Statistical comparison
- Winner selection

### Health Checks

- Automated health monitoring
- Custom health check functions
- Error rate thresholds
- Automatic failover

## Model Registration

### Register a Model

```python
from pr_agent.models import get_model_manager, ModelType

manager = get_model_manager()

model = manager.register_model(
    model_id="gpt-4-turbo",
    name="GPT-4 Turbo",
    provider="openai",
    model_type=ModelType.CHAT,
    version="2024-01",
    config={
        "temperature": 0.7,
        "max_tokens": 4096,
        "api_key_env": "OPENAI_API_KEY"
    },
    tags=["production", "fast"]
)
```

### Via API

```bash
curl -X POST http://localhost:8080/api/models \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "gpt-4-turbo",
    "name": "GPT-4 Turbo",
    "provider": "openai",
    "model_type": "chat",
    "version": "2024-01",
    "config": {
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "tags": ["production"]
  }'
```

## Model Configuration

### Model Types

```python
class ModelType(str, Enum):
    CHAT = "chat"              # Chat completion models
    COMPLETION = "completion"  # Text completion models
    EMBEDDING = "embedding"    # Embedding models
    CLASSIFICATION = "classification"  # Classification models
```

### Model Status

```python
class ModelStatus(str, Enum):
    ACTIVE = "active"          # Currently active
    INACTIVE = "inactive"      # Registered but not active
    TESTING = "testing"        # In A/B test
    DEPRECATED = "deprecated"  # Deprecated, should not use
    FAILED = "failed"          # Failed health check
```

### Update Model

```python
manager.update_model(
    "gpt-4-turbo",
    name="GPT-4 Turbo (Updated)",
    config={"temperature": 0.5},
    tags=["production", "optimized"]
)
```

### Set Active Model

```python
# Model must be in ACTIVE or TESTING status
manager.update_model("gpt-4-turbo", status=ModelStatus.ACTIVE)
manager.set_active_model("gpt-4-turbo")
```

## Performance Monitoring

### Record Usage

```python
# Record successful request
manager.record_usage(
    model_id="gpt-4-turbo",
    success=True,
    tokens=150,
    latency=1.2  # seconds
)

# Record failed request
manager.record_usage(
    model_id="gpt-4-turbo",
    success=False,
    tokens=0,
    latency=0.5
)
```

### Get Metrics

```python
metrics = manager.get_metrics("gpt-4-turbo")

print(f"Total requests: {metrics.total_requests}")
print(f"Success rate: {(1 - metrics.error_rate) * 100}%")
print(f"Average latency: {metrics.avg_latency}s")
print(f"Total tokens: {metrics.total_tokens}")
```

### Via API

```bash
curl http://localhost:8080/api/models/gpt-4-turbo/metrics \
  -H "Authorization: Bearer $TOKEN"
```

Response:
```json
{
  "total_requests": 1000,
  "successful_requests": 980,
  "failed_requests": 20,
  "total_tokens": 150000,
  "total_latency": 1200.5,
  "avg_latency": 1.2,
  "error_rate": 0.02,
  "last_used": "2024-01-15T10:30:00Z"
}
```

## A/B Testing

### Create A/B Test

```python
test = manager.create_ab_test(
    test_id="gpt4-vs-claude",
    models=["gpt-4-turbo", "claude-3-opus"],
    traffic_split={
        "gpt-4-turbo": 0.5,
        "claude-3-opus": 0.5
    }
)
```

### Select Model for Request

```python
test = manager.get_ab_test("gpt4-vs-claude")
model_id = test.select_model(request_id="req-123")

# Use selected model
# ... make API call ...

# Record result
test.record_result(
    model_id=model_id,
    success=True,
    tokens=100,
    latency=1.5
)
```

### Get Test Results

```python
test = manager.get_ab_test("gpt4-vs-claude")
results = test.get_results()

print(f"Test ID: {results['test_id']}")
print(f"Models: {results['models']}")
print(f"Traffic split: {results['traffic_split']}")

for model_id, metrics in results['metrics'].items():
    print(f"\n{model_id}:")
    print(f"  Requests: {metrics['total_requests']}")
    print(f"  Success rate: {(1 - metrics['error_rate']) * 100}%")
    print(f"  Avg latency: {metrics['avg_latency']}s")
```

### End A/B Test

```python
# End test and set winner as active
manager.end_ab_test("gpt4-vs-claude", winner_model_id="gpt-4-turbo")

# Or end without setting winner
manager.end_ab_test("gpt4-vs-claude")
```

### Via API

```bash
# Create test
curl -X POST http://localhost:8080/api/ab-tests \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "test_id": "gpt4-vs-claude",
    "models": ["gpt-4-turbo", "claude-3-opus"],
    "traffic_split": {
      "gpt-4-turbo": 0.5,
      "claude-3-opus": 0.5
    }
  }'

# Get results
curl http://localhost:8080/api/ab-tests/gpt4-vs-claude \
  -H "Authorization: Bearer $TOKEN"

# End test
curl -X POST http://localhost:8080/api/ab-tests/gpt4-vs-claude/end \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"winner_model_id": "gpt-4-turbo"}'
```

## Health Checks

### Basic Health Check

```python
health = await manager.check_health("gpt-4-turbo")

print(f"Model: {health['model_id']}")
print(f"Status: {health['status']}")
print(f"Healthy: {health['healthy']}")
print(f"Metrics: {health['metrics']}")
```

### Custom Health Check

```python
async def custom_health_check():
    """Custom health check function"""
    try:
        # Test API call
        response = await make_test_call()
        return {
            "healthy": response.status == 200,
            "latency": response.latency,
            "message": "API responding"
        }
    except Exception as e:
        return {
            "healthy": False,
            "error": str(e)
        }

# Register custom check
manager.register_health_check("gpt-4-turbo", custom_health_check)

# Run health check
health = await manager.check_health("gpt-4-turbo")
print(health['checks']['custom'])
```

### Automatic Failover

Models with error rate > 10% are automatically marked as FAILED:

```python
# Simulate failures
for _ in range(20):
    manager.record_usage("gpt-4-turbo", success=False, tokens=0, latency=0)

# Check health
health = await manager.check_health("gpt-4-turbo")
assert health['healthy'] == False
assert manager.get_model("gpt-4-turbo").status == ModelStatus.FAILED
```

## API Reference

### List Models

```
GET /api/models?status=active&model_type=chat&provider=openai
```

### Register Model

```
POST /api/models
Body: {model_id, name, provider, model_type, version, config, tags}
```

### Get Model

```
GET /api/models/{model_id}
```

### Update Model

```
PUT /api/models/{model_id}
Body: {name?, config?, status?, tags?}
```

### Delete Model

```
DELETE /api/models/{model_id}
```

### Activate Model

```
POST /api/models/{model_id}/activate
```

### Get Metrics

```
GET /api/models/{model_id}/metrics
```

### Check Health

```
GET /api/models/{model_id}/health
```

### Create A/B Test

```
POST /api/ab-tests
Body: {test_id, models, traffic_split}
```

### Get A/B Test

```
GET /api/ab-tests/{test_id}
```

### End A/B Test

```
POST /api/ab-tests/{test_id}/end
Body: {winner_model_id?}
```

## Best Practices

### 1. Model Versioning

Always include version information:

```python
manager.register_model(
    model_id="gpt-4-2024-01",  # Include date/version
    name="GPT-4 (January 2024)",
    version="2024-01",
    # ...
)
```

### 2. Gradual Rollout

Use A/B testing for gradual rollout:

```python
# Start with 10% traffic
test = manager.create_ab_test(
    test_id="new-model-rollout",
    models=["current-model", "new-model"],
    traffic_split={"current-model": 0.9, "new-model": 0.1}
)

# Monitor metrics, then increase traffic
# Eventually set new model as active
```

### 3. Monitor Error Rates

Set up alerts for high error rates:

```python
metrics = manager.get_metrics("gpt-4-turbo")
if metrics.error_rate > 0.05:  # 5% threshold
    # Send alert
    # Consider switching to backup model
    pass
```

### 4. Regular Health Checks

Schedule periodic health checks:

```python
import asyncio

async def periodic_health_check():
    while True:
        for model in manager.list_models(status=ModelStatus.ACTIVE):
            health = await manager.check_health(model.model_id)
            if not health['healthy']:
                # Alert and failover
                pass
        await asyncio.sleep(300)  # Every 5 minutes
```

### 5. Cost Tracking

Track token usage for cost estimation:

```python
metrics = manager.get_metrics("gpt-4-turbo")
cost_per_1k_tokens = 0.03  # Example rate
estimated_cost = (metrics.total_tokens / 1000) * cost_per_1k_tokens
print(f"Estimated cost: ${estimated_cost:.2f}")
```

### 6. Backup Models

Always have a backup model configured:

```python
# Primary model
manager.register_model(
    model_id="gpt-4-turbo",
    # ...
    tags=["primary"]
)

# Backup model
manager.register_model(
    model_id="gpt-3.5-turbo",
    # ...
    tags=["backup"]
)

# Failover logic
primary = manager.get_model("gpt-4-turbo")
if primary.status == ModelStatus.FAILED:
    manager.set_active_model("gpt-3.5-turbo")
```

### 7. Configuration Management

Store sensitive config in environment variables:

```python
manager.register_model(
    model_id="gpt-4-turbo",
    config={
        "api_key_env": "OPENAI_API_KEY",  # Reference env var
        "temperature": 0.7,
        "max_tokens": 4096
    }
)
```

## Troubleshooting

### Model Not Activating

**Problem**: Cannot set model as active

**Solution**: Ensure model status is ACTIVE or TESTING:

```python
manager.update_model("model-id", status=ModelStatus.ACTIVE)
manager.set_active_model("model-id")
```

### High Error Rate

**Problem**: Model showing high error rate

**Solution**: Check health and consider failover:

```python
health = await manager.check_health("model-id")
if not health['healthy']:
    # Switch to backup
    manager.set_active_model("backup-model-id")
```

### A/B Test Traffic Split Error

**Problem**: Traffic split doesn't sum to 1.0

**Solution**: Ensure percentages sum to exactly 1.0:

```python
# Correct
traffic_split = {"model-a": 0.5, "model-b": 0.5}  # Sum = 1.0

# Incorrect
traffic_split = {"model-a": 0.6, "model-b": 0.6}  # Sum = 1.2
```

## Additional Resources

- [API Documentation](./API_REFERENCE.md)
- [GraphQL API](./GRAPHQL_API.md)
- [Monitoring Guide](./MONITORING.md)
- [Plugin Development](./PLUGIN_DEVELOPMENT.md)
