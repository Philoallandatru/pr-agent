# Plugin Development Guide

This guide explains how to develop custom plugins for PR-Agent to extend its functionality.

## Table of Contents

- [Overview](#overview)
- [Plugin Types](#plugin-types)
- [Creating a Plugin](#creating-a-plugin)
- [Plugin Lifecycle](#plugin-lifecycle)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Best Practices](#best-practices)
- [Testing](#testing)
- [Deployment](#deployment)

## Overview

PR-Agent's plugin system allows you to extend its functionality without modifying the core codebase. Plugins can:

- Add custom review rules
- Send notifications to external services
- Analyze code with custom tools
- Integrate with third-party APIs
- Customize PR review behavior

### Architecture

The plugin system is based on a hook-based architecture:

```
┌─────────────────┐
│  Plugin Manager │
├─────────────────┤
│ - Load plugins  │
│ - Execute hooks │
│ - Manage state  │
└────────┬────────┘
         │
    ┌────┴────┐
    │  Hooks  │
    └────┬────┘
         │
    ┌────┴────────────────────┐
    │                         │
┌───▼────┐              ┌─────▼──────┐
│ Plugin │              │   Plugin   │
│   A    │              │     B      │
└────────┘              └────────────┘
```

## Plugin Types

PR-Agent supports three main plugin types:

### 1. Review Rule Plugins

Add custom code review rules and checks.

```python
from pr_agent.plugins import ReviewRulePlugin

class MyReviewRule(ReviewRulePlugin):
    version = "1.0.0"
    description = "Custom review rule"
    author = "Your Name"
    
    def evaluate(self, pr_data, diff):
        # Your review logic here
        return {
            "passed": True,
            "severity": "info",
            "message": "Check passed",
            "suggestions": []
        }
```

### 2. Notification Plugins

Send notifications to external services.

```python
from pr_agent.plugins import NotificationPlugin

class MyNotification(NotificationPlugin):
    version = "1.0.0"
    description = "Custom notification"
    author = "Your Name"
    
    async def send_notification(self, event_type, data):
        # Your notification logic here
        return True
```

### 3. Analyzer Plugins

Analyze code with custom tools.

```python
from pr_agent.plugins import AnalyzerPlugin

class MyAnalyzer(AnalyzerPlugin):
    version = "1.0.0"
    description = "Custom analyzer"
    author = "Your Name"
    
    def analyze(self, file_path, content, language):
        # Your analysis logic here
        return {
            "issues": [],
            "metrics": {},
            "suggestions": []
        }
```

## Creating a Plugin

### Step 1: Choose a Base Class

Select the appropriate base class for your plugin:

- `ReviewRulePlugin` - For custom review rules
- `NotificationPlugin` - For notifications
- `AnalyzerPlugin` - For code analysis
- `PluginBase` - For generic plugins

### Step 2: Implement Required Methods

All plugins must implement:

```python
def initialize(self) -> bool:
    """Initialize the plugin. Return True if successful."""
    pass

def cleanup(self):
    """Clean up resources when plugin is unloaded."""
    pass
```

### Step 3: Add Plugin Metadata

```python
class MyPlugin(PluginBase):
    version = "1.0.0"
    description = "What your plugin does"
    author = "Your Name"
    dependencies = ["requests>=2.28.0"]  # Optional
```

### Step 4: Implement Plugin Logic

Implement the type-specific methods:

**Review Rule Plugin:**
```python
def evaluate(self, pr_data: Dict[str, Any], diff: str) -> Dict[str, Any]:
    """
    Evaluate PR against your rule.
    
    Args:
        pr_data: PR metadata (repository, pr_number, etc.)
        diff: The PR diff content
        
    Returns:
        {
            "passed": bool,
            "severity": "info" | "warning" | "error",
            "message": str,
            "suggestions": List[str]
        }
    """
```

**Notification Plugin:**
```python
async def send_notification(self, event_type: str, data: Dict[str, Any]) -> bool:
    """
    Send notification for an event.
    
    Args:
        event_type: Type of event (review_completed, pr_created, etc.)
        data: Event data
        
    Returns:
        True if notification sent successfully
    """
```

**Analyzer Plugin:**
```python
def analyze(self, file_path: str, content: str, language: str) -> Dict[str, Any]:
    """
    Analyze code file.
    
    Args:
        file_path: Path to the file
        content: File content
        language: Programming language
        
    Returns:
        {
            "issues": List[Dict],
            "metrics": Dict[str, Any],
            "suggestions": List[str]
        }
    """
```

## Plugin Lifecycle

### 1. Loading

```python
from pr_agent.plugins import PluginManager

manager = PluginManager()
manager.load_plugin(MyPlugin, config={"enabled": True})
```

### 2. Initialization

The `initialize()` method is called when the plugin is loaded.

### 3. Execution

Plugins are executed when relevant events occur:

```python
# Review rules
results = manager.execute_review_rules(pr_data, diff)

# Notifications
await manager.send_notifications("review_completed", data)

# Analyzers
results = manager.analyze_code(file_path, content, language)
```

### 4. Cleanup

The `cleanup()` method is called when the plugin is unloaded.

## API Reference

### PluginBase

Base class for all plugins.

**Attributes:**
- `name: str` - Plugin name (auto-generated from class name)
- `version: str` - Plugin version
- `description: str` - Plugin description
- `author: str` - Plugin author
- `enabled: bool` - Whether plugin is enabled
- `config: Dict[str, Any]` - Plugin configuration

**Methods:**
- `initialize() -> bool` - Initialize plugin
- `cleanup()` - Clean up resources
- `get_metadata() -> Dict[str, Any]` - Get plugin metadata

### PluginManager

Manages plugin lifecycle and execution.

**Methods:**
- `load_plugin(plugin_class, config=None) -> bool` - Load a plugin
- `unload_plugin(plugin_name) -> bool` - Unload a plugin
- `reload_plugin(plugin_name) -> bool` - Reload a plugin
- `get_plugin(plugin_name) -> Optional[PluginBase]` - Get plugin instance
- `get_plugins_by_type(plugin_type) -> List[PluginBase]` - Get plugins by type
- `list_plugins() -> List[Dict]` - List all plugins
- `discover_plugins() -> List[str]` - Discover plugins in plugin directory

## Examples

### Example 1: Security Check Plugin

```python
from pr_agent.plugins import ReviewRulePlugin
import re

class SecurityCheckPlugin(ReviewRulePlugin):
    version = "1.0.0"
    description = "Check for common security issues"
    author = "Security Team"
    
    def initialize(self):
        self.patterns = [
            (r'password\s*=\s*["\'].*["\']', "Hardcoded password detected"),
            (r'api[_-]?key\s*=\s*["\'].*["\']', "Hardcoded API key detected"),
            (r'eval\s*\(', "Use of eval() is dangerous"),
        ]
        return True
    
    def cleanup(self):
        pass
    
    def evaluate(self, pr_data, diff):
        issues = []
        
        for pattern, message in self.patterns:
            matches = re.finditer(pattern, diff, re.IGNORECASE)
            for match in matches:
                issues.append({
                    "line": diff[:match.start()].count('\n') + 1,
                    "message": message,
                    "code": match.group(0)
                })
        
        return {
            "passed": len(issues) == 0,
            "severity": "error" if issues else "info",
            "message": f"Found {len(issues)} security issues" if issues else "No security issues found",
            "suggestions": [f"Line {i['line']}: {i['message']}" for i in issues]
        }
```

### Example 2: Slack Notification Plugin

```python
from pr_agent.plugins import NotificationPlugin
import aiohttp

class SlackNotificationPlugin(NotificationPlugin):
    version = "1.0.0"
    description = "Send notifications to Slack"
    author = "DevOps Team"
    
    def initialize(self):
        self.webhook_url = self.config.get("webhook_url")
        if not self.webhook_url:
            return False
        return True
    
    def cleanup(self):
        pass
    
    async def send_notification(self, event_type, data):
        message = self._format_message(event_type, data)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json={"text": message}
            ) as response:
                return response.status == 200
    
    def _format_message(self, event_type, data):
        if event_type == "review_completed":
            return f"✅ Review completed for PR #{data['pr_number']} in {data['repository']}"
        elif event_type == "pr_created":
            return f"🆕 New PR #{data['pr_number']} created in {data['repository']}"
        else:
            return f"Event: {event_type}"
```

### Example 3: Code Complexity Analyzer

```python
from pr_agent.plugins import AnalyzerPlugin
import ast

class ComplexityAnalyzer(AnalyzerPlugin):
    version = "1.0.0"
    description = "Analyze code complexity"
    author = "Quality Team"
    
    def initialize(self):
        return True
    
    def cleanup(self):
        pass
    
    def analyze(self, file_path, content, language):
        if language != "python":
            return {"issues": [], "metrics": {}, "suggestions": []}
        
        try:
            tree = ast.parse(content)
            complexity = self._calculate_complexity(tree)
            
            issues = []
            if complexity > 10:
                issues.append({
                    "severity": "warning",
                    "message": f"High complexity: {complexity}"
                })
            
            return {
                "issues": issues,
                "metrics": {"complexity": complexity},
                "suggestions": ["Consider refactoring complex functions"]
            }
        except SyntaxError:
            return {"issues": [], "metrics": {}, "suggestions": []}
    
    def _calculate_complexity(self, tree):
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
        return complexity
```

## Best Practices

### 1. Configuration

Use plugin configuration for customizable behavior:

```python
def initialize(self):
    self.threshold = self.config.get("threshold", 10)
    self.enabled_checks = self.config.get("checks", ["all"])
    return True
```

### 2. Error Handling

Always handle errors gracefully:

```python
def evaluate(self, pr_data, diff):
    try:
        # Your logic here
        return {"passed": True, ...}
    except Exception as e:
        return {
            "passed": False,
            "severity": "error",
            "message": f"Plugin error: {str(e)}",
            "suggestions": []
        }
```

### 3. Logging

Use structured logging:

```python
from pr_agent.monitoring import get_logger

logger = get_logger()

def evaluate(self, pr_data, diff):
    logger.info(f"Evaluating PR {pr_data['pr_number']}")
    # Your logic
```

### 4. Performance

- Cache expensive operations
- Use async for I/O operations
- Set reasonable timeouts

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def _expensive_operation(self, data):
    # Cached computation
    pass
```

### 5. Dependencies

Declare dependencies in plugin metadata:

```python
class MyPlugin(PluginBase):
    dependencies = [
        "requests>=2.28.0",
        "beautifulsoup4>=4.11.0"
    ]
```

## Testing

### Unit Tests

```python
import pytest
from my_plugin import MyPlugin

def test_plugin_initialization():
    plugin = MyPlugin()
    assert plugin.initialize() is True

def test_plugin_evaluation():
    plugin = MyPlugin()
    plugin.initialize()
    
    result = plugin.evaluate(
        {"repository": "test/repo", "pr_number": 1},
        "test diff"
    )
    
    assert "passed" in result
    assert "severity" in result
```

### Integration Tests

```python
from pr_agent.plugins import PluginManager

def test_plugin_integration():
    manager = PluginManager()
    manager.load_plugin(MyPlugin)
    
    results = manager.execute_review_rules(pr_data, diff)
    assert len(results) > 0
```

## Deployment

### 1. Package Your Plugin

Create a `setup.py`:

```python
from setuptools import setup

setup(
    name="my-pr-agent-plugin",
    version="1.0.0",
    py_modules=["my_plugin"],
    install_requires=[
        "pr-agent>=1.0.0",
        # Your dependencies
    ],
)
```

### 2. Install Plugin

```bash
pip install my-pr-agent-plugin
```

### 3. Configure Plugin

Add to `configuration.toml`:

```toml
[plugins.my_plugin]
enabled = true
threshold = 10
custom_option = "value"
```

### 4. Load Plugin

```python
from pr_agent.plugins import PluginManager
from my_plugin import MyPlugin

manager = PluginManager()
manager.load_plugin(MyPlugin)
```

### 5. Via API

```bash
# Load plugin
curl -X POST http://localhost:8000/api/plugins/load \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"plugin_name": "MyPlugin", "config": {"enabled": true}}'

# Enable plugin
curl -X POST http://localhost:8000/api/plugins/MyPlugin/enable \
  -H "Authorization: Bearer $TOKEN"
```

## Troubleshooting

### Plugin Not Loading

- Check plugin dependencies are installed
- Verify `initialize()` returns `True`
- Check logs for error messages

### Plugin Not Executing

- Ensure plugin is enabled
- Verify plugin type matches the hook
- Check plugin configuration

### Performance Issues

- Profile plugin execution time
- Add caching for expensive operations
- Use async for I/O operations

## Support

For questions and support:

- GitHub Issues: https://github.com/your-org/pr-agent/issues
- Documentation: https://docs.pr-agent.com
- Community: https://discord.gg/pr-agent
