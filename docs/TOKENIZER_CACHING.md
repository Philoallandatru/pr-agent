# Tokenizer Local Caching

This feature enables offline deployment of PR-Agent in internal networks by caching tokenizers locally, avoiding repeated external network access.

## Configuration

Add the following to your `.pr_agent.toml` or `configuration.toml`:

```toml
[tokenizer]
local_cache_dir = "/opt/pr-agent/tokenizers"  # Custom tokenizer storage path
enable_local_cache = true
fallback_to_download = false  # Set to false for strict offline mode
```

### Configuration Options

- **`local_cache_dir`**: Path to store cached tokenizers (default: empty, disabled)
- **`enable_local_cache`**: Enable local caching (default: false)
- **`fallback_to_download`**: Allow downloading if not in cache (default: true)
  - Set to `false` for strict offline environments

## Usage

### 1. Pre-download Tokenizers (One-time Setup)

Before deploying in an offline environment, download tokenizers on a machine with internet access:

```bash
# Download common tokenizers
python -m pr_agent.algo.tokenizer_manager download

# Download specific models
python -m pr_agent.algo.tokenizer_manager download --models gpt-4 gpt-4o claude-3-opus

# Specify custom cache directory
python -m pr_agent.algo.tokenizer_manager download --cache-dir /opt/pr-agent/tokenizers
```

### 2. Transfer Cache to Offline Environment

Copy the cache directory to your offline deployment:

```bash
# On machine with internet
tar -czf tokenizers.tar.gz /opt/pr-agent/tokenizers

# Transfer to offline machine
scp tokenizers.tar.gz user@offline-server:/tmp/

# On offline machine
tar -xzf /tmp/tokenizers.tar.gz -C /opt/pr-agent/
```

### 3. Verify Cache

Check cached tokenizers:

```bash
# List cached tokenizers
python -m pr_agent.algo.tokenizer_manager list

# Validate cache integrity
python -m pr_agent.algo.tokenizer_manager validate

# Get cache information
python -m pr_agent.algo.tokenizer_manager info
```

### 4. Run PR-Agent Offline

With `fallback_to_download=false`, PR-Agent will only use locally cached tokenizers:

```bash
python -m pr_agent.cli --pr_url https://bitbucket.internal/projects/PROJ/repos/repo/pull-requests/123 review
```

## CLI Commands

### Download Tokenizers

```bash
python -m pr_agent.algo.tokenizer_manager download [--models MODEL1 MODEL2 ...] [--cache-dir PATH]
```

Downloads tokenizers to local cache. If no models specified, downloads common models:
- gpt-4
- gpt-4o
- gpt-3.5-turbo
- o200k_base (fallback encoding)

### List Cached Tokenizers

```bash
python -m pr_agent.algo.tokenizer_manager list [--cache-dir PATH]
```

Lists all tokenizers in the cache.

### Validate Cache

```bash
python -m pr_agent.algo.tokenizer_manager validate [--cache-dir PATH]
```

Validates integrity of cached tokenizers.

### Get Cache Info

```bash
python -m pr_agent.algo.tokenizer_manager info [--cache-dir PATH]
```

Displays cache statistics including directory, size, and cached models.

### Clear Cache

```bash
python -m pr_agent.algo.tokenizer_manager clear [--cache-dir PATH]
```

Clears all cached tokenizers.

## How It Works

1. **Loading Priority**:
   - First: Check custom local cache directory
   - Second: Use tiktoken's internal cache
   - Third: Download from internet (if `fallback_to_download=true`)

2. **Offline Mode**:
   - Set `fallback_to_download=false` to prevent any network access
   - PR-Agent will raise an error if tokenizer not found in cache
   - Error message includes command to download missing tokenizer

3. **Cache Structure**:
   - Each model has a marker file: `{model_name}.tiktoken`
   - tiktoken handles actual encoding data internally
   - Marker files verify tokenizer availability

## Example Deployment

### Development Environment (with internet)

```toml
[tokenizer]
local_cache_dir = "/opt/pr-agent/tokenizers"
enable_local_cache = true
fallback_to_download = true  # Allow downloads during development
```

### Production Environment (offline)

```toml
[tokenizer]
local_cache_dir = "/opt/pr-agent/tokenizers"
enable_local_cache = true
fallback_to_download = false  # Strict offline mode
```

## Troubleshooting

### Error: "Tokenizer not available in local cache"

**Solution**: Download the tokenizer on a machine with internet access:

```bash
python -m pr_agent.algo.tokenizer_manager download --models gpt-4o
```

Then transfer the cache directory to your offline environment.

### Cache directory doesn't exist

**Solution**: The directory is created automatically when downloading tokenizers. Ensure the path is writable:

```bash
mkdir -p /opt/pr-agent/tokenizers
chmod 755 /opt/pr-agent/tokenizers
```

### Tokenizer loads slowly

**Solution**: This is normal on first load. tiktoken caches encodings internally after first use.

## Testing

Run unit tests to verify tokenizer caching:

```bash
PYTHONPATH=. pytest tests/unittest/test_tokenizer_manager.py -v
```

## Integration with PR-Agent

The tokenizer caching is automatically integrated into PR-Agent's token counting:

- `TokenHandler` uses `TokenEncoder.get_token_encoder()`
- `TokenEncoder` checks local cache before downloading
- All token counting operations benefit from caching
- No code changes needed in existing tools

## Performance

- **First load**: ~1-2 seconds (loading from cache)
- **Subsequent loads**: <100ms (in-memory singleton)
- **Cache size**: ~1-5 MB per tokenizer
- **Network savings**: 100% (no downloads in offline mode)
