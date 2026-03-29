from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


@dataclass(slots=True)
class TestCaseAlignmentBundle:
    prompt_items: list[dict]
    results: list[dict]
    matched_case_ids: list[str]


def _settings_section(name: str) -> dict:
    section = get_settings().get(name, {})
    if isinstance(section, dict):
        return section
    try:
        return dict(section)
    except Exception:
        return {}


def _alignment_config() -> dict:
    return _settings_section("testcase_alignment")


def _sync_config() -> dict:
    return _settings_section("confluence_sync")


def _config_value(key: str, default):
    value = _alignment_config().get(key, default)
    return value if value is not None else default


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", (text or "").lower())


def _cache_dir() -> Path:
    sync_cache = _sync_config().get("cache_dir", "")
    fallback = os.path.join(tempfile.gettempdir(), "pr-agent-confluence-sync")
    root = Path(sync_cache or fallback).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _index_file() -> Path:
    return _cache_dir() / "testcases_index.json"


def _extract_case_ids_from_text(text: str, patterns: list[str]) -> list[str]:
    found: list[str] = []
    for pattern in patterns:
        try:
            for match in re.findall(pattern, text or "", flags=re.IGNORECASE):
                case_id = match if isinstance(match, str) else next((m for m in match if m), "")
                case_id = (case_id or "").strip().upper()
                if case_id and case_id not in found:
                    found.append(case_id)
        except re.error:
            continue
    return found


def _extract_case_ids(
    title: str | None,
    description: str | None,
    branch: str | None,
    diff_files: Sequence,
) -> list[str]:
    patterns = _config_value("case_id_patterns", [r"\b(?:TC|CASE|TEST)[-_]?\d+\b"])
    if isinstance(patterns, str):
        patterns = [patterns]
    max_cases = max(1, int(_config_value("max_cases_per_review", 6)))

    text_parts = [title or "", description or "", branch or ""]
    for file_info in diff_files or []:
        filename = getattr(file_info, "filename", "") or ""
        old_filename = getattr(file_info, "old_filename", "") or ""
        patch = getattr(file_info, "patch", "") or ""
        text_parts.extend([filename, old_filename, patch[:1500]])
    merged_text = "\n".join(part for part in text_parts if part)
    ids = _extract_case_ids_from_text(merged_text, patterns)
    return ids[:max_cases]


def _load_cases_by_id(case_ids: Iterable[str]) -> list[dict]:
    case_ids = [case_id.upper() for case_id in case_ids]
    if not case_ids:
        return []
    path = _index_file()
    if not path.exists():
        get_logger().warning(f"TestCase alignment skipped: index file does not exist: {path}")
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        get_logger().warning(f"TestCase alignment skipped: failed to parse index file: {e}")
        return []
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        return []
    by_id = {str(case.get("case_id", "")).upper(): case for case in cases if isinstance(case, dict)}
    matched: list[dict] = []
    for case_id in case_ids:
        case = by_id.get(case_id)
        if case:
            matched.append(case)
    return matched


def _extract_added_lines(patch: str, filename: str) -> list[dict]:
    lines = (patch or "").splitlines()
    extracted: list[dict] = []
    new_line = 0
    hunk_pattern = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for line in lines:
        if line.startswith("@@"):
            match = hunk_pattern.match(line)
            if match:
                new_line = int(match.group(1))
            continue
        if line.startswith("+++"):
            continue
        if line.startswith("-") and not line.startswith("---"):
            continue
        if line.startswith("+"):
            snippet = line[1:].strip()
            if snippet:
                extracted.append(
                    {
                        "source_type": "diff",
                        "path": filename,
                        "start_line": new_line,
                        "end_line": new_line,
                        "snippet": snippet,
                        "tokens": set(_tokenize(snippet)),
                    }
                )
            new_line += 1
            continue
        if line.startswith(" "):
            new_line += 1
    return extracted


def _build_evidence_pool(diff_files: Sequence, repo_context: list[dict]) -> list[dict]:
    pool: list[dict] = []
    for file_info in diff_files or []:
        filename = getattr(file_info, "filename", "") or ""
        patch = getattr(file_info, "patch", "") or ""
        pool.extend(_extract_added_lines(patch, filename))
    for item in repo_context or []:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content", "")).strip()
        if not content:
            continue
        tokens = set(_tokenize(content))
        pool.append(
            {
                "source_type": str(item.get("source_type", "repo_context")),
                "path": str(item.get("path", "")),
                "start_line": int(item.get("start_line", 0) or 0),
                "end_line": int(item.get("end_line", 0) or 0),
                "snippet": content[:220],
                "tokens": tokens,
            }
        )
    return pool


def _match_step(step: str, evidence_pool: list[dict], min_confidence: float) -> tuple[str, dict | None]:
    step_tokens = [token for token in _tokenize(step) if len(token) > 2]
    if not step_tokens:
        return "uncertain", None
    token_set = set(step_tokens)

    best_score = 0.0
    best_evidence = None
    for evidence in evidence_pool:
        overlap = token_set.intersection(evidence.get("tokens", set()))
        if not overlap:
            continue
        score = len(overlap) / max(1, len(token_set))
        if score > best_score:
            best_score = score
            best_evidence = evidence
    if best_score >= min_confidence and best_evidence:
        return "covered", best_evidence
    if best_score >= max(0.2, min_confidence * 0.55):
        return "uncertain", best_evidence
    return "missing", None


def _to_prompt_items(cases: list[dict], max_steps_per_case: int) -> list[dict]:
    prompt_cases: list[dict] = []
    for case in cases:
        steps = case.get("steps", [])
        if not isinstance(steps, list):
            continue
        prompt_cases.append(
            {
                "case_id": str(case.get("case_id", "")).strip(),
                "case_name": str(case.get("case_name", "")).strip() or str(case.get("title", "")).strip(),
                "steps": [str(step).strip() for step in steps[:max_steps_per_case] if str(step).strip()],
                "source_url": str(case.get("source_url", "")).strip(),
                "updated_at": str(case.get("updated_at", "")).strip(),
            }
        )
    return prompt_cases


def _evaluate_cases(cases: list[dict], evidence_pool: list[dict], max_steps_per_case: int, min_confidence: float) -> list[dict]:
    results: list[dict] = []
    for case in cases:
        case_id = str(case.get("case_id", "")).strip()
        case_name = str(case.get("case_name", "")).strip() or str(case.get("title", "")).strip()
        raw_steps = case.get("steps", [])
        steps = [str(step).strip() for step in raw_steps[:max_steps_per_case] if str(step).strip()] if isinstance(raw_steps, list) else []
        if not steps:
            results.append(
                {
                    "case_id": case_id,
                    "case_name": case_name,
                    "alignment_score": 0,
                    "covered_steps": [],
                    "missing_steps": [],
                    "uncertain_steps": ["Unable to parse steps from testcase source."],
                    "evidence_refs": [],
                }
            )
            continue

        covered_steps: list[str] = []
        missing_steps: list[str] = []
        uncertain_steps: list[str] = []
        evidence_refs: list[dict] = []
        for step in steps:
            status, evidence = _match_step(step, evidence_pool, min_confidence=min_confidence)
            if status == "covered":
                covered_steps.append(step)
            elif status == "missing":
                missing_steps.append(step)
            else:
                uncertain_steps.append(step)

            if evidence:
                evidence_refs.append(
                    {
                        "step": step,
                        "path": evidence.get("path", ""),
                        "source_type": evidence.get("source_type", ""),
                        "start_line": evidence.get("start_line", 0),
                        "end_line": evidence.get("end_line", 0),
                        "snippet": evidence.get("snippet", ""),
                    }
                )

        score = int(round(((len(covered_steps) + (0.5 * len(uncertain_steps))) / max(1, len(steps))) * 100))
        results.append(
            {
                "case_id": case_id,
                "case_name": case_name,
                "alignment_score": score,
                "covered_steps": covered_steps,
                "missing_steps": missing_steps,
                "uncertain_steps": uncertain_steps,
                "evidence_refs": evidence_refs,
            }
        )
    return results


def build_testcase_alignment_bundle(
    title: str | None,
    description: str | None,
    branch: str | None,
    diff_files: Sequence,
    repo_context_prompt_items: list[dict] | None = None,
) -> TestCaseAlignmentBundle:
    if not bool(_config_value("enabled", False)):
        return TestCaseAlignmentBundle(prompt_items=[], results=[], matched_case_ids=[])

    case_ids = _extract_case_ids(title=title, description=description, branch=branch, diff_files=diff_files)
    if not case_ids:
        return TestCaseAlignmentBundle(prompt_items=[], results=[], matched_case_ids=[])

    cases = _load_cases_by_id(case_ids)
    if not cases:
        return TestCaseAlignmentBundle(prompt_items=[], results=[], matched_case_ids=case_ids)

    max_steps = max(1, int(_config_value("max_steps_per_case", 20)))
    min_conf = float(_config_value("min_alignment_confidence", 0.55))
    prompt_items = _to_prompt_items(cases, max_steps_per_case=max_steps)
    evidence_pool = _build_evidence_pool(diff_files=diff_files, repo_context=repo_context_prompt_items or [])
    results = _evaluate_cases(cases, evidence_pool=evidence_pool, max_steps_per_case=max_steps, min_confidence=min_conf)
    return TestCaseAlignmentBundle(prompt_items=prompt_items, results=results, matched_case_ids=case_ids)
