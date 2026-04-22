"""
Configuration hot reload system.

This module provides hot reload capabilities for configuration files,
allowing runtime configuration updates without service restart.
"""

import os
import time
import threading
import hashlib
import logging
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timezone
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:
    try:
        import tomli as tomllib  # Fallback for older Python
    except ImportError:
        import toml as tomllib  # Final fallback

logger = logging.getLogger(__name__)


class ConfigWatcher:
    """
    Watch configuration files for changes and trigger reload callbacks.

    Supports:
    - File modification detection via hash comparison
    - Multiple callback registration
    - Automatic periodic checking
    - Thread-safe operations
    """

    def __init__(
        self,
        config_path: str,
        check_interval: int = 5,
        auto_start: bool = False
    ):
        """
        Initialize configuration watcher.

        Args:
            config_path: Path to configuration file to watch
            check_interval: Check interval in seconds (default: 5)
            auto_start: Automatically start watching (default: False)
        """
        self.config_path = Path(config_path)
        self.check_interval = check_interval
        self.callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.last_hash: Optional[str] = None
        self.last_modified: Optional[float] = None
        self.is_running = False
        self.watch_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        if auto_start:
            self.start()

    def add_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Add a callback to be called when configuration changes.

        Args:
            callback: Function that takes new config dict as parameter
        """
        with self._lock:
            self.callbacks.append(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.info(f"Added config reload callback: {callback_name}")

    def remove_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Remove a previously registered callback.

        Args:
            callback: Callback function to remove
        """
        with self._lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
                callback_name = getattr(callback, '__name__', repr(callback))
                logger.info(f"Removed config reload callback: {callback_name}")

    def start(self) -> None:
        """Start watching configuration file for changes."""
        if self.is_running:
            logger.warning("Config watcher already running")
            return

        if not self.config_path.exists():
            logger.error(f"Config file not found: {self.config_path}")
            return

        self.is_running = True
        self.last_hash = self._calculate_hash()
        self.last_modified = self.config_path.stat().st_mtime

        self.watch_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="ConfigWatcher"
        )
        self.watch_thread.start()
        logger.info(f"Started watching config file: {self.config_path}")

    def stop(self) -> None:
        """Stop watching configuration file."""
        if not self.is_running:
            return

        self.is_running = False
        if self.watch_thread:
            self.watch_thread.join(timeout=self.check_interval + 1)
        logger.info("Stopped config watcher")

    def _watch_loop(self) -> None:
        """Main watch loop running in separate thread."""
        while self.is_running:
            try:
                if self._check_for_changes():
                    self._trigger_reload()
            except Exception as e:
                logger.error(f"Error in config watch loop: {e}")

            time.sleep(self.check_interval)

    def _check_for_changes(self) -> bool:
        """
        Check if configuration file has changed.

        Returns:
            True if file has changed, False otherwise
        """
        if not self.config_path.exists():
            logger.warning(f"Config file disappeared: {self.config_path}")
            return False

        # Check modification time first (faster)
        current_mtime = self.config_path.stat().st_mtime
        if current_mtime == self.last_modified:
            return False

        # Modification time changed, verify with hash
        current_hash = self._calculate_hash()
        if current_hash != self.last_hash:
            self.last_hash = current_hash
            self.last_modified = current_mtime
            return True

        return False

    def _calculate_hash(self) -> str:
        """
        Calculate hash of configuration file.

        Returns:
            MD5 hash of file contents
        """
        hasher = hashlib.md5()
        with open(self.config_path, 'rb') as f:
            hasher.update(f.read())
        return hasher.hexdigest()

    def _trigger_reload(self) -> None:
        """Load new configuration and trigger callbacks."""
        try:
            # Load new configuration
            new_config = self._load_config()

            logger.info(f"Configuration changed, reloading from {self.config_path}")

            # Call all registered callbacks
            with self._lock:
                for callback in self.callbacks:
                    try:
                        callback(new_config)
                    except Exception as e:
                        callback_name = getattr(callback, '__name__', repr(callback))
                        logger.error(f"Error in reload callback {callback_name}: {e}")

        except Exception as e:
            logger.error(f"Failed to reload configuration: {e}")

    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary

        Raises:
            Exception if loading fails
        """
        # tomllib (Python 3.11+) requires binary mode
        if hasattr(tomllib, 'load'):
            with open(self.config_path, 'rb') as f:
                return tomllib.load(f)
        else:
            # toml library uses text mode
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return tomllib.load(f)

    def get_status(self) -> Dict[str, Any]:
        """
        Get current watcher status.

        Returns:
            Status dictionary with watcher information
        """
        return {
            "running": self.is_running,
            "config_path": str(self.config_path),
            "check_interval": self.check_interval,
            "callbacks_count": len(self.callbacks),
            "last_modified": (
                datetime.fromtimestamp(self.last_modified, tz=timezone.utc).isoformat()
                if self.last_modified else None
            ),
            "last_hash": self.last_hash
        }


class HotReloadManager:
    """
    Manage hot reload for multiple configuration aspects.

    Provides centralized management of configuration reloading
    with support for different reload strategies.
    """

    def __init__(self, config_path: str):
        """
        Initialize hot reload manager.

        Args:
            config_path: Path to main configuration file
        """
        self.config_path = config_path
        self.watcher = ConfigWatcher(config_path)
        self.reload_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.reload_history: List[Dict[str, Any]] = []
        self.max_history = 50

        # Register default reload callback
        self.watcher.add_callback(self._on_config_change)

    def register_handler(
        self,
        name: str,
        handler: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Register a reload handler for specific configuration section.

        Args:
            name: Handler name/identifier
            handler: Function to call with new config
        """
        self.reload_handlers[name] = handler
        logger.info(f"Registered reload handler: {name}")

    def unregister_handler(self, name: str) -> None:
        """
        Unregister a reload handler.

        Args:
            name: Handler name to remove
        """
        if name in self.reload_handlers:
            del self.reload_handlers[name]
            logger.info(f"Unregistered reload handler: {name}")

    def start(self) -> None:
        """Start hot reload monitoring."""
        self.watcher.start()

    def stop(self) -> None:
        """Stop hot reload monitoring."""
        self.watcher.stop()

    def _on_config_change(self, new_config: Dict[str, Any]) -> None:
        """
        Handle configuration change event.

        Args:
            new_config: New configuration dictionary
        """
        reload_time = datetime.now(timezone.utc)

        # Track reload event
        reload_event = {
            "timestamp": reload_time.isoformat(),
            "handlers_called": [],
            "errors": []
        }

        # Call all registered handlers
        for name, handler in self.reload_handlers.items():
            try:
                handler(new_config)
                reload_event["handlers_called"].append(name)
                logger.info(f"Successfully reloaded: {name}")
            except Exception as e:
                error_msg = f"Failed to reload {name}: {str(e)}"
                reload_event["errors"].append(error_msg)
                logger.error(error_msg)

        # Add to history
        self.reload_history.append(reload_event)
        if len(self.reload_history) > self.max_history:
            self.reload_history.pop(0)

    def get_reload_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent reload history.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of reload events
        """
        return self.reload_history[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """
        Get hot reload manager status.

        Returns:
            Status dictionary
        """
        return {
            "watcher": self.watcher.get_status(),
            "handlers": list(self.reload_handlers.keys()),
            "reload_count": len(self.reload_history),
            "last_reload": (
                self.reload_history[-1]["timestamp"]
                if self.reload_history else None
            )
        }


# Global hot reload manager instance
_hot_reload_manager: Optional[HotReloadManager] = None


def get_hot_reload_manager(config_path: Optional[str] = None) -> HotReloadManager:
    """
    Get or create global hot reload manager instance.

    Args:
        config_path: Path to configuration file (required on first call)

    Returns:
        HotReloadManager instance
    """
    global _hot_reload_manager

    if _hot_reload_manager is None:
        if config_path is None:
            raise ValueError("config_path required for first initialization")
        _hot_reload_manager = HotReloadManager(config_path)

    return _hot_reload_manager
