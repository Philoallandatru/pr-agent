"""
Bitbucket Server Polling Service

Automatically polls Bitbucket Server repositories for new/updated PRs
and triggers review commands.
"""

import asyncio
import multiprocessing
import queue
import traceback
import time

from pr_agent.config_loader import get_settings
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider
from pr_agent.log import LoggingFormat, get_logger, setup_logger
from pr_agent.monitoring.metrics import PerformanceTracker, StructuredLogger, metrics
from pr_agent.notifications import notify_review_completed, notify_review_failed, notify_review_started
from pr_agent.servers.bitbucket_server_webhook import _run_commands_sequentially, should_process_pr_logic
from pr_agent.storage.polling_state import PollingState

setup_logger(fmt=LoggingFormat.JSON, level=get_settings().get("CONFIG.LOG_LEVEL", "DEBUG"))

# Initialize structured logger
structured_logger = StructuredLogger(__name__)


async def _safe_notify(notification, *args):
    try:
        await notification(*args)
    except Exception as e:
        get_logger().warning(f"Notification failed: {e}")


def process_pr_sync(pr_url: str, commands: list, log_context: dict, result_queue=None):
    """
    Synchronous wrapper for PR processing (for multiprocessing)

    Args:
        pr_url: PR URL
        commands: List of commands to run
        log_context: Logging context
        result_queue: Optional multiprocessing queue for reporting status
    """
    success = False
    try:
        success = asyncio.run(process_pr(pr_url, commands, log_context))
    except Exception as e:
        get_logger().error(f"Error processing PR {pr_url}: {e}", artifact={"traceback": traceback.format_exc()})
    finally:
        if result_queue is not None:
            result_queue.put(
                {
                    "repo_key": log_context.get("repo"),
                    "pr_id": log_context.get("pr_id"),
                    "pr_version": log_context.get("pr_version"),
                    "success": success,
                }
            )


async def process_pr(pr_url: str, commands: list, log_context: dict):
    """
    Process a single PR with commands

    Args:
        pr_url: PR URL
        commands: List of commands to execute
        log_context: Logging context
    """
    start_time = time.time()
    repo_name = log_context.get('repository') or log_context.get('repo', 'unknown')
    pr_number = log_context.get('pr_number') or log_context.get('pr_id', 'unknown')
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
        await _safe_notify(notify_review_started, pr_data)

        with PerformanceTracker("process_pr") as tracker:
            tracker.add_metadata(pr_url=pr_url, repository=repo_name)
            success = await _run_commands_sequentially(commands, pr_url, log_context)

        if not success:
            raise RuntimeError(f"One or more PR-Agent commands failed for {pr_url}")

        duration = time.time() - start_time
        metrics.track_pr_review(repo_name, "success", duration)
        structured_logger.info("PR processed successfully", pr_url=pr_url, duration=f"{duration:.2f}s")

        # Notify review completed
        review_data = {
            'duration': duration,
            'commands': commands,
            'status': 'success'
        }
        await _safe_notify(notify_review_completed, pr_data, review_data)
        return True

    except Exception as e:
        duration = time.time() - start_time
        metrics.track_pr_review(repo_name, "error", duration)
        structured_logger.error("PR processing failed", pr_url=pr_url, error=str(e))
        get_logger().error(f"Error processing PR: {e}", artifact={"traceback": traceback.format_exc()})

        # Notify review failed
        await _safe_notify(notify_review_failed, pr_data, str(e))
        return False


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

            tasks.append(
                {
                    "repo_key": repo_key,
                    "pr_id": pr_id,
                    "pr_version": pr_version,
                    "pr_url": pr_url,
                    "commands": commands,
                    "log_context": log_context,
                }
            )

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

            task_queue = []

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

                max_parallel_tasks = max(1, int(get_settings().get("bitbucket_server.max_parallel_tasks", 10)))
                review_timeout_seconds = max(
                    1,
                    int(get_settings().get("bitbucket_server.polling_review_timeout_seconds", 1800)),
                )
                tasks_to_run = task_queue[:max_parallel_tasks]
                deferred_count = len(task_queue) - len(tasks_to_run)
                if deferred_count:
                    get_logger().warning(
                        f"Deferring {deferred_count} PRs due to max_parallel_tasks={max_parallel_tasks}"
                    )

                result_queue = multiprocessing.Queue()
                processes = []

                for task in tasks_to_run:
                    state.update_pr_state(
                        task["repo_key"],
                        task["pr_id"],
                        task["pr_version"],
                        task["commands"],
                        status="processing",
                    )

                    p = multiprocessing.Process(
                        target=process_pr_sync,
                        args=(task["pr_url"], task["commands"], task["log_context"], result_queue),
                    )
                    processes.append(
                        {
                            "process": p,
                            "task": task,
                            "started_at": time.monotonic(),
                            "timed_out": False,
                        }
                    )
                    p.start()

                get_logger().info(f"Started {len(processes)} review processes")

                while any(process_info["process"].is_alive() for process_info in processes):
                    now = time.monotonic()
                    for process_info in processes:
                        process = process_info["process"]
                        task = process_info["task"]
                        if not process.is_alive():
                            continue

                        elapsed_seconds = now - process_info["started_at"]
                        if elapsed_seconds <= review_timeout_seconds:
                            continue

                        process_info["timed_out"] = True
                        get_logger().error(
                            f"Review process timed out for {task['repo_key']}#{task['pr_id']} "
                            f"after {review_timeout_seconds}s"
                        )
                        process.terminate()
                        process.join(timeout=5)
                        if process.is_alive():
                            process.kill()
                            process.join(timeout=1)

                    await asyncio.sleep(1)

                for process_info in processes:
                    process = process_info["process"]
                    task = process_info["task"]
                    process.join(timeout=1)
                    if process.is_alive():
                        process_info["timed_out"] = True
                        process.kill()
                        process.join(timeout=1)

                    if process.exitcode != 0:
                        get_logger().error(
                            f"Review process failed for {task['repo_key']}#{task['pr_id']} "
                            f"with exit code {process.exitcode}"
                        )

                results = {}
                for _ in processes:
                    try:
                        result = result_queue.get(timeout=1)
                    except queue.Empty:
                        break

                    result_key = (result.get("repo_key"), result.get("pr_id"), result.get("pr_version"))
                    results[result_key] = bool(result.get("success"))

                for process_info in processes:
                    process = process_info["process"]
                    task = process_info["task"]
                    task_key = (task["repo_key"], task["pr_id"], task["pr_version"])
                    success = (
                        not process_info["timed_out"]
                        and results.get(task_key, False)
                        and process.exitcode == 0
                    )
                    status = "completed" if success else "failed"
                    state.update_pr_state(
                        task["repo_key"],
                        task["pr_id"],
                        task["pr_version"],
                        task["commands"],
                        status=status,
                    )

                result_queue.close()

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
