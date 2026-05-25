import pytest

from pr_agent.servers import bitbucket_server_polling, bitbucket_server_webhook
from pr_agent.storage.polling_state import PollingState


class FakeProvider:
    def list_pull_requests(self, project_key, repo_slug, state="OPEN", limit=50):
        return [
            {
                "id": 123,
                "version": 5,
                "title": "Review me",
                "author": "alice",
                "fromRef": {"displayId": "feature/demo"},
                "toRef": {
                    "displayId": "main",
                    "repository": {"slug": repo_slug, "project": {"key": project_key}},
                },
            }
        ]


@pytest.mark.asyncio
async def test_poll_repository_does_not_mark_pr_processing_before_execution(tmp_path):
    state = PollingState(state_file=str(tmp_path / "polling-state.json"))
    bitbucket_server_polling.get_settings().set("BITBUCKET_SERVER.URL", "https://bitbucket.example.com")

    tasks = await bitbucket_server_polling.poll_repository(
        FakeProvider(),
        "PROJ",
        "repo",
        state,
        ["/review"],
    )

    assert len(tasks) == 1
    assert tasks[0]["repo_key"] == "PROJ/repo"
    assert state.get_pr_state("PROJ/repo", 123) is None


@pytest.mark.asyncio
async def test_run_commands_sequentially_returns_false_when_agent_fails(monkeypatch):
    class FailingAgent:
        async def handle_request(self, url, body):
            return False

    monkeypatch.setattr(bitbucket_server_webhook, "PRAgent", FailingAgent)
    monkeypatch.setattr(bitbucket_server_webhook, "_process_command", lambda command, url: command)

    success = await bitbucket_server_webhook._run_commands_sequentially(["/review"], "https://pr", {})

    assert success is False


@pytest.mark.asyncio
async def test_process_pr_ignores_notification_failures(monkeypatch):
    async def failing_notification(*args):
        raise RuntimeError("notification endpoint down")

    async def successful_commands(commands, pr_url, log_context):
        return True

    monkeypatch.setattr(bitbucket_server_polling, "notify_review_started", failing_notification)
    monkeypatch.setattr(bitbucket_server_polling, "notify_review_completed", failing_notification)
    monkeypatch.setattr(bitbucket_server_polling, "_run_commands_sequentially", successful_commands)

    success = await bitbucket_server_polling.process_pr(
        "https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123",
        ["/review"],
        {"repo": "PROJ/repo", "pr_id": 123},
    )

    assert success is True


def test_process_command_preserves_quoted_config_value(monkeypatch):
    updated_args = []

    def fake_update_settings_from_args(args):
        updated_args.extend(args)
        return []

    monkeypatch.setattr(bitbucket_server_webhook, "apply_repo_settings", lambda url: None)
    monkeypatch.setattr(bitbucket_server_webhook, "update_settings_from_args", fake_update_settings_from_args)

    command = bitbucket_server_webhook._process_command(
        '/review --pr_reviewer.extra_instructions="focus on retry safety"',
        "https://pr",
    )

    assert command == "/review"
    assert updated_args == ["--pr_reviewer.extra_instructions=focus on retry safety"]
