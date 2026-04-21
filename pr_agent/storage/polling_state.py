"""
Polling State Management - Persistent state tracking for PR polling

This module provides thread-safe state persistence for tracking processed PRs
to avoid duplicate processing and detect updates.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Dict, Optional, List

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class PollingState:
    """Manages persistent state for PR polling"""

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
        self._lock = Lock()
        self._state = self._load_state()

    def _load_state(self) -> Dict:
        """Load state from file"""
        if not self.state_file.exists():
            return {}

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            get_logger().error(f"Failed to load polling state: {e}")
            return {}

    def _save_state(self):
        """Save state to file"""
        try:
            # Ensure parent directory exists
            self.state_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.state_file, 'w') as f:
                json.dump(self._state, f, indent=2)
        except Exception as e:
            get_logger().error(f"Failed to save polling state: {e}")

    def get_pr_state(self, repo_key: str, pr_id: int) -> Optional[Dict]:
        """
        Get state for a specific PR

        Args:
            repo_key: Repository key (PROJECT/repo-slug)
            pr_id: PR ID

        Returns:
            PR state dict or None if not found
        """
        with self._lock:
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
        with self._lock:
            if repo_key not in self._state:
                self._state[repo_key] = {}

            self._state[repo_key][str(pr_id)] = {
                'version': version,
                'last_processed': datetime.now().isoformat(),
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

        return state.get('version') == version

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
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        with self._lock:
            repos_to_remove = []

            for repo_key, prs in self._state.items():
                prs_to_remove = []

                for pr_id, pr_state in prs.items():
                    try:
                        last_processed = datetime.fromisoformat(pr_state['last_processed'])
                        if last_processed < cutoff_date:
                            prs_to_remove.append(pr_id)
                    except Exception as e:
                        get_logger().warning(f"Invalid date in state for {repo_key}/{pr_id}: {e}")
                        prs_to_remove.append(pr_id)

                # Remove old PRs
                for pr_id in prs_to_remove:
                    del prs[pr_id]

                # Mark empty repos for removal
                if not prs:
                    repos_to_remove.append(repo_key)

            # Remove empty repos
            for repo_key in repos_to_remove:
                del self._state[repo_key]

            if prs_to_remove or repos_to_remove:
                get_logger().info(
                    f"Cleaned up {len(prs_to_remove)} old PR entries from {len(repos_to_remove)} repos"
                )
                self._save_state()

    def get_all_state(self) -> Dict:
        """Get complete state (for debugging/monitoring)"""
        with self._lock:
            return self._state.copy()

    def clear_state(self, repo_key: Optional[str] = None):
        """
        Clear state

        Args:
            repo_key: Specific repo to clear. If None, clears all.
        """
        with self._lock:
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
        with self._lock:
            total_repos = len(self._state)
            total_prs = sum(len(prs) for prs in self._state.values())

            recent_count = 0
            cutoff = datetime.now() - timedelta(hours=24)

            for prs in self._state.values():
                for pr_state in prs.values():
                    try:
                        last_processed = datetime.fromisoformat(pr_state['last_processed'])
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
