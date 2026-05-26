"""
Polling State Management - Persistent state tracking for PR polling

This module provides process-safe state persistence for tracking processed PRs
to avoid duplicate processing and detect updates.
"""

import copy
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, List

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False

try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False


class PollingState:
    """Manages persistent state for PR polling with process-safe file locking"""

    def __init__(self, state_file: Optional[str] = None):
        """
        Initialize PollingState

        Args:
            state_file: Path to state file. If None, uses config setting.
        """
        self.state_file = state_file or get_settings().get(
            "bitbucket_server.polling_state_file",
            ".pr_agent_polling_state.json"
        )
        self.state_file = Path(self.state_file)
        self._state = self._load_state()

    def _acquire_lock(self, file_handle):
        """Acquire file lock (cross-platform)"""
        if HAS_FCNTL:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
        elif HAS_MSVCRT:
            # Windows: lock 1 byte at position 0
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                # If lock fails, try blocking lock
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
        # If no locking available, proceed without lock (best effort)

    def _release_lock(self, file_handle):
        """Release file lock (cross-platform)"""
        if HAS_FCNTL:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
        elif HAS_MSVCRT:
            try:
                msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                # Lock may already be released, ignore
                pass

    def _load_state(self) -> Dict:
        """Load state from file with file locking"""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r') as f:
                self._acquire_lock(f)
                try:
                    state = json.load(f)
                finally:
                    self._release_lock(f)
                return state
        except Exception as e:
            get_logger().error(f"Failed to load polling state: {e}")
            return {}

    def _save_state(self):
        """Save state to file atomically with file locking"""
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first (atomic write pattern)
            temp_fd, temp_path = tempfile.mkstemp(
                dir=self.state_file.parent,
                prefix='.pr_agent_state_',
                suffix='.tmp'
            )

            try:
                with os.fdopen(temp_fd, 'w') as f:
                    self._acquire_lock(f)
                    try:
                        json.dump(self._state, f, indent=2)
                        f.flush()
                        os.fsync(f.fileno())
                    finally:
                        self._release_lock(f)

                # Atomic rename
                os.replace(temp_path, self.state_file)
            except:
                # Clean up temp file on error
                try:
                    os.unlink(temp_path)
                except:
                    pass
                raise
        except Exception as e:
            get_logger().error(f"Failed to save polling state: {e}")
            raise  # Re-raise to let caller know save failed

    def get_pr_state(self, repo_key: str, pr_id: int) -> Optional[Dict]:
        """
        Get state for a specific PR

        Args:
            repo_key: Repository key (PROJECT/repo-slug)
            pr_id: PR ID

        Returns:
            PR state dict or None if not found
        """
        # Reload state from file to get latest data
        self._state = self._load_state()
        return self._state.get(repo_key, {}).get(str(pr_id))

    def update_pr_state(
        self,
        repo_key: str,
        pr_id: int,
        version: int,
        commands_run: List[str],
        status: str = "completed"
    ):
        """
        Update state for a PR

        Args:
            repo_key: Repository key (PROJECT/repo-slug)
            pr_id: PR ID
            version: PR version number
            commands_run: List of commands executed
            status: Processing status
        """
        # Reload state to get latest data from other processes
        self._state = self._load_state()

        if repo_key not in self._state:
            self._state[repo_key] = {}

        self._state[repo_key][str(pr_id)] = {
            'version': version,
            'last_processed': datetime.now(timezone.utc).isoformat(),
            'commands_run': commands_run,
            'status': status
        }

        self._save_state()

    def is_pr_processed(self, repo_key: str, pr_id: int, version: int) -> bool:
        """
        Check if PR has been processed at this version

        Args:
            repo_key: Repository key
            pr_id: PR ID
            version: PR version

        Returns:
            True if already processed at this version
        """
        state = self.get_pr_state(repo_key, pr_id)
        if not state:
            return False

        if state.get('version') != version:
            return False

        return state.get('status') in {"completed", "filtered"}

    def is_pr_updated(self, repo_key: str, pr_id: int, version: int) -> bool:
        """
        Check if PR has been updated since last processing

        Args:
            repo_key: Repository key
            pr_id: PR ID
            version: Current PR version

        Returns:
            True if PR version is newer than stored version
        """
        state = self.get_pr_state(repo_key, pr_id)
        if not state:
            return False

        return version > state.get('version', 0)

    def cleanup_old_entries(self, retention_days: int = 30):
        """
        Remove entries older than retention period

        Args:
            retention_days: Number of days to retain entries
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

        # Reload state to get latest data
        self._state = self._load_state()
        repos_to_remove = []
        total_prs_removed = 0

        for repo_key, prs in self._state.items():
            prs_to_remove = []

            for pr_id, pr_state in prs.items():
                try:
                    last_processed = datetime.fromisoformat(pr_state['last_processed'])
                    # Make timezone-aware if naive
                    if last_processed.tzinfo is None:
                        last_processed = last_processed.replace(tzinfo=timezone.utc)
                    if last_processed < cutoff_date:
                        prs_to_remove.append(pr_id)
                except Exception as e:
                    # Only remove if timestamp is truly corrupted, log warning
                    get_logger().warning(f"Corrupted timestamp in state for {repo_key}/{pr_id}: {e}, keeping entry")
                    # Don't remove - let it stay until manually cleaned

                # Remove old PRs
                for pr_id in prs_to_remove:
                    del prs[pr_id]
                total_prs_removed += len(prs_to_remove)

                # Mark empty repos for removal
                if not prs:
                    repos_to_remove.append(repo_key)

            # Remove empty repos
            for repo_key in repos_to_remove:
                del self._state[repo_key]

            if total_prs_removed or repos_to_remove:
                get_logger().info(
                    f"Cleaned up {total_prs_removed} old PR entries from {len(repos_to_remove)} repos"
                )
                self._save_state()

    def get_all_state(self) -> Dict:
        """Get complete state (for debugging/monitoring) - returns deep copy"""
        self._state = self._load_state()
        return copy.deepcopy(self._state)

    def clear_state(self, repo_key: Optional[str] = None):
        """
        Clear state

        Args:
            repo_key: Specific repo to clear. If None, clears all.
        """
        self._state = self._load_state()
        if repo_key:
            if repo_key in self._state:
                del self._state[repo_key]
                get_logger().info(f"Cleared state for repository: {repo_key}")
        else:
            self._state = {}
            get_logger().info("Cleared all polling state")

        self._save_state()

    def get_statistics(self) -> Dict:
        """
        Get statistics about polling state

        Returns:
            Dict with statistics
        """
        self._state = self._load_state()
        total_repos = len(self._state)
        total_prs = sum(len(prs) for prs in self._state.values())

        recent_count = 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        for prs in self._state.values():
            for pr_state in prs.values():
                try:
                    last_processed = datetime.fromisoformat(pr_state['last_processed'])
                    # Make timezone-aware if naive
                    if last_processed.tzinfo is None:
                        last_processed = last_processed.replace(tzinfo=timezone.utc)
                    if last_processed > cutoff:
                        recent_count += 1
                except:
                    pass

        return {
            'total_repositories': total_repos,
            'total_prs_tracked': total_prs,
            'prs_processed_last_24h': recent_count,
                'state_file': str(self.state_file),
                'state_file_exists': self.state_file.exists()
            }
