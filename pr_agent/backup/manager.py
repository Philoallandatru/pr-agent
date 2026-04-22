"""
Backup and restore manager for PR-Agent data.

Handles automated backups of:
- SQLite database
- Configuration files
- Tokenizer cache
- Repository clones
- Log files
"""

import os
import shutil
import tarfile
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from pr_agent.config_loader import get_settings

logger = logging.getLogger(__name__)


class BackupManager:
    """Manages backup and restore operations."""

    def __init__(self, backup_dir: Optional[str] = None):
        """
        Initialize backup manager.

        Args:
            backup_dir: Directory to store backups (default from config)
        """
        settings = get_settings()
        self.backup_dir = Path(backup_dir or settings.get("backup.directory", "./backups"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        # Paths to backup
        self.db_path = Path(settings.get("database.path", "./data/pr_agent.db"))
        self.config_path = Path(settings.get("config.path", "./pr_agent/settings/configuration.toml"))
        self.tokenizer_cache = Path(settings.get("tokenizer.cache_dir", "./tokenizer_cache"))
        self.repo_cache = Path(settings.get("repo_context.cache_dir", "./repo_cache"))
        self.log_dir = Path(settings.get("logging.directory", "./logs"))

        # Backup retention settings
        self.max_backups = settings.get("backup.max_backups", 30)
        self.compression = settings.get("backup.compression", "gz")

    def create_backup(
        self,
        include_db: bool = True,
        include_config: bool = True,
        include_cache: bool = False,
        include_logs: bool = False,
        description: Optional[str] = None,
    ) -> str:
        """
        Create a backup archive.

        Args:
            include_db: Include database
            include_config: Include configuration files
            include_cache: Include tokenizer and repo cache
            include_logs: Include log files
            description: Optional backup description

        Returns:
            Path to backup archive

        Raises:
            Exception: If backup fails
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}.tar.{self.compression}"
        backup_path = self.backup_dir / backup_name
        metadata_path = self.backup_dir / f"backup_{timestamp}.json"

        logger.info(f"Creating backup: {backup_name}")

        try:
            # Create tar archive
            with tarfile.open(backup_path, f"w:{self.compression}") as tar:
                # Backup database
                if include_db and self.db_path.exists():
                    logger.info(f"Backing up database: {self.db_path}")
                    tar.add(self.db_path, arcname=f"database/{self.db_path.name}")

                # Backup configuration
                if include_config and self.config_path.exists():
                    logger.info(f"Backing up config: {self.config_path}")
                    tar.add(self.config_path, arcname=f"config/{self.config_path.name}")

                # Backup cache directories
                if include_cache:
                    if self.tokenizer_cache.exists():
                        logger.info(f"Backing up tokenizer cache: {self.tokenizer_cache}")
                        tar.add(self.tokenizer_cache, arcname="cache/tokenizer")

                    if self.repo_cache.exists():
                        logger.info(f"Backing up repo cache: {self.repo_cache}")
                        tar.add(self.repo_cache, arcname="cache/repos")

                # Backup logs
                if include_logs and self.log_dir.exists():
                    logger.info(f"Backing up logs: {self.log_dir}")
                    tar.add(self.log_dir, arcname="logs")

            # Create metadata file
            metadata = {
                "timestamp": timestamp,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "description": description,
                "includes": {
                    "database": include_db,
                    "config": include_config,
                    "cache": include_cache,
                    "logs": include_logs,
                },
                "size_bytes": backup_path.stat().st_size,
                "compression": self.compression,
            }

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"Backup created successfully: {backup_path}")
            logger.info(f"Backup size: {metadata['size_bytes'] / 1024 / 1024:.2f} MB")

            # Clean up old backups
            self._cleanup_old_backups()

            return str(backup_path)

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup
            if backup_path.exists():
                backup_path.unlink()
            if metadata_path.exists():
                metadata_path.unlink()
            raise

    def restore_backup(
        self,
        backup_path: str,
        restore_db: bool = True,
        restore_config: bool = True,
        restore_cache: bool = False,
        restore_logs: bool = False,
        create_backup_before_restore: bool = True,
    ) -> None:
        """
        Restore from a backup archive.

        Args:
            backup_path: Path to backup archive
            restore_db: Restore database
            restore_config: Restore configuration
            restore_cache: Restore cache directories
            restore_logs: Restore logs
            create_backup_before_restore: Create backup before restoring

        Raises:
            Exception: If restore fails
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        logger.info(f"Restoring from backup: {backup_path}")

        # Create backup before restore
        if create_backup_before_restore:
            logger.info("Creating backup before restore...")
            self.create_backup(
                include_db=restore_db,
                include_config=restore_config,
                include_cache=restore_cache,
                include_logs=restore_logs,
                description="Pre-restore backup",
            )

        try:
            # Extract archive
            with tarfile.open(backup_path, f"r:{self.compression}") as tar:
                # Restore database
                if restore_db:
                    db_member = f"database/{self.db_path.name}"
                    if db_member in tar.getnames():
                        logger.info(f"Restoring database to: {self.db_path}")
                        self.db_path.parent.mkdir(parents=True, exist_ok=True)
                        tar.extract(db_member, path=self.db_path.parent.parent)
                        # Move to correct location
                        extracted = self.db_path.parent.parent / db_member
                        shutil.move(str(extracted), str(self.db_path))
                        # Clean up
                        (self.db_path.parent.parent / "database").rmdir()

                # Restore configuration
                if restore_config:
                    config_member = f"config/{self.config_path.name}"
                    if config_member in tar.getnames():
                        logger.info(f"Restoring config to: {self.config_path}")
                        self.config_path.parent.mkdir(parents=True, exist_ok=True)
                        tar.extract(config_member, path=self.config_path.parent.parent)
                        # Move to correct location
                        extracted = self.config_path.parent.parent / config_member
                        shutil.move(str(extracted), str(self.config_path))
                        # Clean up
                        (self.config_path.parent.parent / "config").rmdir()

                # Restore cache
                if restore_cache:
                    if "cache/tokenizer" in tar.getnames():
                        logger.info(f"Restoring tokenizer cache to: {self.tokenizer_cache}")
                        if self.tokenizer_cache.exists():
                            shutil.rmtree(self.tokenizer_cache)
                        tar.extract("cache/tokenizer", path=self.tokenizer_cache.parent)
                        shutil.move(
                            str(self.tokenizer_cache.parent / "cache" / "tokenizer"),
                            str(self.tokenizer_cache),
                        )

                    if "cache/repos" in tar.getnames():
                        logger.info(f"Restoring repo cache to: {self.repo_cache}")
                        if self.repo_cache.exists():
                            shutil.rmtree(self.repo_cache)
                        tar.extract("cache/repos", path=self.repo_cache.parent)
                        shutil.move(
                            str(self.repo_cache.parent / "cache" / "repos"),
                            str(self.repo_cache),
                        )

                    # Clean up cache directory
                    cache_dir = self.tokenizer_cache.parent / "cache"
                    if cache_dir.exists() and not any(cache_dir.iterdir()):
                        cache_dir.rmdir()

                # Restore logs
                if restore_logs:
                    if "logs" in tar.getnames():
                        logger.info(f"Restoring logs to: {self.log_dir}")
                        if self.log_dir.exists():
                            shutil.rmtree(self.log_dir)
                        tar.extract("logs", path=self.log_dir.parent)

            logger.info("Restore completed successfully")

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise

    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups.

        Returns:
            List of backup metadata dictionaries
        """
        backups = []

        for backup_file in sorted(self.backup_dir.glob(f"backup_*.tar.{self.compression}")):
            timestamp = backup_file.stem.replace("backup_", "")
            metadata_file = self.backup_dir / f"backup_{timestamp}.json"

            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
            else:
                # Create basic metadata if not found
                metadata = {
                    "timestamp": timestamp,
                    "created_at": datetime.fromtimestamp(
                        backup_file.stat().st_mtime, tz=timezone.utc
                    ).isoformat(),
                    "size_bytes": backup_file.stat().st_size,
                }

            metadata["path"] = str(backup_file)
            backups.append(metadata)

        return backups

    def delete_backup(self, backup_path: str) -> None:
        """
        Delete a backup archive and its metadata.

        Args:
            backup_path: Path to backup archive

        Raises:
            FileNotFoundError: If backup not found
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Delete metadata file
        timestamp = backup_path.stem.replace("backup_", "")
        metadata_path = self.backup_dir / f"backup_{timestamp}.json"
        if metadata_path.exists():
            metadata_path.unlink()

        # Delete backup archive
        backup_path.unlink()
        logger.info(f"Deleted backup: {backup_path}")

    def _cleanup_old_backups(self) -> None:
        """Remove old backups exceeding max_backups limit."""
        backups = self.list_backups()

        if len(backups) > self.max_backups:
            # Sort by creation time (oldest first)
            backups.sort(key=lambda x: x["created_at"])

            # Delete oldest backups
            to_delete = backups[: len(backups) - self.max_backups]
            for backup in to_delete:
                logger.info(f"Removing old backup: {backup['path']}")
                self.delete_backup(backup["path"])

    def get_backup_info(self, backup_path: str) -> Dict[str, Any]:
        """
        Get detailed information about a backup.

        Args:
            backup_path: Path to backup archive

        Returns:
            Backup metadata dictionary

        Raises:
            FileNotFoundError: If backup not found
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        timestamp = backup_path.stem.replace("backup_", "")
        metadata_file = self.backup_dir / f"backup_{timestamp}.json"

        if metadata_file.exists():
            with open(metadata_file) as f:
                return json.load(f)

        # Return basic info if metadata not found
        return {
            "timestamp": timestamp,
            "created_at": datetime.fromtimestamp(
                backup_path.stat().st_mtime, tz=timezone.utc
            ).isoformat(),
            "size_bytes": backup_path.stat().st_size,
            "path": str(backup_path),
        }
