import subprocess

import pytest

from pr_agent.algo.agentic_review import (
    AgenticReviewLoop,
    AgenticReviewPromptRunner,
    ReadOnlyRepoToolExecutor,
    build_agentic_review_prompt_runner,
    is_agentic_review_enabled,
    resolve_agentic_repo_root,
)
from pr_agent.config_loader import get_settings
from pr_agent.tools.pr_code_suggestions import PRCodeSuggestions
from pr_agent.tools.pr_reviewer import PRReviewer


@pytest.fixture
def restore_agentic_review_settings():
    old_values = {
        "AGENTIC_REVIEW.ENABLED": get_settings().get("AGENTIC_REVIEW.ENABLED", None),
        "AGENTIC_REVIEW.COMMANDS": get_settings().get("AGENTIC_REVIEW.COMMANDS", None),
        "AGENTIC_REVIEW.REPO_ROOT": get_settings().get("AGENTIC_REVIEW.REPO_ROOT", None),
        "AGENTIC_REVIEW.MAX_ITERATIONS": get_settings().get("AGENTIC_REVIEW.MAX_ITERATIONS", None),
        "AGENTIC_REVIEW.MAX_TOTAL_CONTEXT_CHARS": get_settings().get("AGENTIC_REVIEW.MAX_TOTAL_CONTEXT_CHARS", None),
        "AGENTIC_REVIEW.MAX_COMMAND_OUTPUT_CHARS": get_settings().get("AGENTIC_REVIEW.MAX_COMMAND_OUTPUT_CHARS", None),
        "AGENTIC_REVIEW.COMMAND_TIMEOUT_SECONDS": get_settings().get("AGENTIC_REVIEW.COMMAND_TIMEOUT_SECONDS", None),
        "AGENTIC_REVIEW.USE_REPO_CONTEXT_CACHE": get_settings().get(
            "AGENTIC_REVIEW.USE_REPO_CONTEXT_CACHE", None),
        "AGENTIC_REVIEW.FORCE_REPO_CONTEXT_REFRESH": get_settings().get(
            "AGENTIC_REVIEW.FORCE_REPO_CONTEXT_REFRESH", None),
        "AGENTIC_REVIEW.FALLBACK_TO_DIRECT_REVIEW": get_settings().get(
            "AGENTIC_REVIEW.FALLBACK_TO_DIRECT_REVIEW", None),
        "PR_REVIEW_PROMPT.SYSTEM": get_settings().get("PR_REVIEW_PROMPT.SYSTEM", None),
        "PR_REVIEW_PROMPT.USER": get_settings().get("PR_REVIEW_PROMPT.USER", None),
        "PR_CODE_SUGGESTIONS_PROMPT.SYSTEM": get_settings().get("PR_CODE_SUGGESTIONS_PROMPT.SYSTEM", None),
        "PR_CODE_SUGGESTIONS_PROMPT.USER": get_settings().get("PR_CODE_SUGGESTIONS_PROMPT.USER", None),
    }
    yield
    for key, value in old_values.items():
        get_settings().set(key, value)


class FakeAiHandler:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def chat_completion(self, model, system, user, temperature=0.2, img_path=None):
        self.calls.append({"model": model, "system": system, "user": user, "temperature": temperature})
        return self.responses.pop(0), "stop"


class FakeToolExecutor:
    def __init__(self):
        self.commands = []

    async def execute(self, command):
        self.commands.append(command)
        return "command: rg foo\nexit_code: 0\nstdout: foo.py:1: foo\nstderr: "


class FakeLogger:
    def __init__(self):
        self.infos = []
        self.warnings = []

    def info(self, message):
        self.infos.append(message)

    def warning(self, message):
        self.warnings.append(message)


@pytest.mark.asyncio
async def test_agent_loop_runs_tool_call_then_returns_final_content():
    ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "FINAL", "content": "review:\\n  security_concerns: |\\n    No"}',
    ])
    tool_executor = FakeToolExecutor()

    loop = AgenticReviewLoop(
        ai_handler=ai_handler,
        tool_executor=tool_executor,
        max_iterations=3,
        max_total_context_chars=10_000,
    )

    result = await loop.run(
        model="openai/local-review-model",
        task_system_prompt="Return YAML only.",
        task_user_prompt="Review this diff.",
        temperature=0.1,
    )

    assert result.final_text == "review:\n  security_concerns: |\n    No"
    assert result.stop_reason == "final"
    assert tool_executor.commands == ["rg foo"]
    assert len(result.traces) == 2
    assert "foo.py:1: foo" in result.traces[0].tool_output


@pytest.mark.asyncio
async def test_agent_loop_logs_start_tool_call_and_stop_reason(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.algo.agentic_review.get_logger", lambda: fake_logger)
    ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "FINAL", "content": "done"}',
    ])
    tool_executor = FakeToolExecutor()
    loop = AgenticReviewLoop(ai_handler=ai_handler, tool_executor=tool_executor, max_iterations=3)

    result = await loop.run(
        model="openai/local-review-model",
        task_system_prompt="Return text.",
        task_user_prompt="Review this diff.",
    )

    assert result.final_text == "done"
    assert any("Agentic review loop started" in message for message in fake_logger.infos)
    assert any("Agentic review tool call: rg foo" in message for message in fake_logger.infos)
    assert any("Agentic review loop stopped: final" in message for message in fake_logger.infos)


@pytest.mark.asyncio
async def test_read_only_repo_tool_executes_allowed_search(tmp_path):
    source_file = tmp_path / "foo.py"
    source_file.write_text("def foo():\n    return 1\n")
    tool_executor = ReadOnlyRepoToolExecutor(repo_root=tmp_path, max_command_output_chars=10_000)

    output = await tool_executor.execute("rg foo")

    assert "command: rg foo" in output
    assert "exit_code: 0" in output
    assert "foo.py" in output
    assert "def foo" in output


@pytest.mark.asyncio
async def test_read_only_repo_tool_blocks_mutating_commands(tmp_path):
    tool_executor = ReadOnlyRepoToolExecutor(repo_root=tmp_path)

    output = await tool_executor.execute("rm -rf .")

    assert output == "Agent command blocked by policy: rm -rf ."


@pytest.mark.asyncio
async def test_read_only_repo_tool_logs_blocked_commands(tmp_path, monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr("pr_agent.algo.agentic_review.get_logger", lambda: fake_logger)
    tool_executor = ReadOnlyRepoToolExecutor(repo_root=tmp_path)

    output = await tool_executor.execute("python setup.py install")

    assert output == "Agent command blocked by policy: python setup.py install"
    assert fake_logger.warnings == ["Agentic review command blocked: python setup.py install"]


@pytest.mark.asyncio
async def test_read_only_repo_tool_supports_ls_and_cat_without_shell_aliases(tmp_path):
    source_file = tmp_path / "foo.py"
    source_file.write_text("def foo():\n    return 1\n")
    tool_executor = ReadOnlyRepoToolExecutor(repo_root=tmp_path, max_command_output_chars=10_000)

    ls_output = await tool_executor.execute("ls")
    cat_output = await tool_executor.execute("cat foo.py")

    assert "foo.py" in ls_output
    assert "def foo" in cat_output


@pytest.mark.asyncio
async def test_read_only_repo_tool_rejects_paths_outside_repo_root(tmp_path):
    outside_file = tmp_path.parent / "outside-agent-secret.txt"
    outside_file.write_text("secret")
    tool_executor = ReadOnlyRepoToolExecutor(repo_root=tmp_path)

    output = await tool_executor.execute(f"cat ../{outside_file.name}")

    assert "path escapes repository root" in output


@pytest.mark.asyncio
async def test_read_only_repo_tool_truncates_large_output(tmp_path):
    source_file = tmp_path / "foo.py"
    source_file.write_text("foo\n" * 100)
    tool_executor = ReadOnlyRepoToolExecutor(repo_root=tmp_path, max_command_output_chars=80)

    output = await tool_executor.execute("rg foo")

    assert len(output) > 80
    assert output.endswith("...(truncated)")


@pytest.mark.asyncio
async def test_read_only_repo_tool_reports_timeout(tmp_path, monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="rg foo", timeout=1)

    monkeypatch.setattr("pr_agent.algo.agentic_review.subprocess.run", raise_timeout)
    tool_executor = ReadOnlyRepoToolExecutor(repo_root=tmp_path, command_timeout_seconds=1)

    output = await tool_executor.execute("rg foo")

    assert output == "Agent command timeout: rg foo, timeout=1s"


@pytest.mark.asyncio
async def test_agent_loop_blocks_duplicate_tool_calls():
    ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "FINAL", "content": "No issues found."}',
    ])
    tool_executor = FakeToolExecutor()
    loop = AgenticReviewLoop(ai_handler=ai_handler, tool_executor=tool_executor, max_iterations=5)

    result = await loop.run(
        model="openai/local-review-model",
        task_system_prompt="Return text.",
        task_user_prompt="Review this diff.",
    )

    assert result.final_text == "No issues found."
    assert tool_executor.commands == ["rg foo"]
    assert result.traces[1].warning == "Duplicate tool call blocked: rg foo"


@pytest.mark.asyncio
async def test_agent_loop_forces_final_when_context_budget_is_reached():
    ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "FINAL", "content": "Forced final review."}',
    ])
    tool_executor = FakeToolExecutor()
    loop = AgenticReviewLoop(
        ai_handler=ai_handler,
        tool_executor=tool_executor,
        max_iterations=5,
        max_total_context_chars=1,
    )

    result = await loop.run(
        model="openai/local-review-model",
        task_system_prompt="Return text.",
        task_user_prompt="Review this diff.",
    )

    assert result.final_text == "Forced final review."
    assert result.stop_reason == "max_iterations_or_context_limit"
    assert "Return FINAL only." in ai_handler.calls[-1]["user"]


@pytest.mark.asyncio
async def test_agent_loop_treats_unknown_action_as_unstructured_response():
    ai_handler = FakeAiHandler(['{"action": "THINK", "content": "hmm"}'])
    tool_executor = FakeToolExecutor()
    loop = AgenticReviewLoop(ai_handler=ai_handler, tool_executor=tool_executor)

    result = await loop.run(
        model="openai/local-review-model",
        task_system_prompt="Return text.",
        task_user_prompt="Review this diff.",
    )

    assert result.stop_reason == "unstructured_response"
    assert result.final_text == '{"action": "THINK", "content": "hmm"}'
    assert tool_executor.commands == []


@pytest.mark.asyncio
async def test_prompt_runner_returns_agent_final_text(tmp_path):
    source_file = tmp_path / "foo.py"
    source_file.write_text("def foo():\n    return 1\n")
    ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "FINAL", "content": "review:\\n  security_concerns: |\\n    No"}',
    ])
    runner = AgenticReviewPromptRunner(
        ai_handler=ai_handler,
        repo_root=tmp_path,
        max_iterations=3,
        max_total_context_chars=10_000,
        max_command_output_chars=10_000,
    )

    final_text = await runner.run(
        model="openai/local-review-model",
        system_prompt="Return YAML only.",
        user_prompt="Review this diff.",
        temperature=0.1,
    )

    assert final_text == "review:\n  security_concerns: |\n    No"
    assert "foo.py" in ai_handler.calls[1]["user"]


@pytest.mark.asyncio
async def test_prompt_runner_uses_local_provider_repo_path(tmp_path, restore_agentic_review_settings):
    source_file = tmp_path / "sentinel.py"
    source_file.write_text("def provider_root():\n    return True\n")
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", "")

    class FakeLocalProvider:
        repo_path = tmp_path

    ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "cat sentinel.py"}',
        '{"action": "FINAL", "content": "done"}',
    ])

    runner = build_agentic_review_prompt_runner(ai_handler, git_provider=FakeLocalProvider())
    final_text = await runner.run(
        model="openai/local-review-model",
        system_prompt="Return text.",
        user_prompt="Review this diff.",
    )

    assert final_text == "done"
    assert "provider_root" in ai_handler.calls[1]["user"]


def test_resolve_agentic_repo_root_finds_git_root_from_subdirectory(tmp_path, restore_agentic_review_settings):
    (tmp_path / ".git").mkdir()
    nested_dir = tmp_path / "packages" / "service"
    nested_dir.mkdir(parents=True)
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", "")

    repo_root = resolve_agentic_repo_root(start_path=nested_dir)

    assert repo_root == tmp_path


def test_resolve_agentic_repo_root_rejects_missing_configured_repo_root(
    tmp_path,
    restore_agentic_review_settings,
):
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", str(tmp_path / "missing-repo"))

    with pytest.raises(ValueError, match="repo_root is not a directory"):
        resolve_agentic_repo_root()


def test_resolve_agentic_repo_root_can_use_repo_context_cache(
    tmp_path,
    monkeypatch,
    restore_agentic_review_settings,
):
    cached_repo = tmp_path / "cached-repo"
    cached_repo.mkdir()
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", "")
    get_settings().set("AGENTIC_REVIEW.USE_REPO_CONTEXT_CACHE", True)
    get_settings().set("AGENTIC_REVIEW.FORCE_REPO_CONTEXT_REFRESH", True)

    class FakeProvider:
        def get_git_repo_url(self, pr_url):
            return f"https://example.com/org/repo.git?from={pr_url}"

        def get_pr_branch(self):
            return "feature/agentic"

    class FakeAnalyzer:
        def clone_repository(self, repo_url, branch, force_refresh=False):
            assert repo_url == "https://example.com/org/repo.git?from=https://example.com/org/repo/pull/1"
            assert branch == "feature/agentic"
            assert force_refresh is True
            return cached_repo

    monkeypatch.setattr("pr_agent.algo.agentic_review.RepoContextAnalyzer", FakeAnalyzer)

    repo_root = resolve_agentic_repo_root(
        git_provider=FakeProvider(),
        pr_url="https://example.com/org/repo/pull/1",
    )

    assert repo_root == cached_repo


def test_resolve_agentic_repo_root_reports_repo_context_clone_failure(
    monkeypatch,
    restore_agentic_review_settings,
):
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", "")
    get_settings().set("AGENTIC_REVIEW.USE_REPO_CONTEXT_CACHE", True)

    class FakeProvider:
        def get_git_repo_url(self, pr_url):
            return "https://example.com/org/repo.git"

        def get_pr_branch(self):
            return "feature/agentic"

    class FakeAnalyzer:
        def clone_repository(self, repo_url, branch, force_refresh=False):
            return None

    monkeypatch.setattr("pr_agent.algo.agentic_review.RepoContextAnalyzer", FakeAnalyzer)

    with pytest.raises(ValueError, match="Could not prepare cached repository"):
        resolve_agentic_repo_root(git_provider=FakeProvider(), pr_url="https://example.com/org/repo/pull/1")


def test_agentic_review_is_enabled_only_for_configured_commands(restore_agentic_review_settings):
    get_settings().set("AGENTIC_REVIEW.ENABLED", False)
    get_settings().set("AGENTIC_REVIEW.COMMANDS", ["review"])

    assert is_agentic_review_enabled("review") is False

    get_settings().set("AGENTIC_REVIEW.ENABLED", True)

    assert is_agentic_review_enabled("review") is True
    assert is_agentic_review_enabled("describe") is False


def test_agentic_review_default_configuration_keys_are_present():
    agentic_review_settings = get_settings().agentic_review

    assert agentic_review_settings.enabled is False
    assert agentic_review_settings.commands == ["review", "improve"]
    assert agentic_review_settings.repo_root == ""
    assert agentic_review_settings.use_repo_context_cache is False
    assert agentic_review_settings.force_repo_context_refresh is False
    assert agentic_review_settings.max_iterations == 8
    assert agentic_review_settings.max_total_context_chars == 40_000
    assert agentic_review_settings.command_timeout_seconds == 10
    assert agentic_review_settings.max_command_output_chars == 40_000
    assert agentic_review_settings.fallback_to_direct_review is True


@pytest.mark.asyncio
async def test_pr_reviewer_uses_agentic_review_when_enabled(tmp_path, restore_agentic_review_settings):
    source_file = tmp_path / "foo.py"
    source_file.write_text("def foo():\n    return 1\n")
    get_settings().set("AGENTIC_REVIEW.ENABLED", True)
    get_settings().set("AGENTIC_REVIEW.COMMANDS", ["review"])
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", str(tmp_path))
    get_settings().set("AGENTIC_REVIEW.MAX_ITERATIONS", 3)
    get_settings().set("AGENTIC_REVIEW.MAX_TOTAL_CONTEXT_CHARS", 10_000)
    get_settings().set("AGENTIC_REVIEW.MAX_COMMAND_OUTPUT_CHARS", 10_000)
    get_settings().set("PR_REVIEW_PROMPT.SYSTEM", "Return YAML only.")
    get_settings().set("PR_REVIEW_PROMPT.USER", "Review {{ diff }}")

    reviewer = PRReviewer.__new__(PRReviewer)
    reviewer.vars = {"diff": ""}
    reviewer.patches_diff = "diff text"
    reviewer.ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "FINAL", "content": "review:\\n  security_concerns: |\\n    No"}',
    ])

    prediction = await reviewer._get_prediction("openai/local-review-model")

    assert prediction == "review:\n  security_concerns: |\n    No"
    assert "foo.py" in reviewer.ai_handler.calls[1]["user"]


@pytest.mark.asyncio
async def test_pr_reviewer_passes_provider_repo_path_to_agentic_runner(tmp_path, restore_agentic_review_settings):
    source_file = tmp_path / "review_context.py"
    source_file.write_text("REVIEW_CONTEXT = True\n")
    get_settings().set("AGENTIC_REVIEW.ENABLED", True)
    get_settings().set("AGENTIC_REVIEW.COMMANDS", ["review"])
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", "")
    get_settings().set("AGENTIC_REVIEW.MAX_ITERATIONS", 3)
    get_settings().set("AGENTIC_REVIEW.MAX_TOTAL_CONTEXT_CHARS", 10_000)
    get_settings().set("AGENTIC_REVIEW.MAX_COMMAND_OUTPUT_CHARS", 10_000)
    get_settings().set("PR_REVIEW_PROMPT.SYSTEM", "Return YAML only.")
    get_settings().set("PR_REVIEW_PROMPT.USER", "Review {{ diff }}")

    class FakeLocalProvider:
        repo_path = tmp_path

    reviewer = PRReviewer.__new__(PRReviewer)
    reviewer.vars = {"diff": ""}
    reviewer.patches_diff = "diff text"
    reviewer.git_provider = FakeLocalProvider()
    reviewer.ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "cat review_context.py"}',
        '{"action": "FINAL", "content": "review:\\n  security_concerns: |\\n    No"}',
    ])

    prediction = await reviewer._get_prediction("openai/local-review-model")

    assert prediction == "review:\n  security_concerns: |\n    No"
    assert "REVIEW_CONTEXT = True" in reviewer.ai_handler.calls[1]["user"]


@pytest.mark.asyncio
async def test_pr_code_suggestions_uses_agentic_review_when_enabled(tmp_path, restore_agentic_review_settings):
    source_file = tmp_path / "foo.py"
    source_file.write_text("def foo():\n    return 1\n")
    get_settings().set("AGENTIC_REVIEW.ENABLED", True)
    get_settings().set("AGENTIC_REVIEW.COMMANDS", ["improve"])
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", str(tmp_path))
    get_settings().set("AGENTIC_REVIEW.MAX_ITERATIONS", 3)
    get_settings().set("AGENTIC_REVIEW.MAX_TOTAL_CONTEXT_CHARS", 10_000)
    get_settings().set("AGENTIC_REVIEW.MAX_COMMAND_OUTPUT_CHARS", 10_000)
    get_settings().set("PR_CODE_SUGGESTIONS_PROMPT.SYSTEM", "Return YAML only.")
    get_settings().set("PR_CODE_SUGGESTIONS_PROMPT.USER", "Improve {{ diff }}")

    suggestions = PRCodeSuggestions.__new__(PRCodeSuggestions)
    suggestions.vars = {"diff": "", "diff_no_line_numbers": ""}
    suggestions.pr_code_suggestions_prompt_system = get_settings().pr_code_suggestions_prompt.system
    suggestions.pr_code_suggestions_prompt_user = get_settings().pr_code_suggestions_prompt.user
    suggestions.ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "rg foo"}',
        '{"action": "FINAL", "content": "code_suggestions:\\n  - relevant_file: |\\n      foo.py"}',
    ])
    suggestions._prepare_pr_code_suggestions = lambda response: {"code_suggestions": [{"relevant_file": "foo.py"}]}

    async def no_reflection(*args, **kwargs):
        return None

    suggestions.self_reflect_on_suggestions = no_reflection

    prediction = await suggestions._get_prediction(
        "openai/local-review-model",
        patches_diff="diff text",
        patches_diff_no_line_number="diff text",
    )

    assert prediction == {"code_suggestions": [{"relevant_file": "foo.py", "score": 7, "score_why": ""}]}
    assert "foo.py" in suggestions.ai_handler.calls[1]["user"]


@pytest.mark.asyncio
async def test_pr_code_suggestions_passes_provider_repo_path_to_agentic_runner(
    tmp_path,
    restore_agentic_review_settings,
):
    source_file = tmp_path / "improve_context.py"
    source_file.write_text("IMPROVE_CONTEXT = True\n")
    get_settings().set("AGENTIC_REVIEW.ENABLED", True)
    get_settings().set("AGENTIC_REVIEW.COMMANDS", ["improve"])
    get_settings().set("AGENTIC_REVIEW.REPO_ROOT", "")
    get_settings().set("AGENTIC_REVIEW.MAX_ITERATIONS", 3)
    get_settings().set("AGENTIC_REVIEW.MAX_TOTAL_CONTEXT_CHARS", 10_000)
    get_settings().set("AGENTIC_REVIEW.MAX_COMMAND_OUTPUT_CHARS", 10_000)
    get_settings().set("PR_CODE_SUGGESTIONS_PROMPT.SYSTEM", "Return YAML only.")
    get_settings().set("PR_CODE_SUGGESTIONS_PROMPT.USER", "Improve {{ diff }}")

    class FakeLocalProvider:
        repo_path = tmp_path

    suggestions = PRCodeSuggestions.__new__(PRCodeSuggestions)
    suggestions.vars = {"diff": "", "diff_no_line_numbers": ""}
    suggestions.git_provider = FakeLocalProvider()
    suggestions.pr_code_suggestions_prompt_system = get_settings().pr_code_suggestions_prompt.system
    suggestions.pr_code_suggestions_prompt_user = get_settings().pr_code_suggestions_prompt.user
    suggestions.ai_handler = FakeAiHandler([
        '{"action": "TOOL_CALL", "command": "cat improve_context.py"}',
        '{"action": "FINAL", "content": "code_suggestions:\\n  - relevant_file: |\\n      improve_context.py"}',
    ])
    suggestions._prepare_pr_code_suggestions = lambda response: {
        "code_suggestions": [{"relevant_file": "improve_context.py"}],
    }

    async def no_reflection(*args, **kwargs):
        return None

    suggestions.self_reflect_on_suggestions = no_reflection

    prediction = await suggestions._get_prediction(
        "openai/local-review-model",
        patches_diff="diff text",
        patches_diff_no_line_number="diff text",
    )

    assert prediction == {"code_suggestions": [{"relevant_file": "improve_context.py", "score": 7, "score_why": ""}]}
    assert "IMPROVE_CONTEXT = True" in suggestions.ai_handler.calls[1]["user"]
