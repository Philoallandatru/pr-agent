"""
Automated workflow module.

Provides orchestration for complex multi-stage workflows.
"""

from pr_agent.workflow.review_pipeline import (
    ReviewPipeline,
    ReviewConfig,
    ReviewResult,
    ReviewStage,
    ReviewSeverity,
    ReviewIssue,
    StageResult,
    format_review_report,
)

__all__ = [
    "ReviewPipeline",
    "ReviewConfig",
    "ReviewResult",
    "ReviewStage",
    "ReviewSeverity",
    "ReviewIssue",
    "StageResult",
    "format_review_report",
]
