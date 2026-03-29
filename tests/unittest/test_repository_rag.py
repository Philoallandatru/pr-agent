from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from pr_agent.algo.repository_rag import RepositoryRAGIndex, get_repository_context_bundle
from pr_agent.config_loader import get_settings


class FakeGitProvider:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.pr = SimpleNamespace(title="Payments refactor")

    def get_git_repo_url(self, pr_url: str) -> str:
        return str(self.repo_path)


def _git(repo_path: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo_path), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _create_repo(tmp_path: Path) -> Path:
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    _git(repo_path, "init")
    _git(repo_path, "config", "user.email", "test@example.com")
    _git(repo_path, "config", "user.name", "Test User")

    (repo_path / "src").mkdir()
    (repo_path / "docs" / "prd").mkdir(parents=True)

    (repo_path / "src" / "payments.py").write_text(
        "\n".join(
            [
                "class PaymentService:",
                "    def charge(self, amount):",
                "        return amount * 100",
                "",
                "    def refund(self, amount):",
                "        return amount",
            ]
        ),
        encoding="utf-8",
    )
    (repo_path / "docs" / "prd" / "payments.md").write_text(
        "\n".join(
            [
                "# Payments PRD",
                "",
                "The refund flow must preserve ledger consistency.",
                "The charge path must record a transaction id.",
            ]
        ),
        encoding="utf-8",
    )
    (repo_path / "README.md").write_text("# Repo\n", encoding="utf-8")

    _git(repo_path, "add", ".")
    _git(repo_path, "commit", "-m", "initial commit")
    return repo_path


def test_repository_rag_indexes_code_and_docs(tmp_path):
    repo_path = _create_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    provider = FakeGitProvider(repo_path)

    original_cache_dir = get_settings().get("pr_rag.cache_dir", "")
    original_enabled = get_settings().get("pr_rag.enabled", False)
    original_max = get_settings().get("pr_rag.max_retrieved_chunks", 6)
    original_force = get_settings().get("pr_rag.force_refresh", False)
    original_backend = get_settings().get("pr_rag.backend", "bm25")
    original_top_k_code = get_settings().get("pr_rag.top_k_code", 4)
    original_top_k_docs = get_settings().get("pr_rag.top_k_docs", 3)
    try:
        get_settings().set("pr_rag.cache_dir", str(cache_dir))
        get_settings().set("pr_rag.enabled", True)
        get_settings().set("pr_rag.backend", "bm25")
        get_settings().set("pr_rag.max_retrieved_chunks", 4)
        get_settings().set("pr_rag.top_k_code", 2)
        get_settings().set("pr_rag.top_k_docs", 2)
        get_settings().set("pr_rag.force_refresh", True)

        index = RepositoryRAGIndex.build(provider, "local://repo", force_refresh=True)
        assert index is not None
        assert index.chunks

        doc_results = index.search("refund flow ledger consistency", focus_paths=["docs/prd/payments.md"])
        assert doc_results
        assert any(result.path.endswith("docs/prd/payments.md") for result in doc_results)

        code_results = index.search("transaction id charge", focus_paths=["src/payments.py"])
        assert code_results
        assert any(result.path.endswith("src/payments.py") for result in code_results)
    finally:
        get_settings().set("pr_rag.cache_dir", original_cache_dir)
        get_settings().set("pr_rag.enabled", original_enabled)
        get_settings().set("pr_rag.max_retrieved_chunks", original_max)
        get_settings().set("pr_rag.force_refresh", original_force)
        get_settings().set("pr_rag.backend", original_backend)
        get_settings().set("pr_rag.top_k_code", original_top_k_code)
        get_settings().set("pr_rag.top_k_docs", original_top_k_docs)


def test_repository_context_bundle_formats_markdown(tmp_path):
    repo_path = _create_repo(tmp_path)
    cache_dir = tmp_path / "cache"
    provider = FakeGitProvider(repo_path)
    diff_files = [SimpleNamespace(filename="src/payments.py", patch="+ def charge_refund():\n+    return True", old_filename=None)]

    original_cache_dir = get_settings().get("pr_rag.cache_dir", "")
    original_enabled = get_settings().get("pr_rag.enabled", False)
    original_backend = get_settings().get("pr_rag.backend", "bm25")
    try:
        get_settings().set("pr_rag.cache_dir", str(cache_dir))
        get_settings().set("pr_rag.enabled", True)
        get_settings().set("pr_rag.backend", "bm25")
        bundle = get_repository_context_bundle(
            provider,
            "local://repo",
            diff_files=diff_files,
            title="Payments refactor",
            description="Align charge and refund flow with PRD",
        )
        assert bundle.items
        assert bundle.prompt_items
        assert "Repository context" in bundle.markdown
        assert "src/payments.py" in bundle.markdown or "docs/prd/payments.md" in bundle.markdown
    finally:
        get_settings().set("pr_rag.cache_dir", original_cache_dir)
        get_settings().set("pr_rag.enabled", original_enabled)
        get_settings().set("pr_rag.backend", original_backend)
