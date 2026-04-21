#!/usr/bin/env python3
"""
PR Agent Auto-Review CLI Management Tool

Unified command-line interface for managing the auto-review system.
"""

import argparse
import sys
import subprocess
import json
import os
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None


class AutoReviewCLI:
    """CLI tool for managing PR Agent auto-review system."""

    def __init__(self):
        self.web_platform_url = os.getenv('PR_AGENT_WEB_URL', 'http://localhost:8000')
        self.config_file = Path('.pr_agent.toml')

    def start_polling(self, background: bool = False):
        """Start the Bitbucket polling service."""
        print("🚀 Starting Bitbucket polling service...")
        cmd = [sys.executable, '-m', 'pr_agent.servers.bitbucket_server_polling']

        if background:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Polling service started in background")
        else:
            subprocess.run(cmd)

    def start_web_platform(self, background: bool = False):
        """Start the web platform server."""
        print("🚀 Starting web platform server...")
        cmd = [sys.executable, '-m', 'pr_agent.servers.web_platform']

        if background:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ Web platform started in background")
            print(f"   Access at: {self.web_platform_url}")
        else:
            subprocess.run(cmd)

    def start_all(self):
        """Start all services."""
        print("🚀 Starting all services...")
        self.start_web_platform(background=True)
        self.start_polling(background=True)
        print("\n✅ All services started!")
        print(f"   Web UI: {self.web_platform_url}")
        print(f"   API: {self.web_platform_url}/api")
        print(f"   Docs: {self.web_platform_url}/docs")

    def status(self):
        """Check status of all services."""
        print("📊 Checking service status...\n")

        # Check web platform
        if requests:
            try:
                response = requests.get(f"{self.web_platform_url}/api/health", timeout=2)
                if response.status_code == 200:
                    print("✅ Web Platform: Running")
                    data = response.json()
                    print(f"   Status: {data.get('status', 'unknown')}")
                else:
                    print("❌ Web Platform: Error")
            except requests.exceptions.RequestException:
                print("❌ Web Platform: Not running")
        else:
            print("⚠️  Web Platform: Cannot check (requests not installed)")

        # Check polling service (check if process is running)
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'bitbucket_server_polling'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Polling Service: Running")
                pids = result.stdout.strip().split('\n')
                print(f"   PIDs: {', '.join(pids)}")
            else:
                print("❌ Polling Service: Not running")
        except FileNotFoundError:
            # pgrep not available (Windows)
            print("⚠️  Polling Service: Cannot check (pgrep not available)")

    def logs(self, service: str = 'all', lines: int = 50):
        """View service logs."""
        print(f"📋 Viewing logs ({lines} lines)...\n")

        if service in ['all', 'web']:
            print("=== Web Platform Logs ===")
            # In production, this would read from log files
            print("(Log file location: /var/log/pr-agent/web_platform.log)")
            print()

        if service in ['all', 'polling']:
            print("=== Polling Service Logs ===")
            print("(Log file location: /var/log/pr-agent/polling.log)")
            print()

    def stats(self):
        """Show system statistics."""
        print("📈 System Statistics\n")

        if not requests:
            print("❌ Cannot fetch statistics (requests not installed)")
            return

        try:
            response = requests.get(f"{self.web_platform_url}/api/statistics", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"Total Repositories: {data.get('total_repositories', 0)}")
                print(f"Active Repositories: {data.get('active_repositories', 0)}")
                print(f"Total Reviews: {data.get('total_reviews', 0)}")
                print("\nReviews by Status:")
                for status, count in data.get('reviews_by_status', {}).items():
                    print(f"  {status}: {count}")
            else:
                print("❌ Failed to fetch statistics")
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")

    def validate_config(self):
        """Validate configuration file."""
        print("🔍 Validating configuration...\n")

        if not self.config_file.exists():
            print(f"❌ Configuration file not found: {self.config_file}")
            return False

        try:
            import toml
            config = toml.load(self.config_file)

            # Check required sections
            required_sections = ['config', 'bitbucket_server']
            for section in required_sections:
                if section not in config:
                    print(f"❌ Missing required section: [{section}]")
                    return False
                else:
                    print(f"✅ Section [{section}] found")

            # Check tokenizer config
            if 'tokenizer' in config:
                print("✅ Section [tokenizer] found")
                if config['tokenizer'].get('enable_local_cache'):
                    cache_dir = config['tokenizer'].get('local_cache_dir')
                    if cache_dir and Path(cache_dir).exists():
                        print(f"   ✅ Cache directory exists: {cache_dir}")
                    else:
                        print(f"   ⚠️  Cache directory not found: {cache_dir}")

            # Check polling config
            if config.get('bitbucket_server', {}).get('enable_polling'):
                print("✅ Polling enabled")
                interval = config['bitbucket_server'].get('polling_interval_seconds', 300)
                print(f"   Interval: {interval}s")

            # Check repo context config
            if 'repo_context' in config:
                print("✅ Section [repo_context] found")
                if config['repo_context'].get('enable_full_context'):
                    print("   ✅ Full context analysis enabled")

            print("\n✅ Configuration is valid!")
            return True

        except Exception as e:
            print(f"❌ Configuration error: {e}")
            return False

    def tokenizer_download(self, models: Optional[str] = None):
        """Download tokenizers to local cache."""
        print("📥 Downloading tokenizers...\n")
        cmd = [sys.executable, '-m', 'pr_agent.algo.tokenizer_manager', 'download']
        if models:
            cmd.extend(['--models', models])
        subprocess.run(cmd)

    def tokenizer_list(self):
        """List cached tokenizers."""
        print("📋 Cached tokenizers:\n")
        cmd = [sys.executable, '-m', 'pr_agent.algo.tokenizer_manager', 'list']
        subprocess.run(cmd)

    def tokenizer_info(self):
        """Show tokenizer cache info."""
        print("ℹ️  Tokenizer cache info:\n")
        cmd = [sys.executable, '-m', 'pr_agent.algo.tokenizer_manager', 'info']
        subprocess.run(cmd)


def main():
    parser = argparse.ArgumentParser(
        description='PR Agent Auto-Review System Management CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start --all              Start all services
  %(prog)s start --polling          Start polling service only
  %(prog)s status                   Check service status
  %(prog)s stats                    Show system statistics
  %(prog)s validate                 Validate configuration
  %(prog)s tokenizer download       Download tokenizers
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Start command
    start_parser = subparsers.add_parser('start', help='Start services')
    start_parser.add_argument('--all', action='store_true', help='Start all services')
    start_parser.add_argument('--polling', action='store_true', help='Start polling service')
    start_parser.add_argument('--web', action='store_true', help='Start web platform')
    start_parser.add_argument('--background', '-b', action='store_true', help='Run in background')

    # Status command
    subparsers.add_parser('status', help='Check service status')

    # Stats command
    subparsers.add_parser('stats', help='Show system statistics')

    # Logs command
    logs_parser = subparsers.add_parser('logs', help='View service logs')
    logs_parser.add_argument('--service', choices=['all', 'web', 'polling'], default='all')
    logs_parser.add_argument('--lines', '-n', type=int, default=50, help='Number of lines to show')

    # Validate command
    subparsers.add_parser('validate', help='Validate configuration')

    # Tokenizer commands
    tokenizer_parser = subparsers.add_parser('tokenizer', help='Manage tokenizers')
    tokenizer_subparsers = tokenizer_parser.add_subparsers(dest='tokenizer_command')

    download_parser = tokenizer_subparsers.add_parser('download', help='Download tokenizers')
    download_parser.add_argument('--models', help='Comma-separated list of models')

    tokenizer_subparsers.add_parser('list', help='List cached tokenizers')
    tokenizer_subparsers.add_parser('info', help='Show cache info')

    args = parser.parse_args()
    cli = AutoReviewCLI()

    if args.command == 'start':
        if args.all:
            cli.start_all()
        elif args.polling:
            cli.start_polling(background=args.background)
        elif args.web:
            cli.start_web_platform(background=args.background)
        else:
            print("❌ Please specify --all, --polling, or --web")
            sys.exit(1)

    elif args.command == 'status':
        cli.status()

    elif args.command == 'stats':
        cli.stats()

    elif args.command == 'logs':
        cli.logs(service=args.service, lines=args.lines)

    elif args.command == 'validate':
        if not cli.validate_config():
            sys.exit(1)

    elif args.command == 'tokenizer':
        if args.tokenizer_command == 'download':
            cli.tokenizer_download(models=args.models)
        elif args.tokenizer_command == 'list':
            cli.tokenizer_list()
        elif args.tokenizer_command == 'info':
            cli.tokenizer_info()
        else:
            tokenizer_parser.print_help()

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
