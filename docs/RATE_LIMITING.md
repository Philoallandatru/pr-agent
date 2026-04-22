# Rate Limiting and Quota Management

Complete rate limiting and quota management system for API protection and resource control.

## Features

### Rate Limiting
- **Multiple Strategies**: Fixed window, sliding window, token bucket
- **Flexible Storage**: Redis (distributed) or in-memory (single instance)
- **Per-User/IP Limiting**: Customizable rate limit keys
- **Automatic Headers**: Standard rate limit headers in responses
- **Graceful Degradation**: Falls back to memory if Redis unavailable

### Quota Management
- **Resource Quotas**: API calls, reviews, repositories, users, storage
- **Multiple Periods**: Daily, monthly, yearly, or permanent quotas
- **Alert Thresholds**: Notifications when approaching limits
- **Organization-Level**: Quota isolation per organization
- **Usage Tracking**: Historical usage data with periods

## Rate Limiting

### Strategies

#### 1. Fixed Window
Simple counter per time window. Resets at window boundaries.

**Pros**: Simple, efficient
**Cons**: Burst at window boundaries

```python
limiter = RateLimiter(
    strategy="fixed_window",
    default_limit=100,
    default_window=60  # 100 requests per 60 seconds
)
```

#### 2. Sliding Window
More accurate, tracks individual request timestamps.

**Pros**: No boundary bursts, accurate
**Cons**: More memory usage

```python
limiter = RateLimiter(
    strategy="sliding_window",
    default_limit=100,
    default_window=60
)
```

#### 3. Token Bucket
Allows bursts while maintaining average rate.

**Pros**: Handles bursts gracefully
**Cons**: More complex

```python
limiter = RateLimiter(
    strategy="token_bucket",
    default_limit=100,  # bucket capacity
    default_window=60   # refill rate
)
```

### Usage Examples

#### Basic Rate Limiting

```python
from pr_agent.ratelimit import RateLimiter

# Create limiter
limiter = RateLimiter(
    redis_client=None,  # or redis.Redis()
    default_limit=100,
    default_window=60,
    strategy="fixed_window"
)

# Check rate limit
key = f"user:{user_id}"
allowed, info = limiter.check_rate_limit(key)

if not allowed:
    raise Exception(f"Rate limit exceeded. Retry after {info['retry_after']}s")

# Process request
process_request()
```

#### Custom Limits Per Request

```python
# Different limit for specific endpoint
allowed, info = limiter.check_rate_limit(
    key=f"user:{user_id}",
    limit=10,   # Only 10 requests
    window=60   # per minute
)
```

#### Reset Rate Limit

```python
# Reset for specific user (e.g., after upgrade)
limiter.reset(f"user:{user_id}")
```

#### Get Current Status

```python
# Check status without incrementing
info = limiter.get_limits(f"user:{user_id}")
print(f"Remaining: {info['remaining']}/{info['limit']}")
print(f"Resets at: {info['reset']}")
```

### FastAPI Integration

#### Middleware (Global)

```python
from fastapi import FastAPI
from pr_agent.ratelimit import RateLimiter
from pr_agent.ratelimit.middleware import RateLimitMiddleware

app = FastAPI()

# Create limiter
limiter = RateLimiter(
    redis_client=redis_client,
    default_limit=1000,
    default_window=3600,  # 1000 requests per hour
    strategy="sliding_window"
)

# Add middleware
app.add_middleware(
    RateLimitMiddleware,
    rate_limiter=limiter,
    key_func=lambda req: req.state.user.get("id") if hasattr(req.state, "user") else req.client.host,
    exempt_paths=["/health", "/docs"]
)
```

#### Dependency (Per-Endpoint)

```python
from fastapi import Depends
from pr_agent.ratelimit.middleware import rate_limit_dependency

# Strict limit for expensive endpoint
@app.post(
    "/api/expensive-operation",
    dependencies=[Depends(rate_limit_dependency(limiter, limit=10, window=60))]
)
async def expensive_operation():
    return {"status": "processing"}
```

### Response Headers

Rate limit information is included in response headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 73
X-RateLimit-Reset: 1640000000
```

On rate limit exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1640000000
Retry-After: 45

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Try again in 45 seconds.",
  "retry_after": 45
}
```

## Quota Management

### Quota Types

- **api_calls**: Total API requests per period
- **reviews**: PR reviews per period
- **repositories**: Number of repositories (permanent)
- **users**: Number of users (permanent)
- **storage**: Storage usage in bytes

### Usage Examples

#### Set Quotas

```python
from pr_agent.ratelimit import QuotaManager

manager = QuotaManager("pr_agent.db")

# Monthly API call limit
manager.set_quota(
    org_id=1,
    quota_type="api_calls",
    limit=10000,
    reset_period="monthly"
)

# Permanent repository limit
manager.set_quota(
    org_id=1,
    quota_type="repositories",
    limit=50,
    reset_period="never"
)
```

#### Check Quota

```python
# Check if operation is allowed
if not manager.check_quota(org_id=1, quota_type="reviews", amount=1):
    raise Exception("Review quota exceeded")

# Get detailed quota info
quota = manager.get_quota(org_id=1, quota_type="reviews")
print(f"Used: {quota.used}/{quota.limit}")
print(f"Remaining: {quota.remaining}")
print(f"Resets: {quota.reset_date}")
print(f"Percentage: {quota.percentage_used}%")
```

#### Increment/Decrement Usage

```python
# Increment when resource is used
try:
    quota = manager.increment_quota(
        org_id=1,
        quota_type="reviews",
        amount=1,
        check_limit=True  # Raise exception if exceeded
    )
except QuotaExceeded as e:
    print(f"Quota exceeded: {e.current}/{e.limit}")

# Decrement when resource is deleted
manager.decrement_quota(
    org_id=1,
    quota_type="repositories",
    amount=1
)
```

#### Get All Quotas

```python
# Get all quotas for organization
quotas = manager.get_all_quotas(org_id=1)

for quota in quotas:
    print(f"{quota.quota_type}: {quota.used}/{quota.limit}")
    if quota.is_exceeded:
        print(f"  ⚠️ EXCEEDED!")
```

#### Alert Thresholds

```python
# Set alert at 80% usage
manager.set_alert_threshold(
    org_id=1,
    quota_type="api_calls",
    threshold=80
)

# Check for alerts
alerts = manager.check_alerts(org_id=1)
for alert in alerts:
    print(f"Alert: {alert['quota_type']} at {alert['current_percentage']}%")
    send_notification(alert)
```

### FastAPI Integration

#### Middleware (Global)

```python
from pr_agent.ratelimit.middleware import QuotaMiddleware

app.add_middleware(
    QuotaMiddleware,
    quota_manager=quota_manager,
    org_id_func=lambda req: req.state.user.get("org_id"),
    quota_paths={
        "/api/reviews": "reviews",
        "/api/repositories": "repositories"
    }
)
```

#### Dependency (Per-Endpoint)

```python
from pr_agent.ratelimit.middleware import quota_dependency

@app.post(
    "/api/reviews",
    dependencies=[Depends(quota_dependency(quota_manager, "reviews"))]
)
async def create_review(request: Request):
    # Quota checked automatically
    # Increment on success
    return {"status": "created"}
```

### Response Headers

Quota information in response headers:

```http
HTTP/1.1 200 OK
X-Quota-Limit: 1000
X-Quota-Remaining: 847
X-Quota-Reset: 2024-02-01T00:00:00Z
```

On quota exceeded:

```http
HTTP/1.1 429 Too Many Requests
X-Quota-Limit: 1000
X-Quota-Remaining: 0
X-Quota-Reset: 2024-02-01T00:00:00Z

{
  "error": "quota_exceeded",
  "message": "Quota exceeded for reviews",
  "quota_type": "reviews",
  "limit": 1000,
  "used": 1000,
  "reset_date": "2024-02-01T00:00:00Z"
}
```

## Configuration

Add to `configuration.toml`:

```toml
[rate_limit]
enabled = true
strategy = "sliding_window"  # fixed_window, sliding_window, token_bucket
default_limit = 1000
default_window = 3600  # seconds
redis_url = "redis://localhost:6379/0"  # optional

[quota]
enabled = true
enforce_limits = true
alert_thresholds = [80, 90, 95]  # percentage thresholds

# Default quotas per plan
[quota.free]
api_calls = 1000
reviews = 100
repositories = 10
users = 5

[quota.pro]
api_calls = 10000
reviews = 1000
repositories = 50
users = 25

[quota.enterprise]
api_calls = 100000
reviews = 10000
repositories = 0  # unlimited
users = 0  # unlimited
```

## Redis Setup

For distributed rate limiting:

```python
import redis

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=False
)

limiter = RateLimiter(
    redis_client=redis_client,
    default_limit=1000,
    default_window=3600,
    strategy="sliding_window"
)
```

## Testing

Run the test suite:

```bash
# Rate limiter tests
pytest tests/unittest/test_rate_limiter.py -v

# Quota manager tests
pytest tests/unittest/test_quota_manager.py -v
```

## Best Practices

### Rate Limiting

1. **Choose the Right Strategy**:
   - Fixed window: Simple APIs with moderate traffic
   - Sliding window: APIs requiring accurate limiting
   - Token bucket: APIs with bursty traffic patterns

2. **Set Appropriate Limits**:
   - Start conservative, increase based on monitoring
   - Different limits for authenticated vs anonymous
   - Higher limits for premium users

3. **Use Redis for Production**:
   - Distributed rate limiting across instances
   - Persistent state across restarts
   - Better performance at scale

4. **Exempt Critical Paths**:
   - Health checks
   - Monitoring endpoints
   - Authentication endpoints

### Quota Management

1. **Plan-Based Quotas**:
   - Clear limits per subscription tier
   - Automatic enforcement
   - Upgrade prompts when approaching limits

2. **Alert Thresholds**:
   - Notify at 80%, 90%, 95%
   - Give users time to upgrade
   - Prevent surprise quota exhaustion

3. **Graceful Degradation**:
   - Soft limits with warnings
   - Hard limits with clear messages
   - Upgrade paths in error responses

4. **Usage Analytics**:
   - Track quota usage trends
   - Identify power users
   - Optimize quota allocations

## Troubleshooting

### Rate Limit Not Working

**Issue**: Requests not being rate limited

**Solutions**:
- Check if path is in exempt_paths
- Verify key_func returns consistent keys
- Check Redis connection if using Redis backend
- Verify middleware is added to app

### Quota Not Incrementing

**Issue**: Quota usage not updating

**Solutions**:
- Ensure increment_quota is called after successful operations
- Check database permissions
- Verify org_id is correctly extracted
- Check for exceptions in quota middleware

### Redis Connection Errors

**Issue**: Rate limiter failing with Redis errors

**Solutions**:
- Verify Redis is running
- Check connection string
- Limiter automatically falls back to memory
- Monitor fallback behavior in logs

### Quota Reset Not Working

**Issue**: Quotas not resetting at period boundaries

**Solutions**:
- Check reset_period configuration
- Verify system time is correct
- Manual reset: `manager.reset_quota(org_id, quota_type)`
- Check database for stale period entries

## Performance Considerations

- **Redis**: ~10,000 ops/sec per instance
- **Memory**: ~1MB per 10,000 active keys
- **Sliding Window**: 2x memory vs fixed window
- **Token Bucket**: Minimal memory overhead

## Security

- Rate limiting prevents brute force attacks
- Quota management prevents resource exhaustion
- Use authenticated keys when possible
- Monitor for abuse patterns
- Implement IP-based fallback limits
