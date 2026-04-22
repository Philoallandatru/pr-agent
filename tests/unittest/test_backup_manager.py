"""
Unit tests for backup and restore functionality.
"""

import os
import tempfile
import shutil
from pathlib import Path
import pytest

from pr_agent.backup.manager import BackupManager


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing."""
    temp_dir = tempfile.mkdtemp()
    backup_dir = Path(temp_dir) / "backups"
    data_dir = Path(temp_dir) / "data"
    config_dir = Path(temp_dir) / "config"
    cache_dir = Path(temp_dir) / "cache"
    log_dir = Path(temp_dir) / "logs"

    # Create directories
    backup_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    cache_dir.mkdir(parents=True)
    log_dir.mkdir(parents=True)

    # Create test files
    db_file = data_dir / "test.db"
    db_file.write_text("test database content")

    config_file = config_dir / "config.toml"
    config_file.write_text("test config content")

    cache_file = cache_dir / "cache.txt"
    cache_file.write_text("test cache content")

    log_file = log_dir / "test.log"
    log_file.write_text("test log content")

    yield {
        "temp_dir": temp_dir,
        "backup_dir": backup_dir,
        "db_file": db_file,
        "config_file": config_file,
        "cache_dir": cache_dir,
        "log_dir": log_dir,
    }

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def backup_manager(temp_dirs):
    """Create BackupManager instance with test directories."""
    manager = BackupManager(backup_dir=str(temp_dirs["backup_dir"]))
    manager.db_path = temp_dirs["db_file"]
    manager.config_path = temp_dirs["config_file"]
    manager.tokenizer_cache = temp_dirs["cache_dir"]
    manager.repo_cache = temp_dirs["cache_dir"]
    manager.log_dir = temp_dirs["log_dir"]
    return manager


def test_create_backup_database_only(backup_manager, temp_dirs):
    """Test creating backup with database only."""
    backup_path = backup_manager.create_backup(
        include_db=True,
        include_config=False,
        include_cache=False,
        include_logs=False,
        description="Test backup",
    )

    assert Path(backup_path).exists()
    assert Path(backup_path).stat().st_size > 0


def test_create_backup_all_components(backup_manager, temp_dirs):
    """Test creating backup with all components."""
    backup_path = backup_manager.create_backup(
        include_db=True,
        include_config=True,
        include_cache=True,
        include_logs=True,
        description="Full backup",
    )

    assert Path(backup_path).exists()
    assert Path(backup_path).stat().st_size > 0


def test_list_backups(backup_manager, temp_dirs):
    """Test listing backups."""
    # Create multiple backups
    backup_manager.create_backup(include_db=True, description="Backup 1")
    backup_manager.create_backup(include_db=True, description="Backup 2")

    backups = backup_manager.list_backups()
    assert len(backups) == 2
    assert all("timestamp" in b for b in backups)
    assert all("size_bytes" in b for b in backups)


def test_get_backup_info(backup_manager, temp_dirs):
    """Test getting backup information."""
    backup_path = backup_manager.create_backup(
        include_db=True, description="Test backup"
    )

    info = backup_manager.get_backup_info(backup_path)
    assert "timestamp" in info
    assert "size_bytes" in info
    assert info["description"] == "Test backup"


def test_delete_backup(backup_manager, temp_dirs):
    """Test deleting a backup."""
    backup_path = backup_manager.create_backup(include_db=True)

    assert Path(backup_path).exists()

    backup_manager.delete_backup(backup_path)

    assert not Path(backup_path).exists()


def test_restore_backup_database(backup_manager, temp_dirs):
    """Test restoring database from backup."""
    # Create backup
    backup_path = backup_manager.create_backup(include_db=True, include_config=False)

    # Modify database
    temp_dirs["db_file"].write_text("modified content")

    # Restore backup
    backup_manager.restore_backup(
        backup_path,
        restore_db=True,
        restore_config=False,
        create_backup_before_restore=False,
    )

    # Verify restoration
    assert temp_dirs["db_file"].read_text() == "test database content"


def test_restore_backup_config(backup_manager, temp_dirs):
    """Test restoring configuration from backup."""
    # Create backup
    backup_path = backup_manager.create_backup(include_db=False, include_config=True)

    # Modify config
    temp_dirs["config_file"].write_text("modified config")

    # Restore backup
    backup_manager.restore_backup(
        backup_path,
        restore_db=False,
        restore_config=True,
        create_backup_before_restore=False,
    )

    # Verify restoration
    assert temp_dirs["config_file"].read_text() == "test config content"


def test_restore_backup_with_pre_backup(backup_manager, temp_dirs):
    """Test restore creates backup before restoring."""
    # Create initial backup
    backup_path = backup_manager.create_backup(include_db=True)

    # Modify database
    temp_dirs["db_file"].write_text("modified content")

    # Restore with pre-backup
    backup_manager.restore_backup(
        backup_path,
        restore_db=True,
        create_backup_before_restore=True,
    )

    # Should have 2 backups now (original + pre-restore)
    backups = backup_manager.list_backups()
    assert len(backups) == 2


def test_cleanup_old_backups(backup_manager, temp_dirs):
    """Test automatic cleanup of old backups."""
    backup_manager.max_backups = 3

    # Create 5 backups
    for i in range(5):
        backup_manager.create_backup(include_db=True, description=f"Backup {i}")

    # Should only keep 3 most recent
    backups = backup_manager.list_backups()
    assert len(backups) == 3


def test_backup_nonexistent_file(backup_manager, temp_dirs):
    """Test backup handles nonexistent files gracefully."""
    # Remove database file
    temp_dirs["db_file"].unlink()

    # Should not raise error, just skip missing file
    backup_path = backup_manager.create_backup(include_db=True)
    assert Path(backup_path).exists()


def test_restore_nonexistent_backup(backup_manager, temp_dirs):
    """Test restore raises error for nonexistent backup."""
    with pytest.raises(FileNotFoundError):
        backup_manager.restore_backup("nonexistent_backup.tar.gz")


def test_delete_nonexistent_backup(backup_manager, temp_dirs):
    """Test delete raises error for nonexistent backup."""
    with pytest.raises(FileNotFoundError):
        backup_manager.delete_backup("nonexistent_backup.tar.gz")


def test_backup_metadata(backup_manager, temp_dirs):
    """Test backup metadata is created correctly."""
    backup_path = backup_manager.create_backup(
        include_db=True,
        include_config=True,
        description="Test metadata",
    )

    # Check metadata file exists
    timestamp = Path(backup_path).stem.replace("backup_", "")
    metadata_path = backup_manager.backup_dir / f"backup_{timestamp}.json"
    assert metadata_path.exists()

    # Verify metadata content
    info = backup_manager.get_backup_info(backup_path)
    assert info["description"] == "Test metadata"
    assert info["includes"]["database"] is True
    assert info["includes"]["config"] is True
    assert info["includes"]["cache"] is False


def test_backup_compression_formats(temp_dirs):
    """Test different compression formats."""
    for compression in ["gz", "bz2", "xz"]:
        manager = BackupManager(backup_dir=str(temp_dirs["backup_dir"]))
        manager.compression = compression
        manager.db_path = temp_dirs["db_file"]

        backup_path = manager.create_backup(include_db=True)
        assert backup_path.endswith(f".tar.{compression}")
        assert Path(backup_path).exists()
