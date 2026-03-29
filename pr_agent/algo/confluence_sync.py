from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import html2text
from atlassian import Confluence

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger

_INDEX_FILE_NAME = "testcases_index.json"
_STATE_FILE_NAME = "sync_state.json"
_DEFAULT_PAGE_LIMIT = 50
_MAX_PAGES_PER_SYNC = 2_000


@dataclass(slots=True)
class ConfluenceSyncResult:
    success: bool
    synced_cases: int
    synced_pages: int
    cache_file: str
    message: str


def _settings_section(name: str) -> dict:
    section = get_settings().get(name, {})
    if isinstance(section, dict):
        return section
    try:
        return dict(section)
    except Exception:
        return {}


def _sync_settings() -> dict:
    return _settings_section("confluence_sync")


def _secrets_section(name: str) -> dict:
    section = get_settings(use_context=False).get(name, {})
    if isinstance(section, dict):
        return section
    try:
        return dict(section)
    except Exception:
        return {}


def _cache_dir() -> Path:
    configured = _sync_settings().get("cache_dir", "") or os.path.join(tempfile.gettempdir(), "pr-agent-confluence-sync")
    root = Path(str(configured)).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _index_file() -> Path:
    return _cache_dir() / _INDEX_FILE_NAME


def _state_file() -> Path:
    return _cache_dir() / _STATE_FILE_NAME


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _confluence_client() -> Confluence | None:
    settings = _sync_settings()
    secrets = _secrets_section("confluence")
    base_url = settings.get("base_url", "") or secrets.get("base_url", "")
    if not base_url:
        get_logger().warning("Confluence sync skipped: missing confluence_sync.base_url or confluence.base_url")
        return None

    token = secrets.get("token", "")
    username = secrets.get("username", "")
    password = secrets.get("password", "")
    verify_ssl = bool(settings.get("verify_ssl", True))
    timeout = int(settings.get("request_timeout_seconds", 30))

    try:
        if token:
            return Confluence(url=base_url, token=token, verify_ssl=verify_ssl, timeout=timeout)
        if username and password:
            return Confluence(url=base_url, username=username, password=password, verify_ssl=verify_ssl, timeout=timeout)
        get_logger().warning("Confluence sync skipped: missing credentials (token or username/password)")
        return None
    except Exception as e:
        get_logger().warning(f"Failed to initialize Confluence client: {e}")
        return None


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_case_id(text: str) -> str:
    patterns = _sync_settings().get("case_id_patterns", [r"\b(?:TC|CASE|TEST)[-_]?\d+\b", r"\b\d{3,}\b"])
    if isinstance(patterns, str):
        patterns = [patterns]
    for pattern in patterns:
        try:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(0).strip().upper()
        except re.error:
            continue
    return ""


def _extract_case_name(text: str, title: str) -> str:
    for line in text.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if re.match(r"(?i)^case\s*name\s*[:：]\s*(.+)$", normalized):
            return re.sub(r"(?i)^case\s*name\s*[:：]\s*", "", normalized).strip()
    return title.strip()


def _extract_steps(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    steps: list[str] = []

    in_steps = False
    for line in lines:
        if not line:
            if in_steps and steps:
                break
            continue
        if re.match(r"(?i)^steps?\s*[:：]?$", line):
            in_steps = True
            continue
        if not in_steps:
            continue

        numbered = re.match(r"^(?:\d+[\.\)]|[-*])\s*(.+)$", line)
        if numbered:
            content = numbered.group(1).strip()
            if content:
                steps.append(content)
            continue
        if steps and re.match(r"^[A-Z][A-Za-z0-9 _-]{0,40}$", line):
            # likely new section title
            break
        if steps:
            steps[-1] = f"{steps[-1]} {line}".strip()

    if steps:
        return steps

    # Fallback: collect all numbered lines from full text.
    for line in lines:
        numbered = re.match(r"^(?:\d+[\.\)]|[-*])\s*(.+)$", line)
        if numbered:
            content = numbered.group(1).strip()
            if content:
                steps.append(content)
    return steps


def _extract_case_name_safe(text: str, title: str) -> str:
    for line in text.splitlines():
        normalized = line.strip()
        if not normalized:
            continue
        if re.match(r"(?i)^case\s*name\s*[:：]\s*(.+)$", normalized):
            return re.sub(r"(?i)^case\s*name\s*[:：]\s*", "", normalized).strip()
    return title.strip()


def _extract_steps_safe(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines()]
    steps: list[str] = []

    in_steps = False
    for line in lines:
        if not line:
            if in_steps and steps:
                break
            continue
        if re.match(r"(?i)^steps?\s*[:：]?$", line):
            in_steps = True
            continue
        if not in_steps:
            continue

        numbered = re.match(r"^(?:\d+[\.\)]|[-*])\s*(.+)$", line)
        if numbered:
            content = numbered.group(1).strip()
            if content:
                steps.append(content)
            continue
        if steps and re.match(r"^[A-Z][A-Za-z0-9 _-]{0,40}$", line):
            break
        if steps:
            steps[-1] = f"{steps[-1]} {line}".strip()

    if steps:
        return steps

    for line in lines:
        numbered = re.match(r"^(?:\d+[\.\)]|[-*])\s*(.+)$", line)
        if numbered:
            content = numbered.group(1).strip()
            if content:
                steps.append(content)
    return steps


def _html_to_text(storage_html: str) -> str:
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_links = False
    converter.ignore_images = True
    converter.ignore_tables = False
    return converter.handle(storage_html or "")


def _normalize_case_record(page: dict, storage_html: str, base_url: str) -> dict | None:
    page_id = _safe_str(page.get("id"))
    title = _safe_str(page.get("title"))
    links = page.get("_links", {}) if isinstance(page.get("_links"), dict) else {}
    webui = _safe_str(links.get("webui"))
    source_url = urljoin(base_url.rstrip("/") + "/", webui.lstrip("/")) if webui else ""
    updated_at = _safe_str(page.get("lastModified")) or datetime.now(timezone.utc).isoformat()

    raw_text = _html_to_text(storage_html)
    case_id = _extract_case_id(f"{title}\n{raw_text}")
    if not case_id:
        return None
    case_name = _extract_case_name_safe(raw_text, title)
    steps = _extract_steps_safe(raw_text)
    if not steps:
        return None

    return {
        "page_id": page_id,
        "case_id": case_id,
        "case_name": case_name,
        "steps": steps,
        "updated_at": updated_at,
        "source_url": source_url,
        "title": title,
    }


def _compose_cql(last_sync: str | None = None) -> str:
    settings = _sync_settings()
    page_cql = _safe_str(settings.get("page_cql", "")).strip()
    spaces = settings.get("space_keys", [])
    if isinstance(spaces, str):
        spaces = [spaces]
    spaces = [space for space in spaces if space]

    clauses: list[str] = []
    if page_cql:
        clauses.append(f"({page_cql})")
    if spaces:
        if len(spaces) == 1:
            clauses.append(f'space="{spaces[0]}"')
        else:
            space_filters = " OR ".join(f'space="{space}"' for space in spaces)
            clauses.append(f"({space_filters})")
    clauses.append('type="page"')

    incremental = bool(settings.get("incremental_since_last_sync", True))
    if incremental and last_sync:
        # Confluence CQL accepts date-like values; keep it broadly compatible.
        ts = last_sync[:16].replace("T", " ")
        clauses.append(f'lastmodified >= "{ts}"')

    return " AND ".join(clauses)


def sync_confluence_testcases(force_full: bool = False) -> ConfluenceSyncResult:
    if not bool(_sync_settings().get("enabled", False)):
        return ConfluenceSyncResult(
            success=True,
            synced_cases=0,
            synced_pages=0,
            cache_file=str(_index_file()),
            message="Confluence sync disabled by configuration.",
        )

    client = _confluence_client()
    if not client:
        return ConfluenceSyncResult(
            success=False,
            synced_cases=0,
            synced_pages=0,
            cache_file=str(_index_file()),
            message="Confluence client unavailable.",
        )

    state = _read_json(_state_file())
    last_sync = None if force_full else _safe_str(state.get("last_sync", ""))
    cql = _compose_cql(last_sync=last_sync if last_sync else None)
    base_url = _safe_str(_sync_settings().get("base_url", "")) or _safe_str(_secrets_section("confluence").get("base_url", ""))
    page_limit = max(1, int(_sync_settings().get("page_limit", _DEFAULT_PAGE_LIMIT)))

    existing_index = _read_json(_index_file())
    existing_cases = existing_index.get("cases", [])
    merged_by_page: dict[str, dict] = {}
    for case in existing_cases:
        page_id = _safe_str(case.get("page_id"))
        if page_id:
            merged_by_page[page_id] = case

    fetched_pages = 0
    start = 0
    max_pages = _MAX_PAGES_PER_SYNC
    while fetched_pages < max_pages:
        try:
            response = client.cql(cql=cql, start=start, limit=page_limit, expand="version")
        except Exception as e:
            return ConfluenceSyncResult(
                success=False,
                synced_cases=len(merged_by_page),
                synced_pages=fetched_pages,
                cache_file=str(_index_file()),
                message=f"Confluence CQL request failed: {e}",
            )
        results = response.get("results", []) if isinstance(response, dict) else []
        if not results:
            break

        for page in results:
            page_id = _safe_str(page.get("id"))
            if not page_id:
                continue
            fetched_pages += 1
            try:
                page_full = client.get_page_by_id(page_id=page_id, expand="body.storage,version,_links")
            except Exception as e:
                get_logger().warning(f"Failed to fetch Confluence page {page_id}: {e}")
                continue

            storage_html = (
                (((page_full or {}).get("body") or {}).get("storage") or {}).get("value", "")
                if isinstance(page_full, dict)
                else ""
            )
            normalized = _normalize_case_record(page_full or page, storage_html, base_url)
            if not normalized:
                continue
            merged_by_page[page_id] = normalized

        if len(results) < page_limit:
            break
        start += page_limit

    cases = sorted(merged_by_page.values(), key=lambda item: (_safe_str(item.get("case_id")), _safe_str(item.get("page_id"))))
    now_iso = datetime.now(timezone.utc).isoformat()
    index_payload = {
        "updated_at": now_iso,
        "source": "confluence",
        "cql": cql,
        "cases": cases,
    }
    _write_json(_index_file(), index_payload)
    _write_json(_state_file(), {"last_sync": now_iso})
    return ConfluenceSyncResult(
        success=True,
        synced_cases=len(cases),
        synced_pages=fetched_pages,
        cache_file=str(_index_file()),
        message="Confluence testcase sync completed.",
    )
