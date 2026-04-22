"""
Unit tests for plugin system.
"""

import pytest
import tempfile
from pathlib import Path
from typing import Any, Dict

from pr_agent.plugins import (
    PluginBase,
    ReviewRulePlugin,
    NotificationPlugin,
    AnalyzerPlugin,
    PluginManager,
)


class TestReviewRule(ReviewRulePlugin):
    """Test review rule plugin."""

    version = "1.0.0"
    description = "Test plugin"
    author = "Test"

    def initialize(self) -> bool:
        return True

    def cleanup(self):
        pass

    def evaluate(self, pr_data: Dict[str, Any], diff: str) -> Dict[str, Any]:
        return {
            "passed": True,
            "severity": "info",
            "message": "Test passed",
            "suggestions": [],
        }


class TestNotification(NotificationPlugin):
    """Test notification plugin."""

    version = "1.0.0"
    description = "Test notification"
    author = "Test"

    def initialize(self) -> bool:
        return True

    def cleanup(self):
        pass

    async def send_notification(
        self, event_type: str, data: Dict[str, Any]
    ) -> bool:
        return True


class TestAnalyzer(AnalyzerPlugin):
    """Test analyzer plugin."""

    version = "1.0.0"
    description = "Test analyzer"
    author = "Test"

    def initialize(self) -> bool:
        return True

    def cleanup(self):
        pass

    def analyze(
        self, file_path: str, content: str, language: str
    ) -> Dict[str, Any]:
        return {"issues": [], "metrics": {}, "suggestions": []}


class TestPluginManager:
    """Test PluginManager class."""

    def test_load_plugin(self):
        """Test loading a plugin."""
        manager = PluginManager()
        result = manager.load_plugin(TestReviewRule)
        assert result is True
        assert "TestReviewRule" in manager.plugins

    def test_load_plugin_with_config(self):
        """Test loading plugin with configuration."""
        manager = PluginManager()
        config = {"enabled": True, "custom_option": "value"}
        result = manager.load_plugin(TestReviewRule, config)
        assert result is True
        plugin = manager.get_plugin("TestReviewRule")
        assert plugin.config["custom_option"] == "value"

    def test_load_disabled_plugin(self):
        """Test loading disabled plugin."""
        manager = PluginManager()
        config = {"enabled": False}
        result = manager.load_plugin(TestReviewRule, config)
        assert result is False
        assert "TestReviewRule" not in manager.plugins

    def test_unload_plugin(self):
        """Test unloading a plugin."""
        manager = PluginManager()
        manager.load_plugin(TestReviewRule)
        result = manager.unload_plugin("TestReviewRule")
        assert result is True
        assert "TestReviewRule" not in manager.plugins

    def test_unload_nonexistent_plugin(self):
        """Test unloading non-existent plugin."""
        manager = PluginManager()
        result = manager.unload_plugin("NonExistent")
        assert result is False

    def test_get_plugin(self):
        """Test getting a plugin."""
        manager = PluginManager()
        manager.load_plugin(TestReviewRule)
        plugin = manager.get_plugin("TestReviewRule")
        assert plugin is not None
        assert isinstance(plugin, TestReviewRule)

    def test_get_nonexistent_plugin(self):
        """Test getting non-existent plugin."""
        manager = PluginManager()
        plugin = manager.get_plugin("NonExistent")
        assert plugin is None

    def test_get_plugins_by_type(self):
        """Test getting plugins by type."""
        manager = PluginManager()
        manager.load_plugin(TestReviewRule)
        manager.load_plugin(TestNotification)
        manager.load_plugin(TestAnalyzer)

        review_plugins = manager.get_plugins_by_type("review_rules")
        assert len(review_plugins) == 1
        assert isinstance(review_plugins[0], ReviewRulePlugin)

        notification_plugins = manager.get_plugins_by_type("notifications")
        assert len(notification_plugins) == 1
        assert isinstance(notification_plugins[0], NotificationPlugin)

        analyzer_plugins = manager.get_plugins_by_type("analyzers")
        assert len(analyzer_plugins) == 1
        assert isinstance(analyzer_plugins[0], AnalyzerPlugin)

    def test_execute_review_rules(self):
        """Test executing review rules."""
        manager = PluginManager()
        manager.load_plugin(TestReviewRule)

        pr_data = {"repository": "test/repo", "pr_number": 1}
        diff = "test diff"

        results = manager.execute_review_rules(pr_data, diff)
        assert len(results) == 1
        assert results[0]["passed"] is True
        assert results[0]["plugin"] == "TestReviewRule"

    @pytest.mark.asyncio
    async def test_send_notifications(self):
        """Test sending notifications."""
        manager = PluginManager()
        manager.load_plugin(TestNotification)

        event_type = "review_completed"
        data = {"repository": "test/repo", "pr_number": 1}

        results = await manager.send_notifications(event_type, data)
        assert len(results) == 1
        assert results["TestNotification"] is True

    def test_analyze_code(self):
        """Test analyzing code."""
        manager = PluginManager()
        manager.load_plugin(TestAnalyzer)

        file_path = "test.py"
        content = "def test(): pass"
        language = "python"

        results = manager.analyze_code(file_path, content, language)
        assert len(results) == 1
        assert results[0]["plugin"] == "TestAnalyzer"
        assert "issues" in results[0]

    def test_list_plugins(self):
        """Test listing plugins."""
        manager = PluginManager()
        manager.load_plugin(TestReviewRule)
        manager.load_plugin(TestNotification)

        plugins = manager.list_plugins()
        assert len(plugins) == 2
        assert all("name" in p for p in plugins)
        assert all("version" in p for p in plugins)

    def test_reload_plugin(self):
        """Test reloading a plugin."""
        manager = PluginManager()
        manager.load_plugin(TestReviewRule)

        result = manager.reload_plugin("TestReviewRule")
        assert result is True
        assert "TestReviewRule" in manager.plugins

    def test_reload_nonexistent_plugin(self):
        """Test reloading non-existent plugin."""
        manager = PluginManager()
        result = manager.reload_plugin("NonExistent")
        assert result is False

    def test_plugin_metadata(self):
        """Test plugin metadata."""
        manager = PluginManager()
        manager.load_plugin(TestReviewRule)

        plugin = manager.get_plugin("TestReviewRule")
        metadata = plugin.get_metadata()

        assert metadata["name"] == "TestReviewRule"
        assert metadata["version"] == "1.0.0"
        assert metadata["description"] == "Test plugin"
        assert metadata["author"] == "Test"
        assert metadata["enabled"] is True

    def test_discover_plugins(self):
        """Test plugin discovery."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir)

            # Create a test plugin file
            plugin_file = plugin_dir / "test_plugin.py"
            plugin_file.write_text(
                """
from pr_agent.plugins import ReviewRulePlugin

class DiscoveredPlugin(ReviewRulePlugin):
    def initialize(self):
        return True

    def cleanup(self):
        pass

    def evaluate(self, pr_data, diff):
        return {"passed": True, "severity": "info", "message": "OK", "suggestions": []}
"""
            )

            manager = PluginManager(plugin_dir=str(plugin_dir))
            discovered = manager.discover_plugins()

            assert len(discovered) > 0
            assert any("DiscoveredPlugin" in p for p in discovered)
