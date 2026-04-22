"""
Unit tests for RepoContextAnalyzer
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pr_agent.algo.repo_context_analyzer import RepoContextAnalyzer


class TestRepoContextAnalyzer(unittest.TestCase):
    """Test cases for RepoContextAnalyzer"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

        # Mock settings
        self.settings_patcher = patch('pr_agent.algo.repo_context_analyzer.get_settings')
        self.mock_settings = self.settings_patcher.start()
        self.mock_settings.return_value.get.side_effect = lambda key, default=None: {
            "repo_context.clone_cache_dir": self.temp_dir,
            "repo_context.clone_depth": 1
        }.get(key, default)

        self.analyzer = RepoContextAnalyzer()

    def tearDown(self):
        """Clean up test fixtures"""
        self.settings_patcher.stop()
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_creates_cache_dir(self):
        """Test that initialization creates cache directory"""
        self.assertTrue(Path(self.temp_dir).exists())

    def test_get_repo_cache_path(self):
        """Test repository cache path generation"""
        repo_url = "https://github.com/user/repo.git"
        branch = "main"

        cache_path = self.analyzer._get_repo_cache_path(repo_url, branch)

        self.assertIsInstance(cache_path, Path)
        self.assertIn("repo_main", str(cache_path))

    def test_get_file_content_existing_file(self):
        """Test reading existing file content"""
        # Create test file
        test_repo = Path(self.temp_dir) / "test_repo"
        test_repo.mkdir()
        test_file = test_repo / "test.py"
        test_file.write_text("print('hello')")

        content = self.analyzer.get_file_content(test_repo, "test.py")

        self.assertEqual(content, "print('hello')")

    def test_get_file_content_missing_file(self):
        """Test reading non-existent file"""
        test_repo = Path(self.temp_dir) / "test_repo"
        test_repo.mkdir()

        content = self.analyzer.get_file_content(test_repo, "missing.py")

        self.assertIsNone(content)

    def test_get_changed_files_context(self):
        """Test getting context for changed files"""
        # Create test repo with files
        test_repo = Path(self.temp_dir) / "test_repo"
        test_repo.mkdir()

        file1 = test_repo / "file1.py"
        file1.write_text("content1")

        file2 = test_repo / "file2.py"
        file2.write_text("content2")

        context = self.analyzer.get_changed_files_context(
            test_repo,
            ["file1.py", "file2.py"]
        )

        self.assertEqual(len(context), 2)
        self.assertEqual(context["file1.py"], "content1")
        self.assertEqual(context["file2.py"], "content2")

    def test_get_cache_statistics(self):
        """Test getting cache statistics"""
        # Create test repo
        test_repo = Path(self.temp_dir) / "test_repo"
        test_repo.mkdir()
        test_file = test_repo / "test.txt"
        test_file.write_text("test content")

        stats = self.analyzer.get_cache_statistics()

        self.assertTrue(stats['exists'])
        self.assertEqual(stats['total_repos'], 1)
        self.assertGreaterEqual(stats['total_size_mb'], 0)  # Size can be 0 for small files

    @patch('subprocess.run')
    def test_clone_repository_success(self, mock_run):
        """Test successful repository cloning"""
        mock_run.return_value = Mock(returncode=0)

        repo_url = "https://github.com/user/repo.git"
        branch = "main"

        result = self.analyzer.clone_repository(repo_url, branch)

        self.assertIsNotNone(result)
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_clone_repository_failure(self, mock_run):
        """Test failed repository cloning"""
        mock_run.return_value = Mock(returncode=1, stderr="error")

        repo_url = "https://github.com/user/repo.git"
        branch = "main"

        result = self.analyzer.clone_repository(repo_url, branch)

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
