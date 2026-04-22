# Performance Testing Guide

This guide explains how to run performance benchmarks and load tests for PR Agent.

## Overview

The performance testing suite includes:
- **API Benchmarks**: Measure endpoint response times and throughput
- **Database Benchmarks**: Test database query performance
- **Load Tests**: Simulate realistic user load

## Prerequisites

Install required dependencies:

```bash
pip install httpx psutil
```

## API Benchmarks

### Running API Benchmarks

Test all API endpoints:

```bash
python tests/performance/benchmark_api.py \
  --url http://localhost:8000 \
  --requests 100 \
  --concurrent 10 \
  --output results/api_benchmark.json
```

**Parameters**:
- `--url`: Base URL of the API (default: http://localhost:8000)
- `--token`: Authentication token (optional)
- `--requests`: Number of requests per benchmark (default: 100)
- `--concurrent`: Number of concurrent requests (default: 10)
- `--output`: Output file for JSON report (optional)

### Example Output

```
================================================================================
PR Agent API Performance Benchmarks
================================================================================

Running benchmark: Health Check
  Requests: 100, Concurrent: 10

  Results:
    Duration: 2.45s
    Requests/sec: 40.82
    Success rate: 100.0%
    Response times:
      Mean: 24.50ms
      Median: 23.12ms
      P95: 35.67ms
      P99: 42.18ms
      Min: 18.45ms
      Max: 48.92ms
```

### Metrics Collected

- **Requests per second**: Throughput
- **Response times**: Mean, median, P95, P99, min, max
- **Success rate**: Percentage of successful requests
- **Error breakdown**: Types and counts of errors

## Database Benchmarks

### Running Database Benchmarks

Test database operations:

```bash
python tests/performance/benchmark_database.py \
  --db /path/to/test.db \
  --output results/db_benchmark.json
```

**Parameters**:
- `--db`: Database path (default: temporary database)
- `--output`: Output file for JSON report (optional)

### Operations Tested

1. **INSERT**: Single row inserts
2. **Batch INSERT**: Bulk inserts with batching
3. **SELECT**: Single row queries by ID
4. **JOIN**: Complex queries with joins and aggregations
5. **UPDATE**: Single row updates
6. **Transactions**: Multi-operation transactions

### Example Output

```
================================================================================
Database Performance Benchmarks
================================================================================

Benchmarking INSERT operations (1000 ops)...
  Operations/sec: 2543.21
  Mean time: 0.393ms
  Median time: 0.385ms
  P95 time: 0.512ms
  Min/Max: 0.298ms / 1.234ms

Benchmarking batch INSERT operations (1000 ops, batch size 100)...
  Operations/sec: 8921.45
  Mean time: 0.112ms
  Median time: 0.108ms
  P95 time: 0.145ms
  Min/Max: 0.089ms / 0.234ms
```

## Load Testing

### Running Load Tests

Simulate realistic user load:

```bash
python tests/performance/load_test.py \
  --url http://localhost:8000 \
  --users 50 \
  --duration 300 \
  --ramp-up 30 \
  --output results/load_test.json
```

**Parameters**:
- `--url`: Base URL of the API
- `--token`: Authentication token (optional)
- `--users`: Number of virtual users (default: 10)
- `--duration`: Test duration in seconds (default: 60)
- `--ramp-up`: Ramp-up time in seconds (default: 10)
- `--output`: Output file for JSON report (optional)

### User Scenario

Each virtual user performs the following actions in a loop:
1. Check health endpoint
2. List repositories
3. List reviews
4. Occasionally check analytics (30% probability)
5. Occasionally check metrics (20% probability)
6. Random think time between actions (1-5 seconds)

### Example Output

```
================================================================================
Load Test Starting
================================================================================
Base URL: http://localhost:8000
Virtual Users: 50
Duration: 300s
Ramp-up: 30s

Starting user 1/50
Starting user 2/50
...
All users started, running test...

================================================================================
Load Test Results
================================================================================

Duration: 300.12s
Total Requests: 15234
Successful: 15198
Failed: 36
Success Rate: 99.8%
Requests/sec: 50.76
Avg Response Time: 45.23ms

Response Time Percentiles:
  P50: 38.12ms
  P95: 89.45ms
  P99: 142.67ms

Requests per Endpoint:
  /api/repositories: 3845
  /api/reviews: 3842
  /api/health: 3850
  /api/analytics/overview: 1156
  /metrics: 768

Errors:
  HTTP 503: 24
  TimeoutError: 12
```

## Performance Targets

### API Endpoints

| Endpoint | Target P95 | Target RPS |
|----------|-----------|------------|
| Health Check | < 50ms | > 100 |
| List Repositories | < 200ms | > 50 |
| List Reviews | < 300ms | > 40 |
| Analytics | < 500ms | > 20 |
| Metrics | < 100ms | > 80 |

### Database Operations

| Operation | Target Ops/Sec |
|-----------|---------------|
| INSERT | > 2000 |
| Batch INSERT | > 8000 |
| SELECT by ID | > 5000 |
| JOIN | > 1000 |
| UPDATE | > 1500 |
| Transaction | > 500 |

### Load Test

| Metric | Target |
|--------|--------|
| Success Rate | > 99% |
| P95 Response Time | < 200ms |
| Requests/sec (50 users) | > 40 |

## Continuous Performance Testing

### GitHub Actions Integration

Add to `.github/workflows/performance.yml`:

```yaml
name: Performance Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install httpx psutil
    
    - name: Start application
      run: |
        python -m pr_agent.servers.web_platform &
        sleep 10
    
    - name: Run API benchmarks
      run: |
        python tests/performance/benchmark_api.py \
          --requests 100 \
          --concurrent 10 \
          --output results/api_benchmark.json
    
    - name: Run database benchmarks
      run: |
        python tests/performance/benchmark_database.py \
          --output results/db_benchmark.json
    
    - name: Run load test
      run: |
        python tests/performance/load_test.py \
          --users 20 \
          --duration 60 \
          --output results/load_test.json
    
    - name: Upload results
      uses: actions/upload-artifact@v3
      with:
        name: performance-results
        path: results/
```

## Analyzing Results

### JSON Report Structure

All benchmarks generate JSON reports with the following structure:

```json
{
  "timestamp": "2026-04-22T10:30:00",
  "benchmarks": [
    {
      "name": "Health Check",
      "total_requests": 100,
      "duration": 2.45,
      "requests_per_second": 40.82,
      "mean_response_time": 0.02450,
      "p95_response_time": 0.03567,
      "success_rate": 1.0
    }
  ],
  "summary": {
    "total_benchmarks": 6,
    "average_rps": 45.23,
    "overall_success_rate": 0.998
  }
}
```

### Comparing Results

Compare results over time:

```python
import json

def compare_benchmarks(old_file, new_file):
    with open(old_file) as f:
        old = json.load(f)
    with open(new_file) as f:
        new = json.load(f)
    
    for old_b, new_b in zip(old['benchmarks'], new['benchmarks']):
        name = old_b['name']
        old_rps = old_b['requests_per_second']
        new_rps = new_b['requests_per_second']
        change = ((new_rps - old_rps) / old_rps) * 100
        
        print(f"{name}: {old_rps:.2f} -> {new_rps:.2f} ({change:+.1f}%)")

compare_benchmarks('results/baseline.json', 'results/current.json')
```

## Performance Optimization Tips

### API Performance

1. **Enable caching**: Use Redis for frequently accessed data
2. **Database indexing**: Add indexes for common queries
3. **Connection pooling**: Reuse database connections
4. **Async operations**: Use async/await for I/O operations
5. **Response compression**: Enable gzip compression

### Database Performance

1. **Batch operations**: Use batch inserts/updates
2. **Query optimization**: Analyze and optimize slow queries
3. **Proper indexing**: Index foreign keys and frequently queried columns
4. **Connection limits**: Configure appropriate pool size
5. **Vacuum regularly**: Maintain database health

### System Performance

1. **Resource limits**: Set appropriate CPU/memory limits
2. **Worker processes**: Configure optimal number of workers
3. **Load balancing**: Distribute load across multiple instances
4. **Monitoring**: Track metrics and set up alerts
5. **Caching layers**: Use multiple caching layers (Redis, CDN)

## Troubleshooting

### High Response Times

```bash
# Check system resources
top
htop

# Check database performance
sqlite3 pr_agent.db "EXPLAIN QUERY PLAN SELECT ..."

# Enable query logging
export LOG_LEVEL=DEBUG
```

### Low Throughput

```bash
# Increase worker processes
export WORKERS=4

# Check connection pool
# Edit configuration.toml
[database]
pool_size = 20
max_overflow = 10
```

### Memory Issues

```bash
# Monitor memory usage
python tests/performance/benchmark_api.py --requests 1000

# Check for memory leaks
import tracemalloc
tracemalloc.start()
# Run tests
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
```

## Best Practices

1. **Baseline**: Establish performance baselines before changes
2. **Consistent environment**: Run tests in consistent environments
3. **Warm-up**: Allow warm-up time before measuring
4. **Multiple runs**: Run tests multiple times and average results
5. **Realistic scenarios**: Use realistic data and user patterns
6. **Monitor resources**: Track CPU, memory, disk, network
7. **Document changes**: Record configuration changes
8. **Automate**: Integrate into CI/CD pipeline
9. **Alert on regressions**: Set up alerts for performance degradation
10. **Regular testing**: Run performance tests regularly

## See Also

- [Monitoring Setup](./MONITORING_SETUP.md)
- [Performance Tuning](./PERFORMANCE.md)
- [Database Optimization](./DATABASE_MIGRATIONS.md)
