from __future__ import annotations

import hashlib
import math
import os
import pickle
import re
import shutil
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from pr_agent.config_loader import get_settings
from pr_agent.git_providers.git_provider import GitProvider
from pr_agent.log import get_logger

_RAG_INDEX_VERSION = 2
_DEFAULT_CODE_CHUNK_LINES = 80
_DEFAULT_DOC_CHUNK_LINES = 60
_DEFAULT_CHUNK_OVERLAP_LINES = 12
_DEFAULT_MAX_FILE_CHARS = 120_000

_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "target",
    "out",
    "coverage",
    ".idea",
    ".vscode",
}

_DOC_NAME_HINTS = (
    "prd",
    "spec",
    "design",
    "architecture",
    "adr",
    "requirements",
    "proposal",
    "blueprint",
    "rfc",
    "epic",
)

_DOC_EXTENSIONS = {".md", ".mdx", ".rst", ".txt", ".adoc", ".org", ".wiki"}
_CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".go",
    ".java",
    ".kt",
    ".kts",
    ".rs",
    ".rb",
    ".php",
    ".cs",
    ".c",
    ".cc",
    ".cpp",
    ".h",
    ".hpp",
    ".swift",
    ".scala",
    ".sql",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".bash",
    ".ps1",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".less",
    ".mjs",
    ".cjs",
}

_QUERY_DOC_HINTS = {"prd", "spec", "design", "architecture", "adr", "requirement", "requirements"}


def _signature_bucket(signature: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]", "_", (signature or "").strip())
    return normalized[:64] if normalized else "default"


def _clean_markdown_content(text: str) -> str:
    # Keep content stable for lexical retrieval while dropping noisy markdown wrappers.
    cleaned = re.sub(r"```[^\n]*", "", text)
    cleaned = cleaned.replace("```", "")
    cleaned = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"\[[^\]]+\]\([^)]+\)", " ", cleaned)
    cleaned = re.sub(r"^#{1,6}\s*", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


@dataclass(slots=True)
class RepositoryContextItem:
    source_type: str
    path: str
    title: str
    start_line: int
    end_line: int
    score: float
    content: str


@dataclass(slots=True)
class RepositoryContextBundle:
    items: list[RepositoryContextItem]
    prompt_items: list[dict]
    markdown: str


@dataclass(slots=True)
class _Chunk:
    chunk_id: str
    source_type: str
    path: str
    title: str
    start_line: int
    end_line: int
    content: str
    term_freq: Counter[str]
    doc_len: int


def _settings_section(name: str) -> dict:
    section = get_settings().get(name, {})
    if isinstance(section, dict):
        return section
    try:
        return dict(section)
    except Exception:
        return {}


def _rag_config() -> dict:
    return _settings_section("pr_rag")


def _config_value(key: str, default):
    section = _rag_config()
    value = section.get(key, default)
    return value if value is not None else default


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    text = text.replace("/", " ").replace("\\", " ").replace("-", " ").replace(".", " ")
    rough_tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+", text.lower())
    tokens: list[str] = []
    for token in rough_tokens:
        parts = [part for part in re.split(r"[_\s]+", token) if part]
        if not parts:
            parts = [token]
        for part in parts:
            if len(part) > 1 or part.isdigit():
                tokens.append(part)
    return tokens


def _is_ignored_directory(path: Path) -> bool:
    return any(part in _IGNORE_DIRS for part in path.parts)


def _doc_paths() -> tuple[str, ...]:
    configured = _config_value("doc_paths", ["docs", "prd", "spec"])
    if isinstance(configured, str):
        configured = [configured]
    normalized = tuple(_normalize_path(path.lower()) for path in configured if path)
    return normalized or ("docs", "prd", "spec")


def _looks_like_doc(path: Path) -> bool:
    lower_name = path.name.lower()
    if path.suffix.lower() in _DOC_EXTENSIONS:
        return True
    if any(hint in lower_name for hint in _DOC_NAME_HINTS):
        return True
    normalized = _normalize_path(str(path).lower())
    return any(part in normalized for part in _doc_paths())


def _is_text_candidate(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in _DOC_EXTENSIONS or suffix in _CODE_EXTENSIONS:
        return True
    return suffix == "" and _looks_like_doc(path)


def _read_text_file(path: Path, max_chars: int) -> str | None:
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None
    except Exception:
        return None

    if "\x00" in content:
        return None
    content = content.strip()
    if not content:
        return None
    if len(content) > max_chars:
        content = content[:max_chars]
    return content


def _chunk_lines(text: str, max_lines: int, overlap_lines: int) -> list[tuple[int, int, str]]:
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[tuple[int, int, str]] = []
    if len(lines) <= max_lines:
        return [(1, len(lines), text.strip())]

    start = 0
    while start < len(lines):
        end = min(len(lines), start + max_lines)
        chunk_text = "\n".join(lines[start:end]).strip()
        if chunk_text:
            chunks.append((start + 1, end, chunk_text))
        if end >= len(lines):
            break
        start = max(0, end - overlap_lines)
    return chunks


def _extract_title(path: Path, text: str, source_type: str) -> str:
    if source_type == "doc":
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
            if stripped:
                return stripped[:90]
        return path.name

    patterns = (
        r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_][A-Za-z0-9_]*)",
        r"^\s*(?:export\s+)?class\s+([A-Za-z_][A-Za-z0-9_]*)",
    )
    for line in text.splitlines()[:50]:
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                return f"{path.name}: {match.group(1)}"
    return path.name


def _build_query_text(title: str | None, description: str | None, diff_files: Sequence) -> tuple[str, list[str]]:
    parts: list[str] = []
    focus_paths: list[str] = []
    if title:
        parts.append(title)
    if description:
        parts.append(description)

    for file_info in diff_files or []:
        filename = getattr(file_info, "filename", "") or ""
        old_filename = getattr(file_info, "old_filename", "") or ""
        patch = getattr(file_info, "patch", "") or ""
        focus_paths.extend([p for p in [filename, old_filename] if p])
        if filename:
            parts.append(filename)
        if old_filename:
            parts.append(old_filename)
        if patch:
            parts.append(patch[:2000])
    return "\n".join(part for part in parts if part), focus_paths


def _repo_cache_root() -> Path:
    cache_dir = _config_value("cache_dir", os.path.join(tempfile.gettempdir(), "pr-agent-rag"))
    cache_root = Path(cache_dir).expanduser().resolve()
    cache_root.mkdir(parents=True, exist_ok=True)
    return cache_root


def _repo_snapshot_dir(repo_key: str) -> Path:
    return _repo_cache_root() / repo_key / "snapshot"


def _repo_key_for_provider(git_provider: GitProvider, pr_url: str) -> str:
    repo_url = ""
    try:
        repo_url = git_provider.get_git_repo_url(pr_url)
    except Exception:
        repo_url = ""
    if not repo_url:
        repo_url = pr_url or git_provider.__class__.__name__
    return hashlib.sha256(repo_url.encode("utf-8")).hexdigest()[:16]


def _repo_signature_from_provider(git_provider: GitProvider) -> str:
    try:
        pr = getattr(git_provider, "pr", None)
        if pr is not None:
            head = getattr(pr, "head", None)
            if head is not None and getattr(head, "sha", None):
                return str(head.sha)
            commits = getattr(git_provider, "pr_commits", None)
            if commits:
                last_commit = commits[-1]
                sha = getattr(last_commit, "sha", None) or getattr(last_commit, "hexsha", None)
                if sha:
                    return str(sha)
    except Exception:
        pass

    try:
        repo = getattr(git_provider, "repo", None)
        if repo is not None and hasattr(repo, "head") and getattr(repo.head, "commit", None):
            return str(repo.head.commit.hexsha)
    except Exception:
        pass
    return ""


def _clone_repo_if_needed(git_provider: GitProvider, pr_url: str, repo_root: Path) -> Path | None:
    if repo_root.exists() and any(repo_root.iterdir()):
        return repo_root

    repo_url = ""
    try:
        repo_url = git_provider.get_git_repo_url(pr_url)
    except Exception:
        repo_url = ""
    if not repo_url:
        return None

    try:
        cloned = git_provider.clone(repo_url, str(repo_root), remove_dest_folder=False)
        if cloned and Path(cloned.path).exists():
            return Path(cloned.path)
    except Exception as e:
        get_logger().warning(f"Repository clone for RAG failed: {e}")
    return None


def _chunk_source_file(path: Path, text: str) -> list[tuple[int, int, str, str]]:
    source_type = "doc" if _looks_like_doc(path) else "code"
    if source_type == "doc":
        cleaned = _clean_markdown_content(text)
        max_lines = max(1, int(_config_value("doc_chunk_lines", _DEFAULT_DOC_CHUNK_LINES)))
    else:
        cleaned = text
        max_lines = max(1, int(_config_value("code_chunk_lines", _DEFAULT_CODE_CHUNK_LINES)))

    overlap_lines = max(0, int(_config_value("chunk_overlap_lines", _DEFAULT_CHUNK_OVERLAP_LINES)))
    overlap_lines = min(overlap_lines, max(0, max_lines - 1))
    chunks = _chunk_lines(cleaned, max_lines=max_lines, overlap_lines=overlap_lines)
    return [(start, end, chunk, source_type) for start, end, chunk in chunks]


def _build_index_for_repo(repo_root: Path) -> list[_Chunk]:
    max_chars = int(_config_value("max_file_chars", _DEFAULT_MAX_FILE_CHARS))
    chunks: list[_Chunk] = []
    doc_paths = _doc_paths()

    for path in sorted(repo_root.rglob("*")):
        if not path.is_file() or _is_ignored_directory(path):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg", ".pdf", ".zip", ".gz", ".7z", ".jar", ".exe"}:
            continue
        if not _is_text_candidate(path):
            continue

        normalized_relative = _normalize_path(str(path.relative_to(repo_root)))
        is_doc = _looks_like_doc(path)
        if is_doc and doc_paths:
            lower_path = normalized_relative.lower()
            if not any(marker in lower_path for marker in doc_paths) and not any(hint in path.name.lower() for hint in _DOC_NAME_HINTS):
                continue

        content = _read_text_file(path, max_chars=max_chars)
        if not content:
            continue

        for start_line, end_line, chunk_text, source_type in _chunk_source_file(path, content):
            if not chunk_text.strip():
                continue
            title = _extract_title(path, content, source_type)
            term_freq = Counter(_tokenize(f"{normalized_relative} {title} {chunk_text}"))
            if not term_freq:
                continue
            chunks.append(
                _Chunk(
                    chunk_id=f"{normalized_relative}:{start_line}-{end_line}",
                    source_type=source_type,
                    path=normalized_relative,
                    title=title,
                    start_line=start_line,
                    end_line=end_line,
                    content=chunk_text,
                    term_freq=term_freq,
                    doc_len=sum(term_freq.values()),
                )
            )
    return chunks


class _BM25Index:
    def __init__(self, chunks: list[_Chunk], k1: float = 1.2, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.doc_count = len(chunks)
        self.avg_doc_len = (sum(chunk.doc_len for chunk in chunks) / self.doc_count) if self.doc_count else 0.0
        self.df: dict[str, int] = defaultdict(int)
        for chunk in chunks:
            for term in chunk.term_freq.keys():
                self.df[term] += 1

    def idf(self, term: str) -> float:
        df = self.df.get(term, 0)
        if df == 0:
            return 0.0
        return math.log(1.0 + (self.doc_count - df + 0.5) / (df + 0.5))

    def score(self, chunk: _Chunk, query_terms: Sequence[str]) -> float:
        if not query_terms:
            return 0.0
        score = 0.0
        for term in query_terms:
            tf = chunk.term_freq.get(term, 0)
            if tf <= 0:
                continue
            idf = self.idf(term)
            denom = tf + self.k1 * (1 - self.b + self.b * (chunk.doc_len / max(self.avg_doc_len, 1.0)))
            score += idf * (tf * (self.k1 + 1.0)) / max(denom, 1e-9)
        return score


class RepositoryRAGIndex:
    def __init__(self, repo_key: str, repo_root: Path, signature: str, chunks: list[_Chunk], backend: str = "bm25"):
        self.repo_key = repo_key
        self.repo_root = repo_root
        self.signature = signature
        self.chunks = chunks
        self.backend = backend
        self._bm25 = _BM25Index(chunks)

    @property
    def index_path(self) -> Path:
        return _repo_cache_root() / self.repo_key / _signature_bucket(self.signature) / "index.pkl"

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": _RAG_INDEX_VERSION,
            "repo_key": self.repo_key,
            "repo_root": str(self.repo_root),
            "signature": self.signature,
            "backend": self.backend,
            "chunks": self.chunks,
        }
        with self.index_path.open("wb") as handle:
            pickle.dump(payload, handle, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, repo_key: str, signature: str = "") -> "RepositoryRAGIndex | None":
        cache_root = _repo_cache_root() / repo_key
        candidates: list[Path] = []
        if signature:
            candidates.append(cache_root / _signature_bucket(signature) / "index.pkl")
        # Backward-compatible fallback for older cache layout.
        candidates.append(cache_root / "index.pkl")
        # Try any available bucket as a final fallback.
        if cache_root.exists():
            for candidate in sorted(cache_root.glob("*/index.pkl")):
                if candidate not in candidates:
                    candidates.append(candidate)

        for index_path in candidates:
            if not index_path.exists():
                continue
            try:
                with index_path.open("rb") as handle:
                    payload = pickle.load(handle)
                if payload.get("version") != _RAG_INDEX_VERSION:
                    continue
                loaded = cls(
                    repo_key=payload["repo_key"],
                    repo_root=Path(payload["repo_root"]),
                    signature=payload.get("signature", ""),
                    chunks=payload.get("chunks", []),
                    backend=payload.get("backend", "bm25"),
                )
                if signature and loaded.signature and loaded.signature != signature:
                    continue
                return loaded
            except Exception as e:
                get_logger().warning(f"Failed to load repository RAG index: {e}")
        return None

    @classmethod
    def build(cls, git_provider: GitProvider, pr_url: str, force_refresh: bool = False) -> "RepositoryRAGIndex | None":
        repo_key = _repo_key_for_provider(git_provider, pr_url)
        cache_root = _repo_cache_root() / repo_key
        repo_signature = _repo_signature_from_provider(git_provider)
        backend = str(_config_value("backend", "bm25")).lower()
        if backend != "bm25":
            get_logger().warning(f"Unsupported RAG backend '{backend}', falling back to 'bm25'")
            backend = "bm25"

        if not force_refresh:
            cached = cls.load(repo_key, signature=repo_signature)
            if cached and cached.backend == backend and (not repo_signature or cached.signature == repo_signature) and cached.chunks:
                return cached

        repo_root = None
        if hasattr(git_provider, "repo_path") and getattr(git_provider, "repo_path", None):
            candidate = Path(getattr(git_provider, "repo_path"))
            if candidate.exists():
                repo_root = candidate
                try:
                    repo_signature = repo_signature or subprocess.check_output(
                        ["git", "rev-parse", "HEAD"],
                        cwd=str(candidate),
                        text=True,
                        stderr=subprocess.DEVNULL,
                    ).strip()
                except Exception:
                    pass

        if repo_root is None:
            repo_root = _repo_snapshot_dir(repo_key)
            if force_refresh:
                shutil.rmtree(repo_root, ignore_errors=True)
            elif repo_signature and cache_root.exists():
                cached = cls.load(repo_key, signature=repo_signature)
                if not cached:
                    shutil.rmtree(repo_root, ignore_errors=True)
            repo_root = _clone_repo_if_needed(git_provider, pr_url, repo_root)

        if repo_root is None or not repo_root.exists():
            get_logger().warning("Unable to resolve a repository root for RAG indexing")
            return None

        chunks = _build_index_for_repo(repo_root)
        if not chunks:
            get_logger().warning(f"No usable repository chunks were found for RAG indexing: {repo_root}")
            return None

        index = cls(repo_key=repo_key, repo_root=repo_root, signature=repo_signature, chunks=chunks, backend=backend)
        index.save()
        return index

    def search(self, query: str, focus_paths: Iterable[str] | None = None, max_context_chars: int = 12_000) -> list[RepositoryContextItem]:
        if not query.strip() or not self.chunks:
            return []
        max_context_chars = max(1, int(max_context_chars))

        focus_paths = {_normalize_path(path) for path in (focus_paths or []) if path}
        query_terms = _tokenize(query)
        if not query_terms:
            return []

        top_k_code = max(0, int(_config_value("top_k_code", 4)))
        top_k_docs = max(0, int(_config_value("top_k_docs", 3)))
        total_cap = max(1, int(_config_value("max_retrieved_chunks", top_k_code + top_k_docs)))
        query_lower = query.lower()
        likely_doc_query = any(term in query_lower for term in _QUERY_DOC_HINTS)

        scored: list[tuple[float, _Chunk]] = []
        for chunk in self.chunks:
            score = self._bm25.score(chunk, query_terms)
            if score <= 0:
                continue

            chunk_path = chunk.path
            chunk_dir = "/".join(chunk_path.split("/")[:-1])
            chunk_basename = chunk_path.split("/")[-1]
            if focus_paths:
                for focus_path in focus_paths:
                    focus_dir = "/".join(focus_path.split("/")[:-1])
                    if focus_path == chunk_path:
                        score += 0.18
                    elif focus_path in chunk_path or chunk_path in focus_path:
                        score += 0.12
                    elif focus_dir and focus_dir == chunk_dir:
                        score += 0.08
                    elif focus_path.split("/")[-1] == chunk_basename:
                        score += 0.06

            lower_path = chunk.path.lower()
            if chunk.source_type == "doc" and any(marker in lower_path for marker in _doc_paths()):
                score += 0.03
            if likely_doc_query and chunk.source_type == "doc":
                score += 0.04
            elif not likely_doc_query and chunk.source_type == "code":
                score += 0.02
            scored.append((score, chunk))

        if not scored:
            return []
        scored.sort(key=lambda item: item[0], reverse=True)

        code_candidates = [(s, c) for s, c in scored if c.source_type == "code"]
        doc_candidates = [(s, c) for s, c in scored if c.source_type == "doc"]

        selected_ordered: list[tuple[float, _Chunk]] = []
        selected_ids: set[str] = set()

        def take(candidates: list[tuple[float, _Chunk]], limit: int) -> None:
            for score, chunk in candidates:
                if len(selected_ordered) >= total_cap or len([1 for _, existing in selected_ordered if existing.source_type == chunk.source_type]) >= limit:
                    continue
                if chunk.chunk_id in selected_ids:
                    continue
                selected_ids.add(chunk.chunk_id)
                selected_ordered.append((score, chunk))
                if len(selected_ordered) >= total_cap:
                    break

        take(code_candidates, top_k_code)
        take(doc_candidates, top_k_docs)

        if len(selected_ordered) < total_cap:
            for score, chunk in scored:
                if len(selected_ordered) >= total_cap:
                    break
                if chunk.chunk_id in selected_ids:
                    continue
                selected_ids.add(chunk.chunk_id)
                selected_ordered.append((score, chunk))

        selected: list[RepositoryContextItem] = []
        total_chars = 0
        for score, chunk in sorted(selected_ordered, key=lambda item: item[0], reverse=True):
            content = chunk.content.strip()
            if not content:
                continue
            if len(content) > max_context_chars:
                content = content[:max_context_chars]
            new_total = total_chars + len(content)
            if selected and new_total > max_context_chars:
                break
            total_chars = new_total
            selected.append(
                RepositoryContextItem(
                    source_type=chunk.source_type,
                    path=chunk.path,
                    title=chunk.title,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    score=round(float(score), 4),
                    content=content,
                )
            )
        return selected


def _format_context_markdown(items: list[RepositoryContextItem]) -> str:
    if not items:
        return ""
    lines = [
        "\n\n___\n\n## Repository context",
        "Retrieved from repository code/doc chunks to improve review coverage for PRD/spec and cross-file behavior.",
    ]
    for item in items:
        lines.append(f"- `{item.path}` ({item.source_type}, lines {item.start_line}-{item.end_line}, score={item.score:.2f})")
    return "\n".join(lines) + "\n"


def _to_prompt_items(items: list[RepositoryContextItem]) -> list[dict]:
    return [
        {
            "source_type": item.source_type,
            "path": item.path,
            "title": item.title,
            "start_line": item.start_line,
            "end_line": item.end_line,
            "score": item.score,
            "content": item.content,
        }
        for item in items
    ]


def get_repository_context_bundle(
    git_provider: GitProvider,
    pr_url: str,
    diff_files: Sequence,
    title: str | None = None,
    description: str | None = None,
) -> RepositoryContextBundle:
    if not _config_value("enabled", False):
        return RepositoryContextBundle(items=[], prompt_items=[], markdown="")
    try:
        index = RepositoryRAGIndex.build(git_provider, pr_url, force_refresh=bool(_config_value("force_refresh", False)))
    except Exception as e:
        get_logger().warning(f"Failed to build repository RAG index: {e}")
        return RepositoryContextBundle(items=[], prompt_items=[], markdown="")
    if not index:
        return RepositoryContextBundle(items=[], prompt_items=[], markdown="")

    query_text, focus_paths = _build_query_text(title, description, diff_files)
    if not query_text.strip():
        return RepositoryContextBundle(items=[], prompt_items=[], markdown="")

    max_context_chars = int(_config_value("max_context_chars", 12_000))
    items = index.search(query=query_text, focus_paths=focus_paths, max_context_chars=max_context_chars)
    if not items:
        return RepositoryContextBundle(items=[], prompt_items=[], markdown="")

    return RepositoryContextBundle(items=items, prompt_items=_to_prompt_items(items), markdown=_format_context_markdown(items))
