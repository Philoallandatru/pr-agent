# Configuration Hot Reload

The hot reload system enables dynamic configuration updates without service restarts, allowing zero-downtime configuration changes in production environments.

## Overview

The hot reload system monitors configuration files for changes and automatically reloads them when modifications are detected. This eliminates the need for service restarts when updating configuration.

## Features

- **File Watching**: Automatic detection of configuration file changes
- **Validation**: Verify configuration before applying changes
- **Callbacks**: Execute custom logic when configuration changes
- **Rollback**: Automatic rollback on validation failures
- **Multi-File Support**: Monitor multiple configuration files simultaneously
- **Thread-Safe**: Safe concurrent access to configuration
- **Change Detection**: MD5-based change detection to avoid unnecessary reloads

## Configuration

Add to `configuration.toml`:

```toml
[hot_reload]
# Enable hot reload (default: true)
enabled = true

# Check interval in seconds (default: 5)
check_interval = 5

# Validate configuration before applying (default: true)
validate_before_reload = true

# Files to watch (default: ["configuration.toml"])
watch_files = [
    "configuration.toml",
    "prompts/system.toml",
    "prompts/review.toml"
]

# Enable change notifications (default: true)
notify_on_change = true
```

## Quick Start

### Basic Usage

```python
from pr_agent.config.hot_reload import HotReloadManager
from pr_agent.settings.configuration import get_settings

# Initialize hot reload manager
settings = get_settings()
hot_reload = HotReloadManager(
    config_path="configuration.toml",
    check_interval=5.0
)

# Register callback for configuration changes
def on_config_change(config: dict):
    print(f"Configuration updated: {config}")
    # Update application state
    settings.reload(config)

hot_reload.register_callback(on_config_change)

# Start watching
hot_reload.start()

# Your application runs here...

# Stop watching when done
hot_reload.stop()
```

### Web Platform Integration

The hot reload system is automatically integrated into the web platform:

```bash
# Start web platform with hot reload enabled
python -m pr_agent.servers.web_platform

# Configuration changes are automatically detected and applied
# No restart required!
```

## API Endpoints

### Get Hot Reload Status

```bash
GET /api/config/hot-reload/status

Returns current hot reload status and statistics.

Example:
curl http://localhost:8000/api/config/hot-reload/status

Response:
{
  "enabled": true,
  "watching": true,
  "files": [
    {
      "path": "configuration.toml",
      "last_modified": "2024-01-15T10:30:00Z",
      "last_reload": "2024-01-15T10:30:00Z",
      "reload_count": 5
    }
  ],
  "check_interval": 5.0,
  "total_reloads": 5,
  "last_error": null
}
```

### Enable Hot Reload

```bash
POST /api/config/hot-reload/enable

Enable hot reload monitoring.

Example:
curl -X POST http://localhost:8000/api/config/hot-reload/enable

Response:
{
  "status": "enabled",
  "message": "Hot reload enabled successfully"
}
```

### Disable Hot Reload

```bash
POST /api/config/hot-reload/disable

Disable hot reload monitoring.

Example:
curl -X POST http://localhost:8000/api/config/hot-reload/disable

Response:
{
  "status": "disabled",
  "message": "Hot reload disabled successfully"
}
```

### Force Reload

```bash
POST /api/config/hot-reload/reload

Force immediate configuration reload.

Example:
curl -X POST http://localhost:8000/api/config/hot-reload/reload

Response:
{
  "status": "success",
  "message": "Configuration reloaded successfully",
  "files_reloaded": ["configuration.toml"]
}
```

### Add Watch File

```bash
POST /api/config/hot-reload/watch
Content-Type: application/json

{
  "file_path": "prompts/custom.toml"
}

Add a new file to watch list.

Example:
curl -X POST http://localhost:8000/api/config/hot-reload/watch \
  -H "Content-Type: application/json" \
  -d '{"file_path": "prompts/custom.toml"}'

Response:
{
  "status": "success",
  "message": "File added to watch list",
  "file_path": "prompts/custom.toml"
}
```

### Remove Watch File

```bash
DELETE /api/config/hot-reload/watch/{file_path}

Remove a file from watch list.

Example:
curl -X DELETE http://localhost:8000/api/config/hot-reload/watch/prompts%2Fcustom.toml

Response:
{
  "status": "success",
  "message": "File removed from watch list",
  "file_path": "prompts/custom.toml"
}
```

### Get Watch List

```bash
GET /api/config/hot-reload/files

Get list of watched files.

Example:
curl http://localhost:8000/api/config/hot-reload/files

Response:
{
  "files": [
    {
      "path": "configuration.toml",
      "exists": true,
      "size": 12345,
      "last_modified": "2024-01-15T10:30:00Z"
    },
    {
      "path": "prompts/system.toml",
      "exists": true,
      "size": 5678,
      "last_modified": "2024-01-15T09:15:00Z"
    }
  ]
}
```

## Python API

### Basic Configuration Watcher

```python
from pr_agent.config.hot_reload import ConfigWatcher

# Create watcher for single file
watcher = ConfigWatcher(
    config_path="configuration.toml",
    check_interval=5.0
)

# Register callback
def on_change(config: dict):
    print("Configuration changed!")
    print(f"New config: {config}")

watcher.register_callback(on_change)

# Start watching
watcher.start()

# Check if file has changed
if watcher.has_changed():
    new_config = watcher.reload()
    print(f"Reloaded: {new_config}")

# Stop watching
watcher.stop()
```

### Multi-File Hot Reload Manager

```python
from pr_agent.config.hot_reload import HotReloadManager

# Create manager for multiple files
manager = HotReloadManager(
    config_path="configuration.toml",
    check_interval=5.0
)

# Add additional files to watch
manager.add_file("prompts/system.toml")
manager.add_file("prompts/review.toml")

# Register global callback
def on_any_change(config: dict):
    print("Any configuration file changed")

manager.register_callback(on_any_change)

# Register file-specific callback
def on_prompts_change(config: dict):
    print("Prompts configuration changed")
    # Update prompt templates

manager.register_callback(
    on_prompts_change,
    file_path="prompts/system.toml"
)

# Start watching all files
manager.start()

# Get status
status = manager.get_status()
print(f"Watching {len(status['files'])} files")
print(f"Total reloads: {status['total_reloads']}")

# Force reload all files
manager.reload_all()

# Stop watching
manager.stop()
```

### Custom Validation

```python
from pr_agent.config.hot_reload import ConfigWatcher

def validate_config(config: dict) -> bool:
    """Custom validation logic"""
    # Check required fields
    if "database" not in config:
        print("Error: database configuration missing")
        return False
    
    # Check value ranges
    if config.get("max_workers", 0) > 100:
        print("Error: max_workers too high")
        return False
    
    # Validate URLs
    if "api_url" in config:
        if not config["api_url"].startswith("https://"):
            print("Error: api_url must use HTTPS")
            return False
    
    return True

# Create watcher with custom validator
watcher = ConfigWatcher(
    config_path="configuration.toml",
    validator=validate_config
)

# Invalid configurations will be rejected
watcher.start()
```

### Rollback on Failure

```python
from pr_agent.config.hot_reload import ConfigWatcher

# Store current working configuration
current_config = None

def on_config_change(new_config: dict):
    global current_config
    
    try:
        # Try to apply new configuration
        apply_config(new_config)
        current_config = new_config
        print("Configuration applied successfully")
    except Exception as e:
        print(f"Failed to apply configuration: {e}")
        
        # Rollback to previous configuration
        if current_config:
            apply_config(current_config)
            print("Rolled back to previous configuration")
        
        raise  # Re-raise to prevent watcher from updating

watcher = ConfigWatcher("configuration.toml")
watcher.register_callback(on_config_change)
watcher.start()
```

## Integration Examples

### FastAPI Application

```python
from fastapi import FastAPI
from pr_agent.config.hot_reload import HotReloadManager
from pr_agent.settings.configuration import get_settings

app = FastAPI()
settings = get_settings()
hot_reload = None

@app.on_event("startup")
async def startup_event():
    global hot_reload
    
    # Initialize hot reload
    hot_reload = HotReloadManager(
        config_path="configuration.toml",
        check_interval=5.0
    )
    
    # Register callback to update settings
    def on_config_change(config: dict):
        settings.reload(config)
        print("Settings reloaded from configuration")
    
    hot_reload.register_callback(on_config_change)
    hot_reload.start()
    
    print("Hot reload started")

@app.on_event("shutdown")
async def shutdown_event():
    if hot_reload:
        hot_reload.stop()
        print("Hot reload stopped")

@app.get("/config")
async def get_config():
    return settings.config
```

### Background Service

```python
import asyncio
from pr_agent.config.hot_reload import HotReloadManager

class BackgroundService:
    def __init__(self):
        self.config = {}
        self.hot_reload = HotReloadManager("configuration.toml")
        self.hot_reload.register_callback(self.on_config_change)
    
    def on_config_change(self, config: dict):
        """Handle configuration changes"""
        print("Configuration updated")
        self.config = config
        
        # Update service parameters
        self.update_workers(config.get("workers", 4))
        self.update_timeout(config.get("timeout", 30))
    
    def update_workers(self, count: int):
        print(f"Updating worker count to {count}")
        # Adjust worker pool size
    
    def update_timeout(self, seconds: int):
        print(f"Updating timeout to {seconds}s")
        # Update timeout settings
    
    async def start(self):
        self.hot_reload.start()
        
        # Service main loop
        while True:
            await self.process_tasks()
            await asyncio.sleep(1)
    
    async def stop(self):
        self.hot_reload.stop()

# Run service
service = BackgroundService()
asyncio.run(service.start())
```

### Database Connection Pool

```python
from pr_agent.config.hot_reload import ConfigWatcher
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.watcher = ConfigWatcher("configuration.toml")
        self.watcher.register_callback(self.on_config_change)
        self.watcher.start()
        
        # Initialize with current config
        self.reload_engine(self.watcher.get_current_config())
    
    def on_config_change(self, config: dict):
        """Reload database engine when config changes"""
        db_config = config.get("database", {})
        
        # Check if database config actually changed
        if self.has_db_config_changed(db_config):
            print("Database configuration changed, reloading engine")
            self.reload_engine(config)
    
    def reload_engine(self, config: dict):
        """Create new database engine with updated config"""
        db_config = config.get("database", {})
        
        # Dispose old engine
        if self.engine:
            self.engine.dispose()
        
        # Create new engine with updated settings
        self.engine = create_engine(
            db_config.get("url", "sqlite:///pr_agent.db"),
            poolclass=QueuePool,
            pool_size=db_config.get("pool_size", 5),
            max_overflow=db_config.get("max_overflow", 10),
            pool_timeout=db_config.get("pool_timeout", 30)
        )
        
        print("Database engine reloaded")
    
    def has_db_config_changed(self, new_config: dict) -> bool:
        # Compare with current engine settings
        # Return True if changed
        return True
```

## Best Practices

### Configuration Design

1. **Atomic Changes**: Make configuration changes atomic to avoid partial updates
2. **Validation**: Always validate configuration before applying
3. **Defaults**: Provide sensible defaults for all configuration values
4. **Documentation**: Document all configuration options and their effects
5. **Versioning**: Consider configuration versioning for compatibility

### Hot Reload Strategy

1. **Check Interval**: Balance between responsiveness and overhead (5-10 seconds recommended)
2. **Validation**: Always validate before applying to prevent invalid configurations
3. **Rollback**: Implement rollback mechanism for failed updates
4. **Notifications**: Log configuration changes for audit trail
5. **Testing**: Test configuration changes in staging before production

### Production Considerations

1. **Monitoring**: Monitor hot reload events and failures
2. **Alerting**: Alert on repeated reload failures
3. **Rate Limiting**: Prevent configuration thrashing with rate limits
4. **Backup**: Keep backup of last known good configuration
5. **Gradual Rollout**: Test configuration changes on subset of instances first

## Troubleshooting

### Configuration Not Reloading

```bash
# Check if hot reload is enabled
curl http://localhost:8000/api/config/hot-reload/status

# Check file permissions
ls -la configuration.toml

# Check if file is being watched
curl http://localhost:8000/api/config/hot-reload/files

# Force reload
curl -X POST http://localhost:8000/api/config/hot-reload/reload

# Check logs for errors
tail -f logs/pr_agent.log | grep "hot_reload"
```

### Validation Failures

```python
# Enable debug logging
import logging
logging.getLogger("pr_agent.config.hot_reload").setLevel(logging.DEBUG)

# Test configuration manually
from pr_agent.config.validation import validate_config

try:
    validate_config("configuration.toml")
    print("Configuration is valid")
except Exception as e:
    print(f"Validation failed: {e}")
```

### Performance Issues

```python
# Increase check interval to reduce overhead
hot_reload = HotReloadManager(
    config_path="configuration.toml",
    check_interval=30.0  # Check every 30 seconds instead of 5
)

# Reduce number of watched files
# Only watch files that actually need hot reload
hot_reload.remove_file("rarely_changed.toml")

# Disable validation if not needed (not recommended)
watcher = ConfigWatcher(
    config_path="configuration.toml",
    validator=None  # Skip validation
)
```

### Memory Leaks

```python
# Ensure watchers are properly stopped
try:
    hot_reload.start()
    # ... application code ...
finally:
    hot_reload.stop()  # Always stop watcher

# Clear callbacks when no longer needed
hot_reload.clear_callbacks()

# Use context manager for automatic cleanup
from contextlib import contextmanager

@contextmanager
def hot_reload_context(config_path: str):
    manager = HotReloadManager(config_path)
    manager.start()
    try:
        yield manager
    finally:
        manager.stop()

# Usage
with hot_reload_context("configuration.toml") as hr:
    # Application code
    pass
# Automatically stopped when exiting context
```

## Advanced Features

### Conditional Reloading

```python
from pr_agent.config.hot_reload import ConfigWatcher

class ConditionalWatcher(ConfigWatcher):
    def should_reload(self, new_config: dict) -> bool:
        """Only reload if specific fields changed"""
        old_config = self.get_current_config()
        
        # Only reload if critical fields changed
        critical_fields = ["database", "cache", "api_url"]
        
        for field in critical_fields:
            if old_config.get(field) != new_config.get(field):
                return True
        
        return False
    
    def reload(self) -> dict:
        new_config = super().reload()
        
        if not self.should_reload(new_config):
            print("No critical changes detected, skipping reload")
            return self.get_current_config()
        
        return new_config
```

### Staged Rollout

```python
import random
from pr_agent.config.hot_reload import HotReloadManager

class StagedReloadManager(HotReloadManager):
    def __init__(self, *args, rollout_percentage: float = 100.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.rollout_percentage = rollout_percentage
    
    def should_apply_update(self) -> bool:
        """Randomly decide if this instance should apply update"""
        return random.random() * 100 < self.rollout_percentage

# Apply updates to 10% of instances first
staged_reload = StagedReloadManager(
    config_path="configuration.toml",
    rollout_percentage=10.0
)
```

### Configuration Diff

```python
from pr_agent.config.hot_reload import ConfigWatcher
import json

def get_config_diff(old: dict, new: dict, path: str = "") -> list:
    """Get list of changed configuration keys"""
    changes = []
    
    # Check for added/changed keys
    for key, value in new.items():
        full_path = f"{path}.{key}" if path else key
        
        if key not in old:
            changes.append(f"Added: {full_path} = {value}")
        elif old[key] != value:
            if isinstance(value, dict) and isinstance(old[key], dict):
                changes.extend(get_config_diff(old[key], value, full_path))
            else:
                changes.append(f"Changed: {full_path} = {old[key]} -> {value}")
    
    # Check for removed keys
    for key in old:
        if key not in new:
            full_path = f"{path}.{key}" if path else key
            changes.append(f"Removed: {full_path}")
    
    return changes

# Use in callback
def on_config_change(new_config: dict):
    old_config = watcher.get_current_config()
    changes = get_config_diff(old_config, new_config)
    
    print("Configuration changes:")
    for change in changes:
        print(f"  - {change}")
```

## See Also

- [Configuration Guide](../docs/CONFIGURATION.md)
- [Health Monitoring](HEALTH_MONITORING.md)
- [Deployment Guide](DEPLOYMENT.md)
- [API Documentation](API.md)
