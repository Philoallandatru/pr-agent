from __future__ import annotations

import json
from types import SimpleNamespace

from pr_agent.algo.testcase_alignment import build_testcase_alignment_bundle
from pr_agent.config_loader import get_settings


def test_testcase_alignment_bundle_matches_case_and_scores_steps(tmp_path):
    cache_dir = tmp_path / "confluence-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    index_path = cache_dir / "testcases_index.json"
    index_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "page_id": "1",
                        "case_id": "TC-1001",
                        "case_name": "3DMark prefill warm-up",
                        "steps": [
                            "Open 3DMark prefill page",
                            "Click start prefill button",
                            "Verify score appears in report panel",
                        ],
                        "source_url": "https://confluence.local/pages/1",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    original_alignment_enabled = get_settings().get("testcase_alignment.enabled", False)
    original_patterns = get_settings().get("testcase_alignment.case_id_patterns", [])
    original_max_steps = get_settings().get("testcase_alignment.max_steps_per_case", 20)
    original_conf = get_settings().get("testcase_alignment.min_alignment_confidence", 0.55)
    original_sync_cache = get_settings().get("confluence_sync.cache_dir", "")
    try:
        get_settings().set("testcase_alignment.enabled", True)
        get_settings().set("testcase_alignment.case_id_patterns", [r"\bTC-\d+\b"])
        get_settings().set("testcase_alignment.max_steps_per_case", 10)
        get_settings().set("testcase_alignment.min_alignment_confidence", 0.4)
        get_settings().set("confluence_sync.cache_dir", str(cache_dir))

        diff_files = [
            SimpleNamespace(
                filename="TestCase/Windows/Performance/test_3dmark_prefill.py",
                old_filename=None,
                patch=(
                    "@@ -0,0 +1,5 @@\n"
                    "+def test_prefill_run():\n"
                    "+    open_prefill_page()\n"
                    "+    click_start_prefill_button()\n"
                    "+    assert report_panel.score_text\n"
                ),
            )
        ]
        repo_context = [
            {
                "source_type": "code",
                "path": "src/perf/prefill_runner.py",
                "start_line": 10,
                "end_line": 30,
                "content": "render report panel and score output after benchmark run",
            }
        ]

        bundle = build_testcase_alignment_bundle(
            title="Implement TC-1001 prefill flow",
            description="This PR covers TC-1001",
            branch="feature/tc-1001-prefill",
            diff_files=diff_files,
            repo_context_prompt_items=repo_context,
        )
        assert bundle.prompt_items
        assert bundle.results
        first = bundle.results[0]
        assert first["case_id"] == "TC-1001"
        assert first["alignment_score"] > 0
        assert isinstance(first["covered_steps"], list)
        assert isinstance(first["missing_steps"], list)
        assert isinstance(first["uncertain_steps"], list)
    finally:
        get_settings().set("testcase_alignment.enabled", original_alignment_enabled)
        get_settings().set("testcase_alignment.case_id_patterns", original_patterns)
        get_settings().set("testcase_alignment.max_steps_per_case", original_max_steps)
        get_settings().set("testcase_alignment.min_alignment_confidence", original_conf)
        get_settings().set("confluence_sync.cache_dir", original_sync_cache)


def test_testcase_alignment_bundle_handles_missing_index(tmp_path):
    original_alignment_enabled = get_settings().get("testcase_alignment.enabled", False)
    original_sync_cache = get_settings().get("confluence_sync.cache_dir", "")
    try:
        get_settings().set("testcase_alignment.enabled", True)
        get_settings().set("confluence_sync.cache_dir", str(tmp_path / "missing-cache"))
        bundle = build_testcase_alignment_bundle(
            title="TC-2002 update",
            description="Cover TC-2002",
            branch="feature/tc-2002",
            diff_files=[],
            repo_context_prompt_items=[],
        )
        assert bundle.prompt_items == []
        assert bundle.results == []
        assert bundle.matched_case_ids == ["TC-2002"]
    finally:
        get_settings().set("testcase_alignment.enabled", original_alignment_enabled)
        get_settings().set("confluence_sync.cache_dir", original_sync_cache)
