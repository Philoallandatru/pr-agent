"""
Plugin system for PR Agent.

Provides extensible architecture for custom review rules, notification handlers,
and analyzers.
"""

import importlib
import inspect
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class PluginBase(ABC):
    """Base class for all plugins."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.name = self.__class__.__name__

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the plugin. Return True if successful."""
        pass

    @abstractmethod
    def cleanup(self):
        """Cleanup resources when plugin is unloaded."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Return plugin metadata."""
        return {
            "name": self.name,
            "version": getattr(self, "version", "1.0.0"),
            "description": getattr(self, "description", ""),
            "author": getattr(self, "author", ""),
            "enabled": self.enabled,
        }


class ReviewRulePlugin(PluginBase):
    """Base class for custom review rule plugins."""

    @abstractmethod
    def evaluate(self, pr_data: Dict[str, Any], diff: str) -> Dict[str, Any]:
        """
        Evaluate PR against custom rules.

        Returns:
            {
                "passed": bool,
                "severity": "info" | "warning" | "error",
                "message": str,
                "suggestions": List[str]
            }
        """
        pass


class NotificationPlugin(PluginBase):
    """Base class for custom notification handler plugins."""

    @abstractmethod
    async def send_notification(
        self, event_type: str, data: Dict[str, Any]
    ) -> bool:
        """
        Send notification for an event.

        Args:
            event_type: Type of event (review_started, review_completed, etc.)
            data: Event data

        Returns:
            True if notification sent successfully
        """
        pass


class AnalyzerPlugin(PluginBase):
    """Base class for custom code analyzer plugins."""

    @abstractmethod
    def analyze(
        self, file_path: str, content: str, language: str
    ) -> Dict[str, Any]:
        """
        Analyze code file.

        Returns:
            {
                "issues": List[Dict],
                "metrics": Dict[str, Any],
                "suggestions": List[str]
            }
        """
        pass


class PluginManager:
    """Manages plugin lifecycle and execution."""

    def __init__(self, plugin_dir: Optional[str] = None):
        self.plugin_dir = Path(plugin_dir or "./plugins")
        self.plugins: Dict[str, PluginBase] = {}
        self.plugin_types: Dict[str, List[str]] = {
            "review_rules": [],
            "notifications": [],
            "analyzers": [],
        }

    def discover_plugins(self) -> List[str]:
        """Discover available plugins in plugin directory."""
        if not self.plugin_dir.exists():
            logger.warning(f"Plugin directory not found: {self.plugin_dir}")
            return []

        discovered = []
        for plugin_file in self.plugin_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            module_name = plugin_file.stem
            try:
                spec = importlib.util.spec_from_file_location(
                    f"plugins.{module_name}", plugin_file
                )
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find plugin classes
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if (
                            issubclass(obj, PluginBase)
                            and obj is not PluginBase
                            and not inspect.isabstract(obj)
                        ):
                            discovered.append(f"{module_name}.{name}")
                            logger.info(f"Discovered plugin: {module_name}.{name}")

            except Exception as e:
                logger.error(f"Error discovering plugin {module_name}: {e}")

        return discovered

    def load_plugin(
        self, plugin_class: Type[PluginBase], config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Load and initialize a plugin."""
        try:
            plugin = plugin_class(config)
            plugin_name = plugin.name

            if plugin_name in self.plugins:
                logger.warning(f"Plugin {plugin_name} already loaded")
                return False

            if not plugin.enabled:
                logger.info(f"Plugin {plugin_name} is disabled")
                return False

            if plugin.initialize():
                self.plugins[plugin_name] = plugin

                # Categorize plugin
                if isinstance(plugin, ReviewRulePlugin):
                    self.plugin_types["review_rules"].append(plugin_name)
                elif isinstance(plugin, NotificationPlugin):
                    self.plugin_types["notifications"].append(plugin_name)
                elif isinstance(plugin, AnalyzerPlugin):
                    self.plugin_types["analyzers"].append(plugin_name)

                logger.info(f"Loaded plugin: {plugin_name}")
                return True
            else:
                logger.error(f"Failed to initialize plugin: {plugin_name}")
                return False

        except Exception as e:
            logger.error(f"Error loading plugin: {e}")
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin."""
        if plugin_name not in self.plugins:
            logger.warning(f"Plugin not found: {plugin_name}")
            return False

        try:
            plugin = self.plugins[plugin_name]
            plugin.cleanup()

            # Remove from categories
            for plugins in self.plugin_types.values():
                if plugin_name in plugins:
                    plugins.remove(plugin_name)

            del self.plugins[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True

        except Exception as e:
            logger.error(f"Error unloading plugin {plugin_name}: {e}")
            return False

    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Get a loaded plugin by name."""
        return self.plugins.get(plugin_name)

    def get_plugins_by_type(self, plugin_type: str) -> List[PluginBase]:
        """Get all loaded plugins of a specific type."""
        plugin_names = self.plugin_types.get(plugin_type, [])
        return [self.plugins[name] for name in plugin_names if name in self.plugins]

    def execute_review_rules(
        self, pr_data: Dict[str, Any], diff: str
    ) -> List[Dict[str, Any]]:
        """Execute all review rule plugins."""
        results = []
        for plugin in self.get_plugins_by_type("review_rules"):
            try:
                result = plugin.evaluate(pr_data, diff)
                result["plugin"] = plugin.name
                results.append(result)
            except Exception as e:
                logger.error(f"Error executing review rule {plugin.name}: {e}")
                results.append(
                    {
                        "plugin": plugin.name,
                        "passed": False,
                        "severity": "error",
                        "message": f"Plugin error: {str(e)}",
                        "suggestions": [],
                    }
                )
        return results

    async def send_notifications(
        self, event_type: str, data: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Send notifications through all notification plugins."""
        results = {}
        for plugin in self.get_plugins_by_type("notifications"):
            try:
                success = await plugin.send_notification(event_type, data)
                results[plugin.name] = success
            except Exception as e:
                logger.error(f"Error sending notification via {plugin.name}: {e}")
                results[plugin.name] = False
        return results

    def analyze_code(
        self, file_path: str, content: str, language: str
    ) -> List[Dict[str, Any]]:
        """Run all analyzer plugins on code."""
        results = []
        for plugin in self.get_plugins_by_type("analyzers"):
            try:
                result = plugin.analyze(file_path, content, language)
                result["plugin"] = plugin.name
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing with {plugin.name}: {e}")
                results.append(
                    {
                        "plugin": plugin.name,
                        "issues": [],
                        "metrics": {},
                        "suggestions": [],
                        "error": str(e),
                    }
                )
        return results

    def list_plugins(self) -> List[Dict[str, Any]]:
        """List all loaded plugins with metadata."""
        return [plugin.get_metadata() for plugin in self.plugins.values()]

    def reload_plugin(self, plugin_name: str) -> bool:
        """Reload a plugin."""
        if plugin_name not in self.plugins:
            return False

        plugin = self.plugins[plugin_name]
        config = plugin.config
        plugin_class = plugin.__class__

        if self.unload_plugin(plugin_name):
            return self.load_plugin(plugin_class, config)

        return False


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager(plugin_dir: Optional[str] = None) -> PluginManager:
    """Get or create global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager(plugin_dir)
    return _plugin_manager
