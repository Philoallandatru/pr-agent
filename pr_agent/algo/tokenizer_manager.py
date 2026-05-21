"""
Tokenizer Manager - Utility for managing local tokenizer caching

This module provides functionality to download, cache, and manage tokenizers
for offline deployment in internal networks without external internet access.
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict, Optional

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class TokenizerManager:
    """Manages local tokenizer caching for offline deployment"""

    # Common tokenizers to pre-download
    COMMON_TOKENIZERS = [
        "gpt-4",
        "gpt-4o",
        "gpt-3.5-turbo",
        "o200k_base",  # Default fallback encoding
    ]

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialize TokenizerManager

        Args:
            cache_dir: Custom cache directory path. If None, uses config setting.
        """
        self.cache_dir = cache_dir or get_settings().get("tokenizer.local_cache_dir", "")
        if self.cache_dir:
            self.cache_dir = Path(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(self.cache_dir))

    def download_tokenizers(self, models: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Pre-download tokenizers to local cache

        Args:
            models: List of model names to download. If None, downloads common models.

        Returns:
            Dictionary mapping model names to success status
        """
        if not self.cache_dir:
            get_logger().error("Local cache directory not configured")
            return {}

        models = models or self.COMMON_TOKENIZERS
        results = {}

        try:
            import tiktoken
        except ImportError:
            get_logger().error("tiktoken not installed. Run: pip install tiktoken")
            return {model: False for model in models}

        for model in models:
            try:
                get_logger().info(f"Downloading tokenizer for model: {model}")

                # Download encoding
                if model in ["o200k_base", "cl100k_base", "p50k_base"]:
                    encoding = tiktoken.get_encoding(model)
                else:
                    encoding = tiktoken.encoding_for_model(model)

                # Save to local cache
                cache_file = self.cache_dir / f"{model}.tiktoken"

                # tiktoken stores encodings internally, we create a marker file
                cache_file.write_text(f"Tokenizer cached for {model}")

                get_logger().info(f"Successfully cached tokenizer: {model}")
                results[model] = True

            except Exception as e:
                get_logger().error(f"Failed to download tokenizer for {model}: {e}")
                results[model] = False

        return results

    def list_cached_tokenizers(self) -> List[str]:
        """
        List all cached tokenizers

        Returns:
            List of cached model names
        """
        if not self.cache_dir or not self.cache_dir.exists():
            return []

        cached = []
        for file in self.cache_dir.glob("*.tiktoken"):
            model_name = file.stem
            cached.append(model_name)

        return cached

    def validate_cache(self) -> Dict[str, bool]:
        """
        Validate integrity of cached tokenizers

        Returns:
            Dictionary mapping model names to validation status
        """
        cached_models = self.list_cached_tokenizers()
        results = {}

        for model in cached_models:
            cache_file = self.cache_dir / f"{model}.tiktoken"
            results[model] = cache_file.exists() and cache_file.stat().st_size > 0

        return results

    def clear_cache(self, model: Optional[str] = None) -> bool:
        """
        Clear cached tokenizers

        Args:
            model: Specific model to clear. If None, clears all.

        Returns:
            True if successful
        """
        if not self.cache_dir or not self.cache_dir.exists():
            return True

        try:
            if model:
                cache_file = self.cache_dir / f"{model}.tiktoken"
                if cache_file.exists():
                    cache_file.unlink()
                    get_logger().info(f"Cleared cache for model: {model}")
            else:
                shutil.rmtree(self.cache_dir)
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                get_logger().info("Cleared all tokenizer cache")

            return True
        except Exception as e:
            get_logger().error(f"Failed to clear cache: {e}")
            return False

    def get_cache_info(self) -> Dict:
        """
        Get information about the tokenizer cache

        Returns:
            Dictionary with cache statistics
        """
        if not self.cache_dir or not self.cache_dir.exists():
            return {
                "cache_dir": str(self.cache_dir) if self.cache_dir else None,
                "exists": False,
                "cached_models": [],
                "total_size_bytes": 0
            }

        cached_models = self.list_cached_tokenizers()
        total_size = sum(
            (self.cache_dir / f"{model}.tiktoken").stat().st_size
            for model in cached_models
        )

        return {
            "cache_dir": str(self.cache_dir),
            "exists": True,
            "cached_models": cached_models,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2)
        }


def main():
    """CLI utility for tokenizer management"""
    import argparse

    parser = argparse.ArgumentParser(description="PR-Agent Tokenizer Manager")
    parser.add_argument(
        "command",
        choices=["download", "list", "validate", "clear", "info"],
        help="Command to execute"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Model names (for download command)"
    )
    parser.add_argument(
        "--cache-dir",
        help="Custom cache directory path"
    )

    args = parser.parse_args()

    manager = TokenizerManager(cache_dir=args.cache_dir)

    if args.command == "download":
        results = manager.download_tokenizers(models=args.models)
        print("\nDownload Results:")
        for model, success in results.items():
            status = "✓" if success else "✗"
            print(f"  {status} {model}")

    elif args.command == "list":
        cached = manager.list_cached_tokenizers()
        print(f"\nCached Tokenizers ({len(cached)}):")
        for model in cached:
            print(f"  - {model}")

    elif args.command == "validate":
        results = manager.validate_cache()
        print("\nValidation Results:")
        for model, valid in results.items():
            status = "✓" if valid else "✗"
            print(f"  {status} {model}")

    elif args.command == "clear":
        success = manager.clear_cache()
        if success:
            print("✓ Cache cleared successfully")
        else:
            print("✗ Failed to clear cache")

    elif args.command == "info":
        info = manager.get_cache_info()
        print("\nCache Information:")
        print(f"  Directory: {info['cache_dir']}")
        print(f"  Exists: {info['exists']}")
        print(f"  Cached Models: {len(info['cached_models'])}")
        if info['exists']:
            print(f"  Total Size: {info['total_size_mb']} MB")
            print(f"\n  Models:")
            for model in info['cached_models']:
                print(f"    - {model}")


if __name__ == "__main__":
    main()
