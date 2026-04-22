# API Usage Examples

Practical examples for using the PR Agent API in various programming languages.

## Table of Contents

- [Python Examples](#python-examples)
- [JavaScript/Node.js Examples](#javascriptnodejs-examples)
- [cURL Examples](#curl-examples)
- [Postman Collection](#postman-collection)
- [Common Workflows](#common-workflows)

## Python Examples

### Setup

```python
import requests
from typing import Dict, Any

class PRAgentClient:
    def __init__(self, base_url: str, api_key: str = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.token = None
    
    def _headers(self) -> Dict[str, str]:
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        elif self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        response = requests.post(
            f'{self.base_url}/api/auth/login',
            json={'username': username, 'password': password}
        )
        response.raise_for_status()
        data = response.json()
        self.token = data['access_token']
        return data

# Initialize client
client = PRAgentClient('http://localhost:8000')
client.login('admin', 'admin123')
```

### List Repositories

```python
def list_repositories(client: PRAgentClient, page: int = 1, search: str = None):
    params = {'page': page, 'per_page': 20}
    if search:
        params['search'] = search
    
    response = requests.get(
        f'{client.base_url}/api/repositories',
        headers=client._headers(),
        params=params
    )
    response.raise_for_status()
    return response.json()

# Usage
repos = list_repositories(client, search='backend')
for repo in repos['items']:
    print(f"{repo['name']}: {repo['total_reviews']} reviews")
```

### Add Repository

```python
def add_repository(client: PRAgentClient, name: str, url: str, config: Dict = None):
    data = {
        'name': name,
        'url': url,
        'config': config or {
            'auto_review': True,
            'review_on_update': True,
            'min_approval_count': 2
        }
    }
    
    response = requests.post(
        f'{client.base_url}/api/repositories',
        headers=client._headers(),
        json=data
    )
    response.raise_for_status()
    return response.json()

# Usage
repo = add_repository(
    client,
    'my-project',
    'https://bitbucket.example.com/projects/PROJ/repos/my-project'
)
print(f"Repository created with ID: {repo['id']}")
```

### Trigger Manual Review

```python
def trigger_review(client: PRAgentClient, repository_id: int, pr_number: int):
    data = {
        'repository_id': repository_id,
        'pr_number': pr_number,
        'force': False
    }
    
    response = requests.post(
        f'{client.base_url}/api/reviews',
        headers=client._headers(),
        json=data
    )
    response.raise_for_status()
    return response.json()

# Usage
review = trigger_review(client, repository_id=1, pr_number=123)
print(f"Review queued with ID: {review['id']}")
```

### Get Review Details

```python
def get_review(client: PRAgentClient, review_id: int):
    response = requests.get(
        f'{client.base_url}/api/reviews/{review_id}',
        headers=client._headers()
    )
    response.raise_for_status()
    return response.json()

# Usage
review = get_review(client, review_id=1)
print(f"Review status: {review['status']}")
print(f"Score: {review['result']['score']}")
print(f"Issues found: {review['result']['issues_found']}")
```

### Poll Review Status

```python
import time

def wait_for_review(client: PRAgentClient, review_id: int, timeout: int = 300):
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        review = get_review(client, review_id)
        
        if review['status'] in ['completed', 'failed']:
            return review
        
        print(f"Review status: {review['status']}, waiting...")
        time.sleep(5)
    
    raise TimeoutError(f"Review did not complete within {timeout} seconds")

# Usage
review = trigger_review(client, repository_id=1, pr_number=123)
final_review = wait_for_review(client, review['id'])
print(f"Review completed with score: {final_review['result']['score']}")
```

### Update Prompt

```python
def update_prompt(client: PRAgentClient, prompt_id: str, content: str):
    data = {
        'content': content,
        'active': True
    }
    
    response = requests.put(
        f'{client.base_url}/api/prompts/{prompt_id}',
        headers=client._headers(),
        json=data
    )
    response.raise_for_status()
    return response.json()

# Usage
prompt = update_prompt(
    client,
    'custom-review-v1',
    'You are a code reviewer focusing on security and performance...'
)
print("Prompt updated successfully")
```

### Export Reviews

```python
def export_reviews(client: PRAgentClient, repository_id: int = None, 
                  from_date: str = None, to_date: str = None):
    params = {}
    if repository_id:
        params['repository_id'] = repository_id
    if from_date:
        params['from_date'] = from_date
    if to_date:
        params['to_date'] = to_date
    
    response = requests.get(
        f'{client.base_url}/api/reviews/export',
        headers=client._headers(),
        params=params
    )
    response.raise_for_status()
    
    with open('reviews.csv', 'wb') as f:
        f.write(response.content)
    
    print("Reviews exported to reviews.csv")

# Usage
export_reviews(client, repository_id=1, from_date='2026-04-01')
```

## JavaScript/Node.js Examples

### Setup

```javascript
const axios = require('axios');

class PRAgentClient {
  constructor(baseUrl, apiKey = null) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
    this.token = null;
  }

  _headers() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    } else if (this.apiKey) {
      headers['X-API-Key'] = this.apiKey;
    }
    return headers;
  }

  async login(username, password) {
    const response = await axios.post(
      `${this.baseUrl}/api/auth/login`,
      { username, password }
    );
    this.token = response.data.access_token;
    return response.data;
  }
}

// Initialize client
const client = new PRAgentClient('http://localhost:8000');
await client.login('admin', 'admin123');
```

### List Repositories

```javascript
async function listRepositories(client, page = 1, search = null) {
  const params = { page, per_page: 20 };
  if (search) params.search = search;

  const response = await axios.get(
    `${client.baseUrl}/api/repositories`,
    {
      headers: client._headers(),
      params
    }
  );
  return response.data;
}

// Usage
const repos = await listRepositories(client, 1, 'backend');
repos.items.forEach(repo => {
  console.log(`${repo.name}: ${repo.total_reviews} reviews`);
});
```

### Add Repository

```javascript
async function addRepository(client, name, url, config = null) {
  const data = {
    name,
    url,
    config: config || {
      auto_review: true,
      review_on_update: true,
      min_approval_count: 2
    }
  };

  const response = await axios.post(
    `${client.baseUrl}/api/repositories`,
    data,
    { headers: client._headers() }
  );
  return response.data;
}

// Usage
const repo = await addRepository(
  client,
  'my-project',
  'https://bitbucket.example.com/projects/PROJ/repos/my-project'
);
console.log(`Repository created with ID: ${repo.id}`);
```

### Trigger and Wait for Review

```javascript
async function triggerAndWaitForReview(client, repositoryId, prNumber, timeout = 300000) {
  // Trigger review
  const triggerResponse = await axios.post(
    `${client.baseUrl}/api/reviews`,
    {
      repository_id: repositoryId,
      pr_number: prNumber,
      force: false
    },
    { headers: client._headers() }
  );

  const reviewId = triggerResponse.data.id;
  const startTime = Date.now();

  // Poll for completion
  while (Date.now() - startTime < timeout) {
    const response = await axios.get(
      `${client.baseUrl}/api/reviews/${reviewId}`,
      { headers: client._headers() }
    );

    const review = response.data;

    if (review.status === 'completed' || review.status === 'failed') {
      return review;
    }

    console.log(`Review status: ${review.status}, waiting...`);
    await new Promise(resolve => setTimeout(resolve, 5000));
  }

  throw new Error(`Review did not complete within ${timeout}ms`);
}

// Usage
const review = await triggerAndWaitForReview(client, 1, 123);
console.log(`Review completed with score: ${review.result.score}`);
```

### Batch Operations

```javascript
async function batchAddRepositories(client, repositories) {
  const results = await Promise.allSettled(
    repositories.map(repo => addRepository(client, repo.name, repo.url))
  );

  const succeeded = results.filter(r => r.status === 'fulfilled').length;
  const failed = results.filter(r => r.status === 'rejected').length;

  console.log(`Added ${succeeded} repositories, ${failed} failed`);
  return results;
}

// Usage
const repos = [
  { name: 'repo-1', url: 'https://example.com/repo-1' },
  { name: 'repo-2', url: 'https://example.com/repo-2' },
  { name: 'repo-3', url: 'https://example.com/repo-3' }
];

await batchAddRepositories(client, repos);
```

## cURL Examples

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }'
```

### List Repositories

```bash
TOKEN="your-jwt-token"

curl -X GET "http://localhost:8000/api/repositories?page=1&per_page=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Add Repository

```bash
curl -X POST http://localhost:8000/api/repositories \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-repo",
    "url": "https://bitbucket.example.com/projects/PROJ/repos/my-repo",
    "config": {
      "auto_review": true,
      "review_on_update": true
    }
  }'
```

### Trigger Review

```bash
curl -X POST http://localhost:8000/api/reviews \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_id": 1,
    "pr_number": 123,
    "force": false
  }'
```

### Get Review Status

```bash
curl -X GET http://localhost:8000/api/reviews/1 \
  -H "Authorization: Bearer $TOKEN"
```

### Update Prompt

```bash
curl -X PUT http://localhost:8000/api/prompts/custom-review-v1 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "You are a code reviewer...",
    "active": true
  }'
```

## Common Workflows

### Workflow 1: Setup New Repository for Auto-Review

```python
def setup_repository_for_auto_review(client, name, url):
    # 1. Add repository
    repo = add_repository(client, name, url, {
        'auto_review': True,
        'review_on_update': True,
        'min_approval_count': 2
    })
    print(f"✓ Repository added: {repo['id']}")
    
    # 2. Configure custom prompt (optional)
    prompt = update_prompt(
        client,
        'custom-review-v1',
        'Focus on security and performance issues...'
    )
    print("✓ Custom prompt configured")
    
    # 3. Set up webhook notification
    webhook = requests.post(
        f'{client.base_url}/api/webhooks',
        headers=client._headers(),
        json={
            'url': 'https://hooks.slack.com/services/...',
            'events': ['review.completed', 'review.failed'],
            'active': True
        }
    )
    print("✓ Webhook configured")
    
    return repo

# Usage
repo = setup_repository_for_auto_review(
    client,
    'my-project',
    'https://bitbucket.example.com/projects/PROJ/repos/my-project'
)
```

### Workflow 2: Bulk Review Historical PRs

```python
def bulk_review_historical_prs(client, repository_id, pr_numbers):
    reviews = []
    
    for pr_number in pr_numbers:
        try:
            review = trigger_review(client, repository_id, pr_number)
            reviews.append(review)
            print(f"✓ Triggered review for PR #{pr_number}")
        except Exception as e:
            print(f"✗ Failed to trigger review for PR #{pr_number}: {e}")
    
    # Wait for all reviews to complete
    completed_reviews = []
    for review in reviews:
        try:
            final_review = wait_for_review(client, review['id'])
            completed_reviews.append(final_review)
            print(f"✓ Review completed for PR #{final_review['pr_number']}")
        except Exception as e:
            print(f"✗ Review failed: {e}")
    
    return completed_reviews

# Usage
pr_numbers = [101, 102, 103, 104, 105]
reviews = bulk_review_historical_prs(client, repository_id=1, pr_numbers=pr_numbers)

# Generate summary
total_issues = sum(r['result']['issues_found'] for r in reviews)
avg_score = sum(r['result']['score'] for r in reviews) / len(reviews)
print(f"\nSummary: {len(reviews)} reviews, {total_issues} issues, avg score: {avg_score:.2f}")
```

### Workflow 3: Monitor Review Queue

```python
import time
from datetime import datetime

def monitor_review_queue(client, interval=60):
    print("Starting review queue monitor...")
    
    while True:
        try:
            # Get pending reviews
            response = requests.get(
                f'{client.base_url}/api/reviews',
                headers=client._headers(),
                params={'status': 'pending'}
            )
            pending = response.json()
            
            # Get in-progress reviews
            response = requests.get(
                f'{client.base_url}/api/reviews',
                headers=client._headers(),
                params={'status': 'in_progress'}
            )
            in_progress = response.json()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{timestamp}] Pending: {pending['total']}, In Progress: {in_progress['total']}")
            
            # Alert if queue is too long
            if pending['total'] > 10:
                print(f"⚠️  Warning: Review queue is backed up ({pending['total']} pending)")
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print("\nMonitoring stopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(interval)

# Usage
monitor_review_queue(client, interval=60)
```

### Workflow 4: Generate Weekly Report

```python
from datetime import datetime, timedelta

def generate_weekly_report(client, repository_id=None):
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Fetch reviews
    params = {
        'from_date': start_date.isoformat(),
        'to_date': end_date.isoformat(),
        'per_page': 100
    }
    if repository_id:
        params['repository_id'] = repository_id
    
    response = requests.get(
        f'{client.base_url}/api/reviews',
        headers=client._headers(),
        params=params
    )
    reviews = response.json()['items']
    
    # Calculate statistics
    total_reviews = len(reviews)
    completed = [r for r in reviews if r['status'] == 'completed']
    failed = [r for r in reviews if r['status'] == 'failed']
    
    avg_score = sum(r['result']['score'] for r in completed) / len(completed) if completed else 0
    total_issues = sum(r['result']['issues_found'] for r in completed)
    avg_duration = sum(r['duration'] for r in completed) / len(completed) if completed else 0
    
    # Generate report
    report = f"""
Weekly Review Report
====================
Period: {start_date.date()} to {end_date.date()}

Summary:
- Total Reviews: {total_reviews}
- Completed: {len(completed)}
- Failed: {len(failed)}
- Success Rate: {len(completed)/total_reviews*100:.1f}%

Quality Metrics:
- Average Score: {avg_score:.2f}/10
- Total Issues Found: {total_issues}
- Average Review Time: {avg_duration:.1f}s

Top Issues:
"""
    
    # Find most common issues
    all_issues = []
    for review in completed:
        if 'details' in review['result']:
            for category in review['result']['details'].values():
                all_issues.extend(category.get('issues', []))
    
    # Count issue types
    issue_counts = {}
    for issue in all_issues:
        msg = issue['message']
        issue_counts[msg] = issue_counts.get(msg, 0) + 1
    
    # Add top 5 issues to report
    for msg, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        report += f"- {msg}: {count} occurrences\n"
    
    print(report)
    return report

# Usage
report = generate_weekly_report(client, repository_id=1)
```

## Error Handling

### Robust Error Handling

```python
from requests.exceptions import RequestException, Timeout, HTTPError

def safe_api_call(func, *args, max_retries=3, **kwargs):
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Timeout:
            print(f"Timeout on attempt {attempt + 1}/{max_retries}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # Exponential backoff
        except HTTPError as e:
            if e.response.status_code == 429:  # Rate limit
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited, waiting {retry_after}s")
                time.sleep(retry_after)
            elif e.response.status_code >= 500:  # Server error
                print(f"Server error on attempt {attempt + 1}/{max_retries}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
            else:
                raise
        except RequestException as e:
            print(f"Request failed: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

# Usage
repos = safe_api_call(list_repositories, client, page=1)
```

## See Also

- [API Reference](./API_REFERENCE.md)
- [Authentication Guide](./SECURITY.md)
- [Rate Limiting](./RATE_LIMITING.md)
- [Webhook Configuration](./WEBHOOK_NOTIFICATIONS.md)
