import asyncio
import ast
import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Callable, Iterable

from atlassian.bitbucket import Bitbucket

from pr_agent.agent.pr_agent import PRAgent
from pr_agent.config_loader import get_settings
from pr_agent.log import LoggingFormat, get_logger, setup_logger

setup_logger(fmt=LoggingFormat.JSON, level=get_settings().get("CONFIG.LOG_LEVEL", "DEBUG"))


@dataclass(frozen=True)
class PullRequestSnapshot:
    project_key: str
    repo_slug: str
    pr_id: int
    latest_commit: str

    @property
    def state_key(self) -> str:
        return f"{self.project_key}/{self.repo_slug}/{self.pr_id}"

    def pr_url(self, bitbucket_server_url: str) -> str:
        base_url = bitbucket_server_url.rstrip("/")
        return f"{base_url}/projects/{self.project_key}/repos/{self.repo_slug}/pull-requests/{self.pr_id}"


@dataclass(frozen=True)
class BitbucketServerPollingConfig:
    bitbucket_server_url: str
    repositories: list[tuple[str, str]]
    commands: list[str]
    interval_seconds: int = 300
    state_path: str = ".pr_agent_bitbucket_server_polling.sqlite3"
    page_limit: int = 100
    process_unknown_prs: bool = True


class SQLitePollingState:
    def __init__(self, state_path: str | Path):
        self.state_path = Path(state_path)
        if self.state_path.parent != Path("."):
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self):
        with sqlite3.connect(self.state_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pr_polling_state (
                    pr_key TEXT PRIMARY KEY,
                    latest_commit TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def get_latest_commit(self, pr_key: str) -> str | None:
        with sqlite3.connect(self.state_path) as connection:
            row = connection.execute(
                "SELECT latest_commit FROM pr_polling_state WHERE pr_key = ?",
                (pr_key,),
            ).fetchone()
        return row[0] if row else None

    def set_latest_commit(self, pr_key: str, latest_commit: str):
        with sqlite3.connect(self.state_path) as connection:
            connection.execute(
                """
                INSERT INTO pr_polling_state (pr_key, latest_commit, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(pr_key) DO UPDATE SET
                    latest_commit = excluded.latest_commit,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (pr_key, latest_commit),
            )


def _coerce_list(value, setting_name: str) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = ast.literal_eval(value)
        if isinstance(parsed, list):
            return parsed
    raise ValueError(f"{setting_name} must be a list")


def _parse_repositories(repositories: Iterable[str]) -> list[tuple[str, str]]:
    parsed_repositories = []
    for repository in repositories:
        if not isinstance(repository, str) or "/" not in repository:
            raise ValueError("Each BITBUCKET_SERVER_POLLING.REPOSITORIES entry must look like 'PROJECT/repo-slug'")
        project_key, repo_slug = repository.split("/", 1)
        if not project_key or not repo_slug:
            raise ValueError("Each BITBUCKET_SERVER_POLLING.REPOSITORIES entry must look like 'PROJECT/repo-slug'")
        parsed_repositories.append((project_key, repo_slug))
    return parsed_repositories


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def load_config() -> BitbucketServerPollingConfig:
    settings = get_settings()
    bitbucket_server_url = settings.get("BITBUCKET_SERVER.URL", "")
    if not bitbucket_server_url:
        raise ValueError("BITBUCKET_SERVER.URL is required")

    repositories = _parse_repositories(
        _coerce_list(settings.get("BITBUCKET_SERVER_POLLING.REPOSITORIES", []), "BITBUCKET_SERVER_POLLING.REPOSITORIES")
    )
    if not repositories:
        raise ValueError("BITBUCKET_SERVER_POLLING.REPOSITORIES must contain at least one 'PROJECT/repo-slug' entry")

    commands = _coerce_list(
        settings.get("BITBUCKET_SERVER_POLLING.COMMANDS", settings.get("BITBUCKET_SERVER.PR_COMMANDS", ["/review"])),
        "BITBUCKET_SERVER_POLLING.COMMANDS",
    )
    if not commands or not all(isinstance(command, str) for command in commands):
        raise ValueError("BITBUCKET_SERVER_POLLING.COMMANDS must be a non-empty list of strings")

    return BitbucketServerPollingConfig(
        bitbucket_server_url=bitbucket_server_url,
        repositories=repositories,
        commands=commands,
        interval_seconds=int(settings.get("BITBUCKET_SERVER_POLLING.INTERVAL_SECONDS", 300)),
        state_path=settings.get("BITBUCKET_SERVER_POLLING.STATE_PATH", ".pr_agent_bitbucket_server_polling.sqlite3"),
        page_limit=int(settings.get("BITBUCKET_SERVER_POLLING.PAGE_LIMIT", 100)),
        process_unknown_prs=_coerce_bool(settings.get("BITBUCKET_SERVER_POLLING.PROCESS_UNKNOWN_PRS", True)),
    )


def build_bitbucket_client(config: BitbucketServerPollingConfig) -> Bitbucket:
    settings = get_settings()
    bearer_token = settings.get("BITBUCKET_SERVER.BEARER_TOKEN", None)
    if bearer_token:
        return Bitbucket(url=config.bitbucket_server_url, token=bearer_token)

    return Bitbucket(
        url=config.bitbucket_server_url,
        username=settings.get("BITBUCKET_SERVER.USERNAME", None),
        password=settings.get("BITBUCKET_SERVER.PASSWORD", None),
    )


def collect_open_pull_requests(client, project_key: str, repo_slug: str, limit: int = 100) -> list[PullRequestSnapshot]:
    pull_requests = []
    start = 0
    path = f"rest/api/1.0/projects/{project_key}/repos/{repo_slug}/pull-requests"

    while True:
        response = client.get(path, params={"state": "OPEN", "limit": limit, "start": start})
        for item in response.get("values", []):
            to_repository = item.get("toRef", {}).get("repository", {})
            project = to_repository.get("project", {})
            pull_requests.append(
                PullRequestSnapshot(
                    project_key=project.get("key", project_key),
                    repo_slug=to_repository.get("slug", repo_slug),
                    pr_id=item["id"],
                    latest_commit=item["fromRef"]["latestCommit"],
                )
            )

        if response.get("isLastPage", True):
            break
        start = response["nextPageStart"]

    return pull_requests


async def _handle_pr_agent_command(pr_url: str, command: str):
    return await PRAgent().handle_request(pr_url, command)


async def run_polling_cycle(
    client,
    state: SQLitePollingState,
    config: BitbucketServerPollingConfig,
    handle_command: Callable[[str, str], Awaitable[bool | None]] = _handle_pr_agent_command,
):
    for project_key, repo_slug in config.repositories:
        pull_requests = collect_open_pull_requests(client, project_key, repo_slug, limit=config.page_limit)
        for pull_request in pull_requests:
            saved_commit = state.get_latest_commit(pull_request.state_key)
            if saved_commit == pull_request.latest_commit:
                continue
            if saved_commit is None and not config.process_unknown_prs:
                state.set_latest_commit(pull_request.state_key, pull_request.latest_commit)
                continue

            pr_url = pull_request.pr_url(config.bitbucket_server_url)
            get_logger().info(f"Running polling commands for {pr_url}")
            for command in config.commands:
                command_result = await handle_command(pr_url, command)
                if command_result is False:
                    raise RuntimeError(f"Polling command failed for {pr_url}: {command}")
            state.set_latest_commit(pull_request.state_key, pull_request.latest_commit)


async def polling_loop():
    config = load_config()
    client = build_bitbucket_client(config)
    state = SQLitePollingState(config.state_path)

    get_logger().info(
        f"Starting Bitbucket Server polling for {len(config.repositories)} repositories "
        f"every {config.interval_seconds} seconds"
    )

    while True:
        try:
            await run_polling_cycle(client, state, config)
        except Exception as error:
            get_logger().error(f"Bitbucket Server polling cycle failed: {error}")
        await asyncio.sleep(config.interval_seconds)


def start():
    asyncio.run(polling_loop())


if __name__ == "__main__":
    os.environ.setdefault("CONFIG__GIT_PROVIDER", "bitbucket_server")
    start()
