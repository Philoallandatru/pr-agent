"""
Unit tests for TokenizerManager
"""

import os
import tempfile
import unittest
from pathlib import Path

from pr_agent.algo.tokenizer_manager import TokenizerManager


class TestTokenizerManager(unittest.TestCase):
    """Test cases for TokenizerManager"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = TokenizerManager(cache_dir=self.temp_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_creates_cache_dir(self):
        """Test that initialization creates cache directory"""
        self.assertTrue(Path(self.temp_dir).exists())

    def test_download_tokenizers_success(self):
        """Test downloading tokenizers"""
        results = self.manager.download_tokenizers(models=["o200k_base"])
        self.assertIn("o200k_base", results)
        self.assertTrue(results["o200k_base"])

    def test_list_cached_tokenizers(self):
        """Test listing cached tokenizers"""
        # Download a tokenizer first
        self.manager.download_tokenizers(models=["o200k_base"])

        # List cached tokenizers
        cached = self.manager.list_cached_tokenizers()
        self.assertIn("o200k_base", cached)

    def test_validate_cache(self):
        """Test cache validation"""
        # Download a tokenizer
        self.manager.download_tokenizers(models=["o200k_base"])

        # Validate cache
        results = self.manager.validate_cache()
        self.assertIn("o200k_base", results)
        self.assertTrue(results["o200k_base"])

    def test_get_cache_info(self):
        """Test getting cache information"""
        info = self.manager.get_cache_info()

        self.assertEqual(info["cache_dir"], self.temp_dir)
        self.assertTrue(info["exists"])
        self.assertIsInstance(info["cached_models"], list)
        self.assertIsInstance(info["total_size_bytes"], int)

    def test_clear_cache_specific_model(self):
        """Test clearing cache for specific model"""
        # Download tokenizers
        self.manager.download_tokenizers(models=["o200k_base"])

        # Clear specific model
        success = self.manager.clear_cache(model="o200k_base")
        self.assertTrue(success)

        # Verify it's removed
        cached = self.manager.list_cached_tokenizers()
        self.assertNotIn("o200k_base", cached)

    def test_clear_all_cache(self):
        """Test clearing all cache"""
        # Download tokenizers
        self.manager.download_tokenizers(models=["o200k_base"])

        # Clear all
        success = self.manager.clear_cache()
        self.assertTrue(success)

        # Verify all removed
        cached = self.manager.list_cached_tokenizers()
        self.assertEqual(len(cached), 0)


if __name__ == "__main__":
    unittest.main()
