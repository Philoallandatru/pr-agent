import asyncio
import sqlite3

import pytest

from pr_agent.servers.bitbucket_server_polling import (
    BitbucketServerPollingConfig,
    SQLitePollingState,
    collect_open_pull_requests,
    load_config,
    run_polling_cycle,
)


class FakeBitbucketClient:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        page_index = len(self.calls) - 1
        return self.pages[page_index]


class FakeSettings:
    def __init__(self, values):
        self.values = values

    def get(self, key, default=None):
        return self.values.get(key, default)


def test_load_config_parses_json_list_settings(monkeypatch):
    settings = FakeSettings(
        {
            "BITBUCKET_SERVER.URL": "https://bitbucket.example.com/",
            "BITBUCKET_SERVER_POLLING.REPOSITORIES": '["PROJ/repo-a", "OPS/repo-b"]',
            "BITBUCKET_SERVER_POLLING.COMMANDS": '["/review", "/describe"]',
            "BITBUCKET_SERVER_POLLING.INTERVAL_SECONDS": "60",
            "BITBUCKET_SERVER_POLLING.STATE_PATH": "state.sqlite3",
            "BITBUCKET_SERVER_POLLING.PROCESS_UNKNOWN_PRS": "false",
        }
    )
    monkeypatch.setattr("pr_agent.servers.bitbucket_server_polling.get_settings", lambda: settings)

    config = load_config()

    assert config.bitbucket_server_url == "https://bitbucket.example.com/"
    assert config.repositories == [("PROJ", "repo-a"), ("OPS", "repo-b")]
    assert config.commands == ["/review", "/describe"]
    assert config.interval_seconds == 60
    assert config.state_path == "state.sqlite3"
    assert config.process_unknown_prs is False


def test_collect_open_pull_requests_handles_pagination():
    client = FakeBitbucketClient(
        [
            {
                "values": [
                    {
                        "id": 7,
                        "fromRef": {"latestCommit": "abc"},
                        "toRef": {"repository": {"slug": "repo", "project": {"key": "PROJ"}}},
                    }
                ],
                "isLastPage": False,
                "nextPageStart": 25,
            },
            {"values": [], "isLastPage": True},
        ]
    )

    pull_requests = collect_open_pull_requests(client, "PROJ", "repo", limit=25)

    assert len(pull_requests) == 1
    assert pull_requests[0].state_key == "PROJ/repo/7"
    assert pull_requests[0].latest_commit == "abc"
    assert client.calls == [
        ("rest/api/1.0/projects/PROJ/repos/repo/pull-requests", {"state": "OPEN", "limit": 25, "start": 0}),
        ("rest/api/1.0/projects/PROJ/repos/repo/pull-requests", {"state": "OPEN", "limit": 25, "start": 25}),
    ]


def test_run_polling_cycle_runs_commands_only_for_new_or_updated_prs(tmp_path):
    client = FakeBitbucketClient(
        [
            {
                "values": [
                    {
                        "id": 1,
                        "fromRef": {"latestCommit": "new-head"},
                        "toRef": {"repository": {"slug": "repo", "project": {"key": "PROJ"}}},
                    },
                    {
                        "id": 2,
                        "fromRef": {"latestCommit": "old-head"},
                        "toRef": {"repository": {"slug": "repo", "project": {"key": "PROJ"}}},
                    },
                ],
                "isLastPage": True,
            }
        ]
    )
    state = SQLitePollingState(tmp_path / "polling.sqlite3")
    state.set_latest_commit("PROJ/repo/2", "old-head")
    config = BitbucketServerPollingConfig(
        bitbucket_server_url="https://bitbucket.example.com",
        repositories=[("PROJ", "repo")],
        commands=["/review", "/describe"],
    )
    handled = []

    async def handle(pr_url, command):
        handled.append((pr_url, command))

    asyncio.run(run_polling_cycle(client, state, config, handle))

    assert handled == [
        ("https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/1", "/review"),
        ("https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/1", "/describe"),
    ]
    assert state.get_latest_commit("PROJ/repo/1") == "new-head"
    assert state.get_latest_commit("PROJ/repo/2") == "old-head"


def test_run_polling_cycle_can_bootstrap_unknown_prs_without_running_commands(tmp_path):
    client = FakeBitbucketClient(
        [
            {
                "values": [
                    {
                        "id": 1,
                        "fromRef": {"latestCommit": "head"},
                        "toRef": {"repository": {"slug": "repo", "project": {"key": "PROJ"}}},
                    }
                ],
                "isLastPage": True,
            }
        ]
    )
    state = SQLitePollingState(tmp_path / "polling.sqlite3")
    config = BitbucketServerPollingConfig(
        bitbucket_server_url="https://bitbucket.example.com",
        repositories=[("PROJ", "repo")],
        commands=["/review"],
        process_unknown_prs=False,
    )
    handled = []

    async def handle(pr_url, command):
        handled.append((pr_url, command))

    asyncio.run(run_polling_cycle(client, state, config, handle))

    assert handled == []
    assert state.get_latest_commit("PROJ/repo/1") == "head"


def test_run_polling_cycle_does_not_advance_state_when_command_fails(tmp_path):
    client = FakeBitbucketClient(
        [
            {
                "values": [
                    {
                        "id": 1,
                        "fromRef": {"latestCommit": "head"},
                        "toRef": {"repository": {"slug": "repo", "project": {"key": "PROJ"}}},
                    }
                ],
                "isLastPage": True,
            }
        ]
    )
    state = SQLitePollingState(tmp_path / "polling.sqlite3")
    config = BitbucketServerPollingConfig(
        bitbucket_server_url="https://bitbucket.example.com",
        repositories=[("PROJ", "repo")],
        commands=["/review"],
    )

    async def handle(pr_url, command):
        raise RuntimeError("review failed")

    with pytest.raises(RuntimeError, match="review failed"):
        asyncio.run(run_polling_cycle(client, state, config, handle))

    assert state.get_latest_commit("PROJ/repo/1") is None


def test_run_polling_cycle_does_not_advance_state_when_command_returns_false(tmp_path):
    client = FakeBitbucketClient(
        [
            {
                "values": [
                    {
                        "id": 1,
                        "fromRef": {"latestCommit": "head"},
                        "toRef": {"repository": {"slug": "repo", "project": {"key": "PROJ"}}},
                    }
                ],
                "isLastPage": True,
            }
        ]
    )
    state = SQLitePollingState(tmp_path / "polling.sqlite3")
    config = BitbucketServerPollingConfig(
        bitbucket_server_url="https://bitbucket.example.com",
        repositories=[("PROJ", "repo")],
        commands=["/review"],
    )

    async def handle(pr_url, command):
        return False

    with pytest.raises(RuntimeError, match="/review"):
        asyncio.run(run_polling_cycle(client, state, config, handle))

    assert state.get_latest_commit("PROJ/repo/1") is None


def test_sqlite_state_creates_parent_directory(tmp_path):
    state_path = tmp_path / "nested" / "polling.sqlite3"
    state = SQLitePollingState(state_path)
    state.set_latest_commit("PROJ/repo/1", "head")

    with sqlite3.connect(state_path) as connection:
        saved_commit = connection.execute(
            "SELECT latest_commit FROM pr_polling_state WHERE pr_key = ?",
            ("PROJ/repo/1",),
        ).fetchone()[0]

    assert saved_commit == "head"
