"""
Unit tests for configuration hot reload system.
"""

import pytest
import tempfile
import os
import time
from pathlib import Path
from unittest.mock import Mock, patch

from pr_agent.config.hot_reload import ConfigWatcher, HotReloadManager


@pytest.fixture
def temp_config():
    """Create temporary configuration file."""
    fd, path = tempfile.mkstemp(suffix='.toml')
    os.close(fd)

    # Write initial config
    with open(path, 'w') as f:
        f.write('[test]\nvalue = 1\n')

    yield path

    # Cleanup
    if os.path.exists(path):
        try:
            os.unlink(path)
        except:
            pass


class TestConfigWatcher:
    """Test ConfigWatcher class."""

    def test_watcher_initialization(self, temp_config):
        """Test watcher initialization."""
        watcher = ConfigWatcher(temp_config, check_interval=1)

        assert watcher.config_path == Path(temp_config)
        assert watcher.check_interval == 1
        assert watcher.is_running is False
        assert len(watcher.callbacks) == 0

    def test_add_callback(self, temp_config):
        """Test adding callback."""
        watcher = ConfigWatcher(temp_config)
        callback = Mock()

        watcher.add_callback(callback)

        assert callback in watcher.callbacks
        assert len(watcher.callbacks) == 1

    def test_remove_callback(self, temp_config):
        """Test removing callback."""
        watcher = ConfigWatcher(temp_config)
        callback = Mock()

        watcher.add_callback(callback)
        watcher.remove_callback(callback)

        assert callback not in watcher.callbacks
        assert len(watcher.callbacks) == 0

    def test_calculate_hash(self, temp_config):
        """Test hash calculation."""
        watcher = ConfigWatcher(temp_config)

        hash1 = watcher._calculate_hash()
        assert hash1 is not None
        assert len(hash1) == 32  # MD5 hash length

        # Same file should produce same hash
        hash2 = watcher._calculate_hash()
        assert hash1 == hash2

    def test_calculate_hash_changes(self, temp_config):
        """Test hash changes when file is modified."""
        watcher = ConfigWatcher(temp_config)

        hash1 = watcher._calculate_hash()

        # Modify file
        with open(temp_config, 'a') as f:
            f.write('\n[new]\nvalue = 2\n')

        hash2 = watcher._calculate_hash()
        assert hash1 != hash2

    def test_load_config(self, temp_config):
        """Test loading configuration."""
        watcher = ConfigWatcher(temp_config)

        config = watcher._load_config()

        assert 'test' in config
        assert config['test']['value'] == 1

    def test_check_for_changes_no_change(self, temp_config):
        """Test checking for changes when file hasn't changed."""
        watcher = ConfigWatcher(temp_config)
        watcher.last_hash = watcher._calculate_hash()
        watcher.last_modified = Path(temp_config).stat().st_mtime

        changed = watcher._check_for_changes()

        assert changed is False

    def test_check_for_changes_with_change(self, temp_config):
        """Test checking for changes when file has changed."""
        watcher = ConfigWatcher(temp_config)
        watcher.last_hash = watcher._calculate_hash()
        watcher.last_modified = Path(temp_config).stat().st_mtime

        # Wait a bit to ensure mtime changes
        time.sleep(0.1)

        # Modify file
        with open(temp_config, 'a') as f:
            f.write('\n[new]\nvalue = 2\n')

        changed = watcher._check_for_changes()

        assert changed is True

    def test_start_stop(self, temp_config):
        """Test starting and stopping watcher."""
        watcher = ConfigWatcher(temp_config, check_interval=1)

        watcher.start()
        assert watcher.is_running is True
        assert watcher.watch_thread is not None

        watcher.stop()
        assert watcher.is_running is False

    def test_trigger_reload(self, temp_config):
        """Test triggering reload callbacks."""
        watcher = ConfigWatcher(temp_config)
        callback = Mock()
        watcher.add_callback(callback)

        watcher._trigger_reload()

        callback.assert_called_once()
        args = callback.call_args[0]
        assert 'test' in args[0]

    def test_trigger_reload_with_error(self, temp_config):
        """Test reload with callback error."""
        watcher = ConfigWatcher(temp_config)
        callback = Mock(side_effect=Exception("Test error"))
        watcher.add_callback(callback)

        # Should not raise exception
        watcher._trigger_reload()

        callback.assert_called_once()

    def test_get_status(self, temp_config):
        """Test getting watcher status."""
        watcher = ConfigWatcher(temp_config, check_interval=5)
        watcher.start()

        status = watcher.get_status()

        assert status["running"] is True
        assert status["config_path"] == str(temp_config)
        assert status["check_interval"] == 5
        assert status["callbacks_count"] == 0
        assert status["last_hash"] is not None

        watcher.stop()

    def test_auto_start(self, temp_config):
        """Test auto-start functionality."""
        watcher = ConfigWatcher(temp_config, auto_start=True)

        assert watcher.is_running is True

        watcher.stop()

    def test_start_nonexistent_file(self):
        """Test starting watcher with nonexistent file."""
        watcher = ConfigWatcher("/nonexistent/config.toml")

        watcher.start()

        assert watcher.is_running is False


class TestHotReloadManager:
    """Test HotReloadManager class."""

    def test_manager_initialization(self, temp_config):
        """Test manager initialization."""
        manager = HotReloadManager(temp_config)

        assert manager.config_path == temp_config
        assert manager.watcher is not None
        assert len(manager.reload_handlers) == 0
        assert len(manager.reload_history) == 0

    def test_register_handler(self, temp_config):
        """Test registering reload handler."""
        manager = HotReloadManager(temp_config)
        handler = Mock()

        manager.register_handler("test_handler", handler)

        assert "test_handler" in manager.reload_handlers
        assert manager.reload_handlers["test_handler"] == handler

    def test_unregister_handler(self, temp_config):
        """Test unregistering reload handler."""
        manager = HotReloadManager(temp_config)
        handler = Mock()

        manager.register_handler("test_handler", handler)
        manager.unregister_handler("test_handler")

        assert "test_handler" not in manager.reload_handlers

    def test_on_config_change(self, temp_config):
        """Test handling configuration change."""
        manager = HotReloadManager(temp_config)
        handler = Mock()
        manager.register_handler("test_handler", handler)

        new_config = {"test": {"value": 2}}
        manager._on_config_change(new_config)

        handler.assert_called_once_with(new_config)
        assert len(manager.reload_history) == 1
        assert "test_handler" in manager.reload_history[0]["handlers_called"]

    def test_on_config_change_with_error(self, temp_config):
        """Test handling config change with handler error."""
        manager = HotReloadManager(temp_config)
        handler = Mock(side_effect=Exception("Test error"))
        manager.register_handler("test_handler", handler)

        new_config = {"test": {"value": 2}}
        manager._on_config_change(new_config)

        handler.assert_called_once()
        assert len(manager.reload_history) == 1
        assert len(manager.reload_history[0]["errors"]) > 0

    def test_get_reload_history(self, temp_config):
        """Test getting reload history."""
        manager = HotReloadManager(temp_config)

        # Trigger multiple reloads
        for i in range(5):
            manager._on_config_change({"test": {"value": i}})

        history = manager.get_reload_history(limit=3)

        assert len(history) == 3
        assert all("timestamp" in event for event in history)

    def test_reload_history_limit(self, temp_config):
        """Test reload history size limit."""
        manager = HotReloadManager(temp_config)
        manager.max_history = 10

        # Trigger more reloads than max_history
        for i in range(15):
            manager._on_config_change({"test": {"value": i}})

        assert len(manager.reload_history) == 10

    def test_get_status(self, temp_config):
        """Test getting manager status."""
        manager = HotReloadManager(temp_config)
        handler = Mock()
        manager.register_handler("test_handler", handler)

        status = manager.get_status()

        assert "watcher" in status
        assert "handlers" in status
        assert "test_handler" in status["handlers"]
        assert status["reload_count"] == 0

    def test_start_stop(self, temp_config):
        """Test starting and stopping manager."""
        manager = HotReloadManager(temp_config)

        manager.start()
        assert manager.watcher.is_running is True

        manager.stop()
        assert manager.watcher.is_running is False

    def test_integration_reload_on_file_change(self, temp_config):
        """Test end-to-end reload on file change."""
        manager = HotReloadManager(temp_config)
        handler = Mock()
        manager.register_handler("test_handler", handler)

        manager.start()

        # Wait a bit for watcher to initialize
        time.sleep(0.2)

        # Modify config file
        with open(temp_config, 'w') as f:
            f.write('[test]\nvalue = 999\n')

        # Wait for watcher to detect change (check_interval + buffer)
        time.sleep(6)

        manager.stop()

        # Handler should have been called
        assert handler.call_count > 0
        assert len(manager.reload_history) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
