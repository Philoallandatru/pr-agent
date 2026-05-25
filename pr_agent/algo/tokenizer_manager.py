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

    MODELSCOPE_TOKENIZER_FILE_PATTERNS = [
        "tokenizer.json",
        "tokenizer_config.json",
        "special_tokens_map.json",
        "added_tokens.json",
        "vocab.json",
        "merges.txt",
        "*.model",
        "config.json",
        "generation_config.json",
        "chat_template.jinja",
        "tokenization_*.py",
        "configuration_*.py",
    ]

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

    def _get_modelscope_local_dir(self, model_id: str) -> Path:
        safe_model_id = model_id.replace("/", "__")
        return self.cache_dir / "modelscope" / safe_model_id

    def download_modelscope_tokenizer(self, model_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Download a ModelScope tokenizer snapshot to a stable local directory.

        Args:
            model_id: ModelScope model id. If None, uses tokenizer.modelscope_model_id.

        Returns:
            Dictionary mapping model id to success status
        """
        if not self.cache_dir:
            get_logger().error("Local cache directory not configured")
            return {}

        model_id = model_id or get_settings().get("tokenizer.modelscope_model_id", "")
        if not model_id:
            get_logger().error("tokenizer.modelscope_model_id is not configured")
            return {}

        try:
            from modelscope import snapshot_download
        except ImportError:
            get_logger().error("modelscope not installed. Run: pip install modelscope")
            return {model_id: False}

        local_dir = self._get_modelscope_local_dir(model_id)
        local_dir.mkdir(parents=True, exist_ok=True)

        try:
            get_logger().info(f"Downloading ModelScope tokenizer for model: {model_id}")
            try:
                snapshot_path = Path(
                    snapshot_download(
                        model_id,
                        local_dir=str(local_dir),
                        allow_patterns=self.MODELSCOPE_TOKENIZER_FILE_PATTERNS,
                    )
                )
            except TypeError:
                try:
                    snapshot_path = Path(
                        snapshot_download(
                            model_id,
                            local_dir=str(local_dir),
                            allow_file_pattern=self.MODELSCOPE_TOKENIZER_FILE_PATTERNS,
                        )
                    )
                except TypeError:
                    snapshot_path = Path(snapshot_download(model_id, cache_dir=str(self.cache_dir / "modelscope")))
                    if snapshot_path.resolve() != local_dir.resolve():
                        shutil.copytree(snapshot_path, local_dir, dirs_exist_ok=True)

            marker_file = local_dir / ".modelscope_tokenizer"
            marker_file.write_text(model_id)
            get_logger().info(f"Successfully cached ModelScope tokenizer: {model_id}")
            return {model_id: True}
        except Exception as e:
            get_logger().error(f"Failed to download ModelScope tokenizer for {model_id}: {e}")
            return {model_id: False}

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
        for marker_file in self.cache_dir.glob("modelscope/*/.modelscope_tokenizer"):
            model_id = marker_file.read_text().strip()
            if model_id:
                cached.append(f"modelscope:{model_id}")

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
            if model.startswith("modelscope:"):
                model_id = model.removeprefix("modelscope:")
                model_dir = self._get_modelscope_local_dir(model_id)
                results[model] = model_dir.exists() and any(model_dir.iterdir())
            else:
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
                if model.startswith("modelscope:"):
                    model_id = model.removeprefix("modelscope:")
                    model_dir = self._get_modelscope_local_dir(model_id)
                    if model_dir.exists():
                        shutil.rmtree(model_dir)
                        get_logger().info(f"Cleared cache for model: {model}")
                else:
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
                "total_models": 0,
                "total_size_bytes": 0
            }

        cached_models = self.list_cached_tokenizers()
        total_size = 0
        for model in cached_models:
            if model.startswith("modelscope:"):
                model_id = model.removeprefix("modelscope:")
                model_dir = self._get_modelscope_local_dir(model_id)
                total_size += sum(file.stat().st_size for file in model_dir.rglob("*") if file.is_file())
            else:
                total_size += (self.cache_dir / f"{model}.tiktoken").stat().st_size

        return {
            "cache_dir": str(self.cache_dir),
            "exists": True,
            "cached_models": cached_models,
            "total_models": len(cached_models),
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
    parser.add_argument(
        "--modelscope-model-id",
        help="ModelScope model id to download, for example Qwen/Qwen3.6-35B-A3B-FP8"
    )

    args = parser.parse_args()

    manager = TokenizerManager(cache_dir=args.cache_dir)

    if args.command == "download":
        if args.modelscope_model_id:
            results = manager.download_modelscope_tokenizer(model_id=args.modelscope_model_id)
        else:
            results = manager.download_tokenizers(models=args.models)
        print("\nDownload Results:")
        for model, success in results.items():
            status = "OK" if success else "FAIL"
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
            status = "OK" if valid else "FAIL"
            print(f"  {status} {model}")

    elif args.command == "clear":
        success = manager.clear_cache()
        if success:
            print("OK Cache cleared successfully")
        else:
            print("FAIL Failed to clear cache")

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
