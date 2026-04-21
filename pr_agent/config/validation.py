"""Configuration validation and health check utilities."""

import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates PR Agent configuration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> bool:
        """Run all validation checks."""
        self._validate_required_sections()
        self._validate_git_provider()
        self._validate_tokenizer()
        self._validate_polling()
        self._validate_repo_context()
        self._validate_web_platform()

        if self.errors:
            logger.error(f"Configuration validation failed with {len(self.errors)} errors")
            for error in self.errors:
                logger.error(f"  - {error}")
            return False

        if self.warnings:
            logger.warning(f"Configuration has {len(self.warnings)} warnings")
            for warning in self.warnings:
                logger.warning(f"  - {warning}")

        logger.info("Configuration validation passed")
        return True

    def _validate_required_sections(self):
        """Check for required configuration sections."""
        required = ['config']
        for section in required:
            if section not in self.config:
                self.errors.append(f"Missing required section: [{section}]")

    def _validate_git_provider(self):
        """Validate git provider configuration."""
        config_section = self.config.get('config', {})
        provider = config_section.get('git_provider')

        if not provider:
            self.errors.append("git_provider not specified in [config]")
            return

        if provider == 'bitbucket_server':
            bb_config = self.config.get('bitbucket_server', {})
            if not bb_config.get('url'):
                self.errors.append("bitbucket_server.url is required")
            if not bb_config.get('bearer_token') and not os.getenv('BITBUCKET_BEARER_TOKEN'):
                self.warnings.append("bitbucket_server.bearer_token not set")

    def _validate_tokenizer(self):
        """Validate tokenizer configuration."""
        tokenizer = self.config.get('tokenizer', {})

        if tokenizer.get('enable_local_cache'):
            cache_dir = tokenizer.get('local_cache_dir')
            if not cache_dir:
                self.errors.append("tokenizer.local_cache_dir required when enable_local_cache=true")
            elif not Path(cache_dir).exists():
                self.warnings.append(f"Tokenizer cache directory does not exist: {cache_dir}")

            if tokenizer.get('fallback_to_download') is False:
                # Strict offline mode - cache must exist
                if cache_dir and not Path(cache_dir).exists():
                    self.errors.append(
                        f"Offline mode enabled but cache directory missing: {cache_dir}"
                    )

    def _validate_polling(self):
        """Validate polling configuration."""
        bb_config = self.config.get('bitbucket_server', {})

        if bb_config.get('enable_polling'):
            interval = bb_config.get('polling_interval_seconds', 300)
            if interval < 60:
                self.warnings.append(
                    f"Polling interval is very short ({interval}s), may cause rate limiting"
                )

            repos = bb_config.get('polling_repositories', [])
            if not repos:
                self.warnings.append("No repositories configured for polling")

            commands = bb_config.get('polling_commands', [])
            if not commands:
                self.warnings.append("No commands configured for polling")

            state_file = bb_config.get('polling_state_file')
            if state_file:
                state_path = Path(state_file)
                if not state_path.parent.exists():
                    self.warnings.append(
                        f"Polling state directory does not exist: {state_path.parent}"
                    )

    def _validate_repo_context(self):
        """Validate repository context configuration."""
        repo_context = self.config.get('repo_context', {})

        if repo_context.get('enable_full_context'):
            cache_dir = repo_context.get('clone_cache_dir')
            if cache_dir and not Path(cache_dir).exists():
                self.warnings.append(
                    f"Repository cache directory does not exist: {cache_dir}"
                )

            max_files = repo_context.get('max_related_files', 20)
            if max_files > 50:
                self.warnings.append(
                    f"max_related_files is high ({max_files}), may impact performance"
                )

            max_tokens = repo_context.get('max_context_tokens', 10000)
            if max_tokens > 50000:
                self.warnings.append(
                    f"max_context_tokens is very high ({max_tokens}), may exceed model limits"
                )

    def _validate_web_platform(self):
        """Validate web platform configuration."""
        web_config = self.config.get('web_platform', {})

        if web_config.get('enable'):
            db_path = web_config.get('database_path')
            if db_path:
                db_file = Path(db_path)
                if not db_file.parent.exists():
                    self.warnings.append(
                        f"Database directory does not exist: {db_file.parent}"
                    )

            port = web_config.get('port', 8000)
            if port < 1024 and os.name != 'nt':
                self.warnings.append(
                    f"Port {port} requires root privileges on Unix systems"
                )

    def get_report(self) -> Dict[str, Any]:
        """Get validation report."""
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


class HealthChecker:
    """Performs health checks on the system."""

    def __init__(self):
        self.checks: Dict[str, bool] = {}
        self.details: Dict[str, str] = {}

    def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        self._check_database()
        self._check_git()
        self._check_tokenizer_cache()
        self._check_disk_space()
        self._check_memory()

        all_healthy = all(self.checks.values())
        status = 'healthy' if all_healthy else 'degraded'

        return {
            'status': status,
            'checks': self.checks,
            'details': self.details,
            'timestamp': self._get_timestamp()
        }

    def _check_database(self):
        """Check database connectivity."""
        try:
            from pr_agent.storage.database import Database
            db = Database()
            # Try a simple query
            db.get_all_repositories()
            self.checks['database'] = True
            self.details['database'] = 'Connected'
        except Exception as e:
            self.checks['database'] = False
            self.details['database'] = f'Error: {str(e)}'

    def _check_git(self):
        """Check git availability."""
        import subprocess
        try:
            result = subprocess.run(
                ['git', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                self.checks['git'] = True
                self.details['git'] = result.stdout.strip()
            else:
                self.checks['git'] = False
                self.details['git'] = 'Git command failed'
        except Exception as e:
            self.checks['git'] = False
            self.details['git'] = f'Error: {str(e)}'

    def _check_tokenizer_cache(self):
        """Check tokenizer cache status."""
        try:
            from pr_agent.algo.tokenizer_manager import TokenizerManager
            manager = TokenizerManager()
            info = manager.get_cache_info()
            self.checks['tokenizer_cache'] = True
            self.details['tokenizer_cache'] = (
                f"{info['total_models']} models, {info['total_size_mb']:.1f} MB"
            )
        except Exception as e:
            self.checks['tokenizer_cache'] = False
            self.details['tokenizer_cache'] = f'Error: {str(e)}'

    def _check_disk_space(self):
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage('/')
            free_gb = free / (1024 ** 3)
            free_percent = (free / total) * 100

            self.checks['disk_space'] = free_percent > 10
            self.details['disk_space'] = f"{free_gb:.1f} GB free ({free_percent:.1f}%)"
        except Exception as e:
            self.checks['disk_space'] = False
            self.details['disk_space'] = f'Error: {str(e)}'

    def _check_memory(self):
        """Check available memory."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024 ** 3)
            available_percent = memory.percent

            self.checks['memory'] = available_percent < 90
            self.details['memory'] = (
                f"{available_gb:.1f} GB available ({100 - available_percent:.1f}%)"
            )
        except ImportError:
            self.checks['memory'] = True
            self.details['memory'] = 'psutil not installed, skipping check'
        except Exception as e:
            self.checks['memory'] = False
            self.details['memory'] = f'Error: {str(e)}'

    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
