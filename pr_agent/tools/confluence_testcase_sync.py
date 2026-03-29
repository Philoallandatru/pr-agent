from __future__ import annotations

from pr_agent.algo.confluence_sync import sync_confluence_testcases
from pr_agent.log import get_logger


class ConfluenceTestcaseSync:
    """
    Sync testcase data from Confluence into local cache for offline review-time alignment.
    """

    def __init__(self, pr_url: str, args=None, ai_handler=None):  # noqa: ARG002
        self.pr_url = pr_url
        self.args = args or []

    async def run(self):
        force_full = False
        if self.args:
            force_full = any(str(arg).strip().lower() in {"--full", "full", "--force-full"} for arg in self.args)
        result = sync_confluence_testcases(force_full=force_full)
        level = "info" if result.success else "warning"
        logger = getattr(get_logger(), level)
        logger(
            "Confluence testcase sync finished",
            artifact={
                "success": result.success,
                "synced_cases": result.synced_cases,
                "synced_pages": result.synced_pages,
                "cache_file": result.cache_file,
                "message": result.message,
            },
        )
        return result.message
