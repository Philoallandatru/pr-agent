"""
Repository Context Analyzer

Clones repositories and analyzes dependencies to provide full codebase context
for PR reviews beyond just the diff.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class RepoContextAnalyzer:
    """Analyzes repository context for comprehensive PR reviews"""

    def __init__(self):
        self.cache_dir = Path(get_settings().get("repo_context.clone_cache_dir", "/tmp/pr-agent-repos"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.clone_depth = get_settings().get("repo_context.clone_depth", 1)

    def _get_repo_cache_path(self, repo_url: str, branch: str) -> Path:
        """
        Get cache path for a repository

        Args:
            repo_url: Git repository URL
            branch: Branch name

        Returns:
            Path to cached repository
        """
        # Create safe directory name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        safe_name = f"{repo_name}_{branch}".replace('/', '_').replace('\\', '_')
        return self.cache_dir / safe_name

    def clone_repository(
        self,
        repo_url: str,
        branch: str,
        force_refresh: bool = False
    ) -> Optional[Path]:
        """
        Clone or update repository to local cache

        Args:
            repo_url: Git repository URL
            branch: Branch to checkout
            force_refresh: Force re-clone even if cached

        Returns:
            Path to cloned repository or None on failure
        """
        repo_path = self._get_repo_cache_path(repo_url, branch)

        try:
            # Remove existing if force refresh
            if force_refresh and repo_path.exists():
                get_logger().info(f"Force refresh: removing cached repo at {repo_path}")
                shutil.rmtree(repo_path)

            # Clone if doesn't exist
            if not repo_path.exists():
                get_logger().info(f"Cloning repository: {repo_url} (branch: {branch})")

                clone_cmd = [
                    "git", "clone",
                    "--depth", str(self.clone_depth),
                    "--branch", branch,
                    "--single-branch",
                    repo_url,
                    str(repo_path)
                ]

                result = subprocess.run(
                    clone_cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                if result.returncode != 0:
                    get_logger().error(f"Failed to clone repository: {result.stderr}")
                    return None

                get_logger().info(f"Successfully cloned to {repo_path}")

            else:
                # Update existing clone
                get_logger().info(f"Updating cached repository at {repo_path}")

                # Fetch latest changes
                fetch_cmd = ["git", "-C", str(repo_path), "fetch", "origin", branch]
                subprocess.run(fetch_cmd, capture_output=True, timeout=60)

                # Reset to latest
                reset_cmd = ["git", "-C", str(repo_path), "reset", "--hard", f"origin/{branch}"]
                subprocess.run(reset_cmd, capture_output=True, timeout=30)

                get_logger().info(f"Updated repository at {repo_path}")

            return repo_path

        except subprocess.TimeoutExpired:
            get_logger().error(f"Timeout while cloning/updating repository: {repo_url}")
            return None
        except Exception as e:
            get_logger().error(f"Error cloning repository: {e}")
            return None

    def get_file_content(self, repo_path: Path, file_path: str) -> Optional[str]:
        """
        Get content of a file from repository

        Args:
            repo_path: Path to cloned repository
            file_path: Relative path to file

        Returns:
            File content or None if not found
        """
        try:
            full_path = repo_path / file_path
            if not full_path.exists():
                return None

            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()

        except Exception as e:
            get_logger().warning(f"Failed to read file {file_path}: {e}")
            return None

    def find_related_files(
        self,
        repo_path: Path,
        changed_files: List[str],
        max_files: int = 20
    ) -> List[Tuple[str, str, int]]:
        """
        Find files related to changed files through imports/dependencies

        Args:
            repo_path: Path to cloned repository
            changed_files: List of changed file paths
            max_files: Maximum number of related files to return

        Returns:
            List of (file_path, content, relevance_score) tuples
        """
        from pr_agent.algo.dependency_resolver import get_resolver

        related_files = {}  # file_path -> (content, score)

        for changed_file in changed_files:
            try:
                # Get appropriate resolver for file type
                resolver = get_resolver(changed_file)
                if not resolver:
                    continue

                # Get file content
                content = self.get_file_content(repo_path, changed_file)
                if not content:
                    continue

                # Resolve dependencies
                dependencies = resolver.resolve_dependencies(content, changed_file, repo_path)

                # Add dependencies with scores
                for dep_file, score in dependencies:
                    if dep_file not in changed_files:  # Don't include files already in PR
                        if dep_file not in related_files or related_files[dep_file][1] < score:
                            dep_content = self.get_file_content(repo_path, dep_file)
                            if dep_content:
                                related_files[dep_file] = (dep_content, score)

            except Exception as e:
                get_logger().warning(f"Failed to analyze dependencies for {changed_file}: {e}")
                continue

        # Sort by relevance score and limit
        sorted_files = sorted(
            [(path, content, score) for path, (content, score) in related_files.items()],
            key=lambda x: x[2],
            reverse=True
        )

        return sorted_files[:max_files]

    def get_changed_files_context(
        self,
        repo_path: Path,
        changed_files: List[str]
    ) -> Dict[str, str]:
        """
        Get full content of changed files

        Args:
            repo_path: Path to cloned repository
            changed_files: List of changed file paths

        Returns:
            Dict mapping file paths to full content
        """
        context = {}

        for file_path in changed_files:
            content = self.get_file_content(repo_path, file_path)
            if content:
                context[file_path] = content

        return context

    def cleanup_old_clones(self, max_age_days: int = 7):
        """
        Remove cloned repositories older than max_age_days

        Args:
            max_age_days: Maximum age in days
        """
        if not self.cache_dir.exists():
            return

        cutoff_time = datetime.now().timestamp() - (max_age_days * 86400)
        removed_count = 0

        try:
            for repo_dir in self.cache_dir.iterdir():
                if repo_dir.is_dir():
                    # Check modification time
                    mtime = repo_dir.stat().st_mtime
                    if mtime < cutoff_time:
                        get_logger().info(f"Removing old clone: {repo_dir}")
                        shutil.rmtree(repo_dir)
                        removed_count += 1

            if removed_count > 0:
                get_logger().info(f"Cleaned up {removed_count} old repository clones")

        except Exception as e:
            get_logger().error(f"Error during cleanup: {e}")

    def get_cache_statistics(self) -> Dict:
        """
        Get statistics about repository cache

        Returns:
            Dict with cache statistics
        """
        if not self.cache_dir.exists():
            return {
                "cache_dir": str(self.cache_dir),
                "exists": False,
                "total_repos": 0,
                "total_size_mb": 0
            }

        total_size = 0
        repo_count = 0

        for repo_dir in self.cache_dir.iterdir():
            if repo_dir.is_dir():
                repo_count += 1
                # Calculate directory size
                for path in repo_dir.rglob('*'):
                    if path.is_file():
                        total_size += path.stat().st_size

        return {
            "cache_dir": str(self.cache_dir),
            "exists": True,
            "total_repos": repo_count,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }
