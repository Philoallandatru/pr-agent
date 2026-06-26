# bitbucket-review

Review Bitbucket Server pull requests with AI assistance.

## Usage

### Start webhook server
```
/bitbucket-review start-webhook
```

### Review a specific PR
```
/bitbucket-review review <pr_url>
```

### Run multiple commands on a PR
```
/bitbucket-review review <pr_url> --commands review describe improve
```

### Check connection status
```
/bitbucket-review status
```

## Configuration

Set these environment variables or configure in `.pr_agent.toml`:

### Required
- `BITBUCKET_URL` - Bitbucket Server URL (e.g., https://bitbucket.example.com)
- `BITBUCKET_TOKEN` - Personal access token (recommended)
  
  OR
  
- `BITBUCKET_USERNAME` + `BITBUCKET_PASSWORD` - Username and password

- `OPENAI_API_KEY` - OpenAI API key (or other AI provider key like `ANTHROPIC_API_KEY`)

### Optional
- `WEBHOOK_SECRET` - Secret for webhook signature verification
- `WEBHOOK_PORT` - Webhook server port (default: 3000)
- `WEBHOOK_HOST` - Webhook server host (default: 0.0.0.0)

### Configuration in `.pr_agent.toml`

```toml
[bitbucket_server]
url = "https://bitbucket.example.com"
bearer_token = "your_token_here"

# Webhook settings
webhook_secret = "your_secret"
auto_review_on_open = true
auto_review_on_update = false

# Commands to run automatically
pr_commands = ["review"]

[config]
# Ignore patterns (regex)
ignore_repositories = ["archive/.*", "deprecated/.*"]
ignore_pr_authors = ["bot-user"]
ignore_pr_title = ["WIP:.*", "Draft:.*"]
```

## Examples

### Start webhook server

```bash
# Start webhook server in foreground
/bitbucket-review start-webhook

# Or use Python directly
python -m pr_agent.skills.bitbucket_review.skill start-webhook
```

Then configure webhook in Bitbucket Server:
- URL: `http://your-server:3000/webhook`
- Events: PR opened, updated, commented

### Manual PR review

```bash
# Review a single PR
/bitbucket-review review https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123

# Run multiple commands
/bitbucket-review review https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123 --commands review describe improve
```

### Test connection

```bash
/bitbucket-review status

# Or use Python directly
python -m pr_agent.skills.bitbucket_review.skill test-connection
```

## Features

### Webhook Integration
- Automatically review PRs when opened or updated
- Respond to comment commands (e.g., `/review`, `/improve`)
- Filter PRs by repository, author, or title patterns

### PR Commands
- **review** - AI-powered code review with suggestions
- **describe** - Generate PR description
- **improve** - Suggest code improvements
- **ask** - Answer questions about the PR
- And more...

### Efficiency Monitoring
- Tracks review metrics (time saved, issues found, cost)
- Stores data in SQLite database
- View metrics with `monitor_efficiency.py`

## Implementation

This skill integrates:
- Bitbucket Server webhook handling (FastAPI)
- PR data fetching via Bitbucket REST API
- AI-powered code review (GPT-4, Claude, etc.)
- Automated comment posting
- Efficiency metrics tracking

## Architecture

```
BitbucketReviewSkill
├── BitbucketServerClient    # API wrapper
├── WebhookHandler           # Event parsing & filtering
├── ReviewRunner             # PR command execution
└── FastAPI app              # Webhook server
```

## Troubleshooting

### Connection issues
```bash
# Test connection
python -m pr_agent.skills.bitbucket_review.skill test-connection
```

### Webhook not triggering
1. Check webhook configuration in Bitbucket Server
2. Verify webhook URL is accessible
3. Check webhook signature if secret is set
4. View logs for error messages

### PR not being reviewed
1. Check filter rules (ignore_repositories, ignore_pr_authors)
2. Verify auto_review_on_open/auto_review_on_update settings
3. Check database for existing reviews (if deduplication is enabled)

## Related Documentation

- [Bitbucket Server Webhook Guide](../docs/BITBUCKET_SERVER_WEBHOOK.md)
- [Quick Start](../docs/BITBUCKET_SERVER_QUICKSTART.md)
- [Service Startup Guide](../docs/HOW_TO_START_SERVICE.md)
- [Monitoring Guide](../docs/MONITORING_GUIDE.md)
