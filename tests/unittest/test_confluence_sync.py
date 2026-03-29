from __future__ import annotations

import json

from pr_agent.algo import confluence_sync
from pr_agent.config_loader import get_settings


class _FakeConfluenceClient:
    def __init__(self):
        self._pages = [
            {
                "id": "100",
                "title": "TC-3001 3DMark prefill",
                "_links": {"webui": "/spaces/QA/pages/100"},
            }
        ]

    def cql(self, cql, start=0, limit=50, expand=None):  # noqa: ARG002
        if start > 0:
            return {"results": []}
        return {"results": self._pages}

    def get_page_by_id(self, page_id, expand=None):  # noqa: ARG002
        assert page_id == "100"
        return {
            "id": "100",
            "title": "TC-3001 3DMark prefill",
            "_links": {"webui": "/spaces/QA/pages/100"},
            "body": {
                "storage": {
                    "value": (
                        "<p>Case ID: TC-3001</p>"
                        "<p>Case Name: Prefill baseline</p>"
                        "<p>Steps:</p>"
                        "<ol><li>Open prefill page</li><li>Click start</li><li>Verify report score</li></ol>"
                    )
                }
            },
        }


def test_confluence_sync_writes_index(tmp_path, monkeypatch):
    cache_dir = tmp_path / "sync-cache"
    base_url = "https://confluence.local"

    original_enabled = get_settings().get("confluence_sync.enabled", False)
    original_cache = get_settings().get("confluence_sync.cache_dir", "")
    original_base = get_settings().get("confluence_sync.base_url", "")
    original_space = get_settings().get("confluence_sync.space_keys", [])
    original_cql = get_settings().get("confluence_sync.page_cql", "")
    try:
        get_settings().set("confluence_sync.enabled", True)
        get_settings().set("confluence_sync.cache_dir", str(cache_dir))
        get_settings().set("confluence_sync.base_url", base_url)
        get_settings().set("confluence_sync.space_keys", ["QA"])
        get_settings().set("confluence_sync.page_cql", 'title ~ "TC-"')
        monkeypatch.setattr(confluence_sync, "_confluence_client", lambda: _FakeConfluenceClient())

        result = confluence_sync.sync_confluence_testcases(force_full=True)
        assert result.success is True
        assert result.synced_cases == 1
        index_path = cache_dir / "testcases_index.json"
        assert index_path.exists()

        payload = json.loads(index_path.read_text(encoding="utf-8"))
        assert payload["cases"][0]["case_id"] == "TC-3001"
        assert payload["cases"][0]["case_name"] == "Prefill baseline"
        assert len(payload["cases"][0]["steps"]) == 3
    finally:
        get_settings().set("confluence_sync.enabled", original_enabled)
        get_settings().set("confluence_sync.cache_dir", original_cache)
        get_settings().set("confluence_sync.base_url", original_base)
        get_settings().set("confluence_sync.space_keys", original_space)
        get_settings().set("confluence_sync.page_cql", original_cql)
