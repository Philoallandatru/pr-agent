"""
Bitbucket Server Polling Service

Automatically polls Bitbucket Server repositories for new/updated PRs
and triggers review commands.
"""

import asyncio
import multiprocessing
import traceback
import time
from collections import deque
from datetime import datetime

from pr_agent.agent.pr_agent import PRAgent
from pr_agent.config_loader import get_settings
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider
from pr_agent.log import LoggingFormat, get_logger, setup_logger
from pr_agent.servers.bitbucket_server_webhook import should_process_pr_logic, _run_commands_sequentially
from pr_agent.storage.polling_state import PollingState
from pr_agent.monitoring.metrics import metrics, PerformanceTracker, StructuredLogger
from pr_agent.notifications import notify_review_started, notify_review_completed, notify_review_failed

setup_logger(fmt=LoggingFormat.JSON, level=get_settings().get("CONFIG.LOG_LEVEL", "DEBUG"))

# Initialize structured logger
structured_logger = StructuredLogger(__name__)


def process_pr_sync(pr_url: str, commands: list, log_context: dict):
    """
    Synchronous wrapper for PR processing (for multiprocessing)

    Args:
        pr_url: PR URL
        commands: List of commands to run
        log_context: Logging context
    """
    try:
        asyncio.run(_run_commands_sequentially(commands, pr_url, log_context))
    except Exception as e:
        get_logger().error(f"Error processing PR {pr_url}: {e}", artifact={"traceback": traceback.format_exc()})


async def process_pr(pr_url: str, commands: list, log_context: dict):
    """
    Process a single PR with commands

    Args:
        pr_url: PR URL
        commands: List of commands to execute
        log_context: Logging context
    """
    start_time = time.time()
    repo_name = log_context.get('repository', 'unknown')
    pr_number = log_context.get('pr_number', 'unknown')
    pr_author = log_context.get('author', 'unknown')
    pr_title = log_context.get('title', '')

    # Build PR data for notifications
    pr_data = {
        'repository': repo_name,
        'pr_number': pr_number,
        'author': pr_author,
        'title': pr_title,
        'url': pr_url
    }

    try:
        # Notify review started
        await notify_review_started(pr_data)

        with PerformanceTracker("process_pr") as tracker:
            tracker.add_metadata(pr_url=pr_url, repository=repo_name)
            await _run_commands_sequentially(commands, pr_url, log_context)

        duration = time.time() - start_time
        metrics.track_pr_review(repo_name, "success", duration)
        structured_logger.info("PR processed successfully", pr_url=pr_url, duration=f"{duration:.2f}s")

        # Notify review completed
        review_data = {
            'duration': duration,
            'commands': commands,
            'status': 'success'
        }
        await notify_review_completed(pr_data, review_data)

    except Exception as e:
        duration = time.time() - start_time
        metrics.track_pr_review(repo_name, "error", duration)
        structured_logger.error("PR processing failed", pr_url=pr_url, error=str(e))
        get_logger().error(f"Error processing PR: {e}", artifact={"traceback": traceback.format_exc()})

        # Notify review failed
        await notify_review_failed(pr_data, str(e))


async def poll_repository(
    provider: BitbucketServerProvider,
    project_key: str,
    repo_slug: str,
    state: PollingState,
    commands: list
):
    """
    Poll a single repository for new/updated PRs

    Args:
        provider: Bitbucket Server provider instance
        project_key: Project key
        repo_slug: Repository slug
        state: Polling state manager
        commands: Commands to run on PRs

    Returns:
        List of tasks to process
    """
    repo_key = f"{project_key}/{repo_slug}"
    tasks = []

    try:
        structured_logger.info("Polling repository", repository=repo_key)

        # List open PRs
        prs = provider.list_pull_requests(project_key, repo_slug, state="OPEN", limit=50)

        get_logger().info(f"Found {len(prs)} open PRs in {repo_key}")

        for pr in prs:
            pr_id = pr['id']
            pr_version = pr['version']
            pr_title = pr['title']

            # Check if PR is new or updated
            if state.is_pr_processed(repo_key, pr_id, pr_version):
                get_logger().debug(f"PR {repo_key}#{pr_id} already processed at version {pr_version}")
                continue

            # Build PR URL
            bitbucket_server_url = get_settings().get("BITBUCKET_SERVER.URL")
            pr_url = f"{bitbucket_server_url}/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}"

            # Check if PR should be processed (apply filters)
            pr_data = {
                "pullRequest": {
                    "id": pr_id,
                    "title": pr_title,
                    "author": {"user": {"name": pr['author']}},
                    "fromRef": pr['fromRef'],
                    "toRef": pr['toRef']
                }
            }

            if not should_process_pr_logic(pr_data):
                get_logger().info(f"PR {repo_key}#{pr_id} filtered out by config")
                # Still mark as processed to avoid checking again
                state.update_pr_state(repo_key, pr_id, pr_version, [], status="filtered")
                continue

            # Determine if new or updated
            is_new = state.get_pr_state(repo_key, pr_id) is None
            status = "new" if is_new else "updated"

            get_logger().info(
                f"Found {status} PR: {repo_key}#{pr_id} (v{pr_version}) - {pr_title}"
            )

            # Add to task queue
            log_context = {
                "server_type": "bitbucket_server_polling",
                "api_url": pr_url,
                "repo": repo_key,
                "pr_id": pr_id,
                "pr_version": pr_version,
                "status": status
            }

            tasks.append((process_pr_sync, (pr_url, commands, log_context)))

            # Update state to mark as processing
            state.update_pr_state(repo_key, pr_id, pr_version, commands, status="processing")

    except Exception as e:
        get_logger().error(
            f"Failed to poll repository {repo_key}: {e}",
            artifact={"traceback": traceback.format_exc()}
        )

    return tasks


async def polling_loop():
    """
    Main polling loop - continuously polls configured repositories
    """
    get_logger().info("Starting Bitbucket Server polling service")

    # Initialize state manager
    state = PollingState()

    # Get configuration
    polling_interval = get_settings().get("bitbucket_server.polling_interval_seconds", 300)
    polling_repos = get_settings().get("bitbucket_server.polling_repositories", [])
    polling_commands = get_settings().get("bitbucket_server.polling_commands", [
        "/describe --pr_description.final_update_message=false",
        "/review",
        "/improve"
    ])

    if not polling_repos:
        get_logger().error("No repositories configured for polling. Set bitbucket_server.polling_repositories")
        return

    get_logger().info(
        f"Polling configuration: {len(polling_repos)} repositories, "
        f"interval: {polling_interval}s, commands: {polling_commands}"
    )

    # Initialize Bitbucket provider
    bitbucket_server_url = get_settings().get("BITBUCKET_SERVER.URL")
    if not bitbucket_server_url:
        get_logger().error("BITBUCKET_SERVER.URL not configured")
        return

    provider = BitbucketServerProvider()

    # Cleanup old state entries on startup
    state.cleanup_old_entries(retention_days=30)

    # Main polling loop
    iteration = 0
    while True:
        try:
            iteration += 1
            get_logger().info(f"Polling iteration #{iteration} started")

            task_queue = deque()

            # Poll each repository
            for repo_config in polling_repos:
                # Parse PROJECT/repo-slug format
                if '/' not in repo_config:
                    get_logger().warning(f"Invalid repository format: {repo_config}. Expected: PROJECT/repo-slug")
                    continue

                project_key, repo_slug = repo_config.split('/', 1)

                # Poll repository
                tasks = await poll_repository(
                    provider,
                    project_key,
                    repo_slug,
                    state,
                    polling_commands
                )

                task_queue.extend(tasks)

            # Process tasks in parallel
            if task_queue:
                get_logger().info(f"Processing {len(task_queue)} PRs")

                max_parallel_tasks = get_settings().get("bitbucket_server.max_parallel_tasks", 10)
                processes = []

                for i, (func, args) in enumerate(task_queue):
                    if i >= max_parallel_tasks:
                        get_logger().warning(
                            f"Dropping {len(task_queue) - max_parallel_tasks} tasks due to parallel limit"
                        )
                        break

                    p = multiprocessing.Process(target=func, args=args)
                    processes.append(p)
                    p.start()

                # Don't wait for processes to complete - move to next iteration
                get_logger().info(f"Started {len(processes)} background processes")

            else:
                get_logger().info("No new or updated PRs found")

            # Periodic cleanup (every 10 iterations)
            if iteration % 10 == 0:
                state.cleanup_old_entries(retention_days=30)
                stats = state.get_statistics()
                get_logger().info(f"Polling statistics: {stats}")

            # Wait for next polling interval
            get_logger().info(f"Waiting {polling_interval}s until next poll")
            await asyncio.sleep(polling_interval)

        except Exception as e:
            get_logger().error(
                f"Polling exception during iteration #{iteration}: {e}",
                artifact={"traceback": traceback.format_exc()}
            )
            # Wait before retrying
            await asyncio.sleep(60)


def start():
    """Start the polling service"""
    try:
        # Check if polling is enabled
        if not get_settings().get("bitbucket_server.enable_polling", False):
            get_logger().error(
                "Bitbucket Server polling is not enabled. "
                "Set bitbucket_server.enable_polling=true in configuration"
            )
            return

        # Run polling loop
        asyncio.run(polling_loop())

    except KeyboardInterrupt:
        get_logger().info("Polling service stopped by user")
    except Exception as e:
        get_logger().error(f"Fatal error in polling service: {e}", artifact={"traceback": traceback.format_exc()})


if __name__ == '__main__':
    start()
