"""
Agentic code-review loop for read-only repository exploration.

The loop protocol and trace shape are adapted from Nikita-Filonov/ai-review
(Apache-2.0) to fit PR-Agent's AI handler interface and existing review/improve
output contracts.
"""

import json
import re
import shlex
import subprocess
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pr_agent.algo.repo_context_analyzer import RepoContextAnalyzer
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class AgenticReviewError(Exception):
    """Base exception for agentic review errors"""
    pass


class UnstructuredResponseError(AgenticReviewError):
    """Raised when model returns unstructured response that cannot be parsed"""
    pass


def is_agentic_review_enabled(command: str) -> bool:
    if not get_settings().get("agentic_review.enabled", False):
        return False

    commands = get_settings().get("agentic_review.commands", [])
    return command in commands


def _find_git_root(start_path: str | Path = ".") -> Path:
    current = Path(start_path).resolve()
    if current.is_file():
        current = current.parent

    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent

    if (current / ".git").exists():
        return current
    raise ValueError(f"Could not resolve git repository root from {start_path}")


def _resolve_existing_directory(path: str | Path, source: str) -> Path:
    repo_root = Path(path).resolve()
    if not repo_root.is_dir():
        raise ValueError(f"Configured agentic review {source} is not a directory: {repo_root}")
    return repo_root


def _get_provider_branch(git_provider) -> str:
    branch = git_provider.get_pr_branch()
    if isinstance(branch, str):
        return branch
    return getattr(branch, "name", None) or getattr(branch, "ref", None) or str(branch)


def _resolve_repo_context_cache(git_provider, pr_url: str | None) -> Path | None:
    if not get_settings().get("agentic_review.use_repo_context_cache", False):
        return None
    if not git_provider:
        return None

    effective_pr_url = pr_url or getattr(git_provider, "pr_url", None)
    if not effective_pr_url:
        get_logger().warning("Agentic review repo context cache requested, but PR URL is unavailable")
        return None

    repo_url = git_provider.get_git_repo_url(effective_pr_url)
    branch = _get_provider_branch(git_provider)
    repo_path = RepoContextAnalyzer().clone_repository(
        repo_url,
        branch,
        force_refresh=get_settings().get("agentic_review.force_repo_context_refresh", False),
    )
    if not repo_path:
        message = f"Could not prepare cached repository for agentic review: repo_url={repo_url}, branch={branch}"
        get_logger().warning(message)
        raise ValueError(message)

    return _resolve_existing_directory(repo_path, "repo context cache")


def resolve_agentic_repo_root(git_provider=None, pr_url: str | None = None, start_path: str | Path = ".") -> Path:
    configured_repo_root = get_settings().get("agentic_review.repo_root", "")
    if configured_repo_root:
        return _resolve_existing_directory(configured_repo_root, "repo_root")

    provider_repo_path = getattr(git_provider, "repo_path", None) if git_provider else None
    if provider_repo_path:
        return _resolve_existing_directory(provider_repo_path, "provider repo_path")

    repo_context_root = _resolve_repo_context_cache(git_provider, pr_url)
    if repo_context_root:
        return repo_context_root

    return _find_git_root(start_path)


def build_agentic_review_prompt_runner(
    ai_handler,
    git_provider=None,
    pr_url: str | None = None,
) -> "AgenticReviewPromptRunner":
    repo_root = resolve_agentic_repo_root(git_provider=git_provider, pr_url=pr_url)
    return AgenticReviewPromptRunner(
        ai_handler=ai_handler,
        repo_root=repo_root,
        max_iterations=get_settings().get("agentic_review.max_iterations", 8),
        max_total_context_chars=get_settings().get("agentic_review.max_total_context_chars", 40_000),
        command_timeout_seconds=get_settings().get("agentic_review.command_timeout_seconds", 10),
        max_command_output_chars=get_settings().get("agentic_review.max_command_output_chars", 40_000),
    )


class AgentAction(StrEnum):
    TOOL_CALL = "TOOL_CALL"
    FINAL = "FINAL"


@dataclass
class AgentStep:
    action: AgentAction
    command: str = ""
    content: str = ""


@dataclass
class AgentTrace:
    step: AgentStep
    iteration: int
    raw_output: str
    tool_output: str = ""
    warning: str = ""


@dataclass
class AgentLoopResult:
    final_text: str
    stop_reason: str
    traces: list[AgentTrace] = field(default_factory=list)
    finish_reason: str = "stop"  # AI model finish reason (stop, length, content_filter, etc.)


class AgentToolExecutor(Protocol):
    async def execute(self, command: str) -> str:
        ...


class AgenticReviewLoop:
    def __init__(
        self,
        ai_handler,
        tool_executor: AgentToolExecutor,
        max_iterations: int = 8,
        max_total_context_chars: int = 40_000,
    ):
        # Validate configuration
        if max_iterations <= 0:
            raise ValueError(f"max_iterations must be positive, got {max_iterations}")
        if max_total_context_chars <= 0:
            raise ValueError(f"max_total_context_chars must be positive, got {max_total_context_chars}")

        self.ai_handler = ai_handler
        self.tool_executor = tool_executor
        self.max_iterations = max_iterations
        self.max_total_context_chars = max_total_context_chars

    def _parse_step(self, raw_output: str) -> AgentStep | None:
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError:
            return None

        try:
            action = AgentAction(payload.get("action", ""))
        except ValueError:
            return None
        if action == AgentAction.TOOL_CALL:
            return AgentStep(action=action, command=(payload.get("command") or "").strip())
        return AgentStep(action=action, content=(payload.get("content") or "").strip())

    def _build_agent_system_prompt(self) -> str:
        return (
            "You are a tool-using code-review agent. Return exactly one JSON object. "
            "Use TOOL_CALL to request one read-only repository command, or FINAL with the complete task output."
        )

    def _build_agent_user_prompt(
        self,
        task_system_prompt: str,
        task_user_prompt: str,
        traces: list[AgentTrace],
        force_final: bool = False,
    ) -> str:
        mode = "Return FINAL only." if force_final else "You may call one tool or return FINAL."
        history = "\n\n".join(
            f"Iteration {trace.iteration}\n"
            f"Action: {trace.step.action.value}\n"
            f"Command: {trace.step.command}\n"
            f"Output:\n{trace.tool_output}\n"
            f"Warning: {trace.warning}"
            for trace in traces
        )
        return (
            f"## Agent mode\n{mode}\n\n"
            f"## Task output format\n{task_system_prompt}\n\n"
            f"## Task\n{task_user_prompt}\n\n"
            f"## Agent history\n{history}\n"
        )

    async def _chat(self, model: str, system: str, user: str, temperature: float) -> tuple[str, str]:
        response, finish_reason = await self.ai_handler.chat_completion(
            model=model,
            temperature=temperature,
            system=system,
            user=user,
        )
        return response, finish_reason

    async def run(
        self,
        model: str,
        task_system_prompt: str,
        task_user_prompt: str,
        temperature: float = 0.2,
    ) -> AgentLoopResult:
        get_logger().info(
            f"Agentic review loop started: model={model}, max_iterations={self.max_iterations}, "
            f"max_total_context_chars={self.max_total_context_chars}"
        )
        traces: list[AgentTrace] = []
        context_used = 0
        seen_commands: set[str] = set()
        last_finish_reason = "stop"

        for iteration in range(1, self.max_iterations + 1):
            raw_output, finish_reason = await self._chat(
                model=model,
                temperature=temperature,
                system=self._build_agent_system_prompt(),
                user=self._build_agent_user_prompt(task_system_prompt, task_user_prompt, traces),
            )
            last_finish_reason = finish_reason

            # Check for abnormal termination
            if finish_reason != "stop":
                get_logger().warning(
                    f"Agentic review model terminated abnormally: finish_reason={finish_reason}, "
                    f"iteration={iteration}"
                )

            step = self._parse_step(raw_output)
            if step is None:
                get_logger().warning("Agentic review loop stopped: unstructured_response")
                # Raise exception to trigger fallback model retry
                raise UnstructuredResponseError(
                    f"Model returned unstructured response that could not be parsed. "
                    f"Raw output: {raw_output[:200]}..."
                )

            if step.action == AgentAction.FINAL:
                traces.append(AgentTrace(step=step, iteration=iteration, raw_output=raw_output))

                # Log completion summary
                get_logger().info(
                    f"Agentic review completed: iterations={iteration}, "
                    f"commands_executed={len(seen_commands)}, "
                    f"total_context_used={context_used} chars"
                )

                # Log search summary if enabled
                if get_settings().get("agentic_review.log_search_behavior", True) and seen_commands:
                    get_logger().info(
                        f"Agentic review search summary: {list(seen_commands)}"
                    )

                return AgentLoopResult(
                    final_text=step.content,
                    stop_reason="final",
                    finish_reason=finish_reason,
                    traces=traces
                )

            if step.command in seen_commands:
                get_logger().warning(f"Agentic review duplicate tool call blocked: {step.command}")
                traces.append(AgentTrace(
                    step=step,
                    iteration=iteration,
                    raw_output=raw_output,
                    warning=f"Duplicate tool call blocked: {step.command}",
                ))
                continue

            seen_commands.add(step.command)
            get_logger().info(
                f"Agentic review tool call [{iteration}/{self.max_iterations}]: {step.command}"
            )
            tool_output = await self.tool_executor.execute(step.command)

            # Log tool output summary if enabled
            if get_settings().get("agentic_review.log_search_behavior", True):
                output_preview = (
                    tool_output[:200].replace('\n', ' ')
                    if len(tool_output) > 200
                    else tool_output.replace('\n', ' ')
                )
                get_logger().info(
                    f"Agentic review tool result [{iteration}]: {len(tool_output)} chars, "
                    f"preview: {output_preview}..."
                )

            traces.append(AgentTrace(step=step, iteration=iteration, raw_output=raw_output, tool_output=tool_output))

            # Estimate total context size (tool output + prompt overhead)
            # Rough estimate: tool_output + history + system/user prompts
            # Use 4 chars per token as approximation
            tool_output_chars = len(tool_output)
            prompt_overhead = len(task_system_prompt) + len(task_user_prompt) + len(raw_output)
            history_chars = sum(len(t.tool_output) + len(t.raw_output) for t in traces)
            estimated_total_chars = tool_output_chars + prompt_overhead + history_chars

            context_used += tool_output_chars
            if estimated_total_chars >= self.max_total_context_chars:
                get_logger().warning(
                    f"Agentic review context budget reached: tool_output={context_used}, "
                    f"estimated_total={estimated_total_chars}, limit={self.max_total_context_chars}"
                )
                break

        raw_output, finish_reason = await self._chat(
            model=model,
            temperature=temperature,
            system=self._build_agent_system_prompt(),
            user=self._build_agent_user_prompt(task_system_prompt, task_user_prompt, traces, force_final=True),
        )
        last_finish_reason = finish_reason
        step = self._parse_step(raw_output)
        final_text = step.content if step and step.action == AgentAction.FINAL else raw_output
        traces.append(AgentTrace(
            step=step or AgentStep(action=AgentAction.FINAL, content=raw_output),
            iteration=min(len(traces) + 1, self.max_iterations),
            raw_output=raw_output,
            warning="Forced final response after max iterations or context limit.",
        ))
        get_logger().warning(
            f"Agentic review loop stopped: max_iterations_or_context_limit, traces={len(traces)}, "
            f"commands_executed={len(seen_commands)}, context_used={context_used}, finish_reason={finish_reason}"
        )

        # Log summary of commands executed if enabled
        if get_settings().get("agentic_review.log_search_behavior", True) and seen_commands:
            get_logger().info(
                f"Agentic review search summary: {list(seen_commands)}"
            )

        return AgentLoopResult(
            final_text=final_text,
            stop_reason="max_iterations_or_context_limit",
            finish_reason=last_finish_reason,
            traces=traces,
        )


class ReadOnlyRepoToolExecutor:
    DEFAULT_ALLOW_COMMANDS = [
        re.compile(r"^ls(?:[ \t]+[^\n]*)?$"),
        re.compile(r"^cat(?:[ \t]+[^\n]*)?$"),
        re.compile(r"^rg(?:[ \t]+[^\n]*)?$"),
        re.compile(r"^grep(?:[ \t]+[^\n]*)?$"),
        re.compile(r"^git[ \t]+(?:status|show|diff|log|rev-parse|ls-files)(?:[ \t]+[^\n]*)?$"),
    ]

    def __init__(
        self,
        repo_root: str | Path,
        allow_commands: list[re.Pattern[str]] | None = None,
        command_timeout_seconds: int = 10,
        max_command_output_chars: int = 40_000,
    ):
        # Validate configuration
        if command_timeout_seconds <= 0:
            raise ValueError(f"command_timeout_seconds must be positive, got {command_timeout_seconds}")
        if max_command_output_chars <= 0:
            raise ValueError(f"max_command_output_chars must be positive, got {max_command_output_chars}")

        self.repo_root = Path(repo_root).resolve()
        self.allow_commands = allow_commands or self.DEFAULT_ALLOW_COMMANDS
        self.command_timeout_seconds = command_timeout_seconds
        self.max_command_output_chars = max_command_output_chars

    def _is_allowed(self, command: str) -> bool:
        return any(pattern.fullmatch(command) for pattern in self.allow_commands)

    def _truncate(self, text: str) -> str:
        if len(text) <= self.max_command_output_chars:
            return text
        return text[:self.max_command_output_chars] + "\n...(truncated)"

    def _resolve_repo_path(self, path: str = ".") -> Path:
        # Check for symlinks before resolving to prevent escape via symlink
        candidate = self.repo_root / path
        if candidate.is_symlink():
            raise ValueError(f"symlinks not allowed: {path}")

        resolved = candidate.resolve()
        if resolved != self.repo_root and self.repo_root not in resolved.parents:
            raise ValueError(f"path escapes repository root: {path}")
        return resolved

    def _format_output(self, command: str, exit_code: int, stdout: str = "", stderr: str = "") -> str:
        return self._truncate(
            f"command: {command}\n"
            f"exit_code: {exit_code}\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}"
        )

    def _execute_builtin(self, command: str, argv: list[str]) -> str | None:
        if argv[0] == "ls":
            path = self._resolve_repo_path(argv[1] if len(argv) > 1 else ".")
            if not path.exists():
                return self._format_output(command, 1, stderr=f"path not found: {path}")
            if path.is_file():
                stdout = path.name
            else:
                stdout = "\n".join(sorted(child.name for child in path.iterdir()))
            return self._format_output(command, 0, stdout=stdout)

        if argv[0] == "cat":
            if len(argv) < 2:
                return self._format_output(command, 1, stderr="cat requires a file path")
            path = self._resolve_repo_path(argv[1])
            if not path.is_file():
                return self._format_output(command, 1, stderr=f"file not found: {path}")

            # Check if file is binary by trying to read first few bytes
            try:
                with open(path, 'rb') as f:
                    sample = f.read(8192)
                    # Check for null bytes (common in binary files)
                    if b'\x00' in sample:
                        return self._format_output(command, 0, stdout=f"<binary file: {path.name}>")
            except Exception:
                pass

            return self._format_output(command, 0, stdout=path.read_text(encoding="utf-8", errors="replace"))

        return None

    async def execute(self, command: str) -> str:
        command = (command or "").strip()
        if not command:
            get_logger().warning("Agentic review: empty command rejected")
            return "Agent command rejected: empty command"
        if not self._is_allowed(command):
            get_logger().warning(f"Agentic review: command blocked by policy: {command}")
            return f"Agent command blocked by policy: {command}"

        get_logger().info(f"Agentic review: executing command: {command}")

        try:
            argv = shlex.split(command)
        except ValueError as error:
            return f"Agent command parse error: {command} | {error}"

        try:
            builtin_output = self._execute_builtin(command, argv)
        except Exception as error:
            return f"Agent command failed: {command}: {error}"
        if builtin_output is not None:
            return builtin_output

        try:
            result = subprocess.run(
                argv,
                cwd=self.repo_root,
                check=False,
                capture_output=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.command_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return f"Agent command timeout: {command}, timeout={self.command_timeout_seconds}s"
        except Exception as error:
            return f"Agent command failed: {command}: {error}"

        return self._format_output(command, result.returncode, result.stdout or "", result.stderr or "")


class AgenticReviewPromptRunner:
    def __init__(
        self,
        ai_handler,
        repo_root: str | Path,
        max_iterations: int = 8,
        max_total_context_chars: int = 40_000,
        command_timeout_seconds: int = 10,
        max_command_output_chars: int = 40_000,
    ):
        tool_executor = ReadOnlyRepoToolExecutor(
            repo_root=repo_root,
            command_timeout_seconds=command_timeout_seconds,
            max_command_output_chars=max_command_output_chars,
        )
        self.loop = AgenticReviewLoop(
            ai_handler=ai_handler,
            tool_executor=tool_executor,
            max_iterations=max_iterations,
            max_total_context_chars=max_total_context_chars,
        )

    async def run(self, model: str, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        result = await self.loop.run(
            model=model,
            task_system_prompt=system_prompt,
            task_user_prompt=user_prompt,
            temperature=temperature,
        )

        # Log warning if model terminated abnormally
        if result.finish_reason != "stop":
            get_logger().warning(
                f"Agentic review completed with abnormal finish_reason: {result.finish_reason}. "
                f"Output may be incomplete or truncated. stop_reason={result.stop_reason}"
            )

        return result.final_text
