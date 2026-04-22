"""
Automated code review workflow pipeline.

This module orchestrates the complete code review process by integrating
all available analysis tools and generating comprehensive review reports.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ReviewStage(str, Enum):
    """Review pipeline stages."""
    INITIALIZATION = "initialization"
    QUALITY_GATE = "quality_gate"
    FORMATTING = "formatting"
    METRICS = "metrics"
    AI_REVIEW = "ai_review"
    SECURITY = "security"
    DOCUMENTATION = "documentation"
    FINALIZATION = "finalization"


class ReviewSeverity(str, Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ReviewIssue:
    """A single review issue."""
    severity: ReviewSeverity
    category: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suggestion: Optional[str] = None
    auto_fixable: bool = False


@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    stage: ReviewStage
    success: bool
    duration_seconds: float
    issues: List[ReviewIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ReviewConfig:
    """Configuration for review pipeline."""
    # Stages to run
    enabled_stages: Set[ReviewStage] = field(default_factory=lambda: set(ReviewStage))

    # Quality gate settings
    max_complexity: int = 10
    min_maintainability: float = 65.0
    max_file_lines: int = 1000

    # Formatting settings
    auto_format: bool = False
    format_languages: List[str] = field(default_factory=lambda: ["python", "javascript", "typescript"])

    # AI review settings
    enable_ai: bool = False
    ai_model: str = "gpt-4"

    # Security settings
    check_dependencies: bool = True
    check_secrets: bool = True

    # Documentation settings
    require_docstrings: bool = True
    min_doc_coverage: float = 80.0

    # General settings
    fail_on_critical: bool = True
    fail_on_high: bool = False
    parallel_execution: bool = True


@dataclass
class ReviewResult:
    """Complete review pipeline result."""
    success: bool
    start_time: datetime
    end_time: datetime
    total_duration_seconds: float
    stages: List[StageResult]
    issues: List[ReviewIssue]
    summary: Dict[str, Any]
    config: ReviewConfig


class ReviewPipeline:
    """Automated code review pipeline."""

    def __init__(self, config: Optional[ReviewConfig] = None):
        """Initialize pipeline with configuration."""
        self.config = config or ReviewConfig()
        self._stage_handlers = {
            ReviewStage.INITIALIZATION: self._run_initialization,
            ReviewStage.QUALITY_GATE: self._run_quality_gate,
            ReviewStage.FORMATTING: self._run_formatting,
            ReviewStage.METRICS: self._run_metrics,
            ReviewStage.AI_REVIEW: self._run_ai_review,
            ReviewStage.SECURITY: self._run_security,
            ReviewStage.DOCUMENTATION: self._run_documentation,
            ReviewStage.FINALIZATION: self._run_finalization,
        }

    async def review_files(self, file_paths: List[str]) -> ReviewResult:
        """
        Run complete review pipeline on specified files.

        Args:
            file_paths: List of file paths to review

        Returns:
            ReviewResult with all findings
        """
        start_time = datetime.now(timezone.utc)
        stages: List[StageResult] = []
        all_issues: List[ReviewIssue] = []

        logger.info(f"Starting review pipeline for {len(file_paths)} files")

        # Run stages
        for stage in self.config.enabled_stages:
            if stage not in self._stage_handlers:
                logger.warning(f"No handler for stage {stage}, skipping")
                continue

            stage_start = datetime.now(timezone.utc)
            try:
                result = await self._stage_handlers[stage](file_paths)
                result.duration_seconds = (datetime.now(timezone.utc) - stage_start).total_seconds()
                stages.append(result)
                all_issues.extend(result.issues)

                logger.info(f"Stage {stage} completed: {len(result.issues)} issues found")

                # Check if we should stop
                if not result.success and self._should_stop(result):
                    logger.error(f"Pipeline stopped at stage {stage}")
                    break

            except Exception as e:
                logger.exception(f"Error in stage {stage}")
                result = StageResult(
                    stage=stage,
                    success=False,
                    duration_seconds=(datetime.now(timezone.utc) - stage_start).total_seconds(),
                    error=str(e)
                )
                stages.append(result)
                break

        end_time = datetime.now(timezone.utc)
        total_duration = (end_time - start_time).total_seconds()

        # Generate summary
        summary = self._generate_summary(stages, all_issues)

        # Determine overall success
        success = self._determine_success(all_issues)

        return ReviewResult(
            success=success,
            start_time=start_time,
            end_time=end_time,
            total_duration_seconds=total_duration,
            stages=stages,
            issues=all_issues,
            summary=summary,
            config=self.config
        )

    async def review_directory(self, directory: str, patterns: Optional[List[str]] = None) -> ReviewResult:
        """
        Review all files in a directory.

        Args:
            directory: Directory path to review
            patterns: File patterns to include (e.g., ["*.py", "*.js"])

        Returns:
            ReviewResult with all findings
        """
        dir_path = Path(directory)
        if not dir_path.exists():
            raise ValueError(f"Directory not found: {directory}")

        # Collect files
        file_paths = []
        patterns = patterns or ["*.py", "*.js", "*.ts", "*.java", "*.go"]

        for pattern in patterns:
            file_paths.extend([str(p) for p in dir_path.rglob(pattern)])

        logger.info(f"Found {len(file_paths)} files to review in {directory}")

        return await self.review_files(file_paths)

    def _should_stop(self, result: StageResult) -> bool:
        """Check if pipeline should stop based on stage result."""
        if not result.success:
            # Stop on critical errors
            critical_issues = [i for i in result.issues if i.severity == ReviewSeverity.CRITICAL]
            if critical_issues and self.config.fail_on_critical:
                return True

            # Stop on high severity issues if configured
            high_issues = [i for i in result.issues if i.severity == ReviewSeverity.HIGH]
            if high_issues and self.config.fail_on_high:
                return True

        return False

    def _determine_success(self, issues: List[ReviewIssue]) -> bool:
        """Determine overall success based on issues."""
        critical_count = sum(1 for i in issues if i.severity == ReviewSeverity.CRITICAL)
        high_count = sum(1 for i in issues if i.severity == ReviewSeverity.HIGH)

        if critical_count > 0 and self.config.fail_on_critical:
            return False

        if high_count > 0 and self.config.fail_on_high:
            return False

        return True

    def _generate_summary(self, stages: List[StageResult], issues: List[ReviewIssue]) -> Dict[str, Any]:
        """Generate summary statistics."""
        severity_counts = {
            ReviewSeverity.CRITICAL: 0,
            ReviewSeverity.HIGH: 0,
            ReviewSeverity.MEDIUM: 0,
            ReviewSeverity.LOW: 0,
            ReviewSeverity.INFO: 0,
        }

        for issue in issues:
            severity_counts[issue.severity] += 1

        category_counts = {}
        for issue in issues:
            category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

        auto_fixable_count = sum(1 for i in issues if i.auto_fixable)

        return {
            "total_issues": len(issues),
            "severity_counts": {k.value: v for k, v in severity_counts.items()},
            "category_counts": category_counts,
            "auto_fixable_count": auto_fixable_count,
            "stages_completed": len([s for s in stages if s.success]),
            "stages_failed": len([s for s in stages if not s.success]),
        }

    # Stage handlers

    async def _run_initialization(self, file_paths: List[str]) -> StageResult:
        """Initialize review pipeline."""
        issues = []

        # Check files exist
        for file_path in file_paths:
            if not Path(file_path).exists():
                issues.append(ReviewIssue(
                    severity=ReviewSeverity.CRITICAL,
                    category="initialization",
                    message=f"File not found: {file_path}",
                    file_path=file_path
                ))

        return StageResult(
            stage=ReviewStage.INITIALIZATION,
            success=len(issues) == 0,
            duration_seconds=0.0,
            issues=issues,
            metadata={"files_checked": len(file_paths)}
        )

    async def _run_quality_gate(self, file_paths: List[str]) -> StageResult:
        """Run quality gate checks."""
        issues = []

        try:
            from pr_agent.quality.gate import QualityGate, QualityConfig

            gate_config = QualityConfig(
                max_complexity=self.config.max_complexity,
                min_maintainability=self.config.min_maintainability,
                max_file_lines=self.config.max_file_lines
            )

            gate = QualityGate(gate_config)

            for file_path in file_paths:
                if not file_path.endswith('.py'):
                    continue

                result = gate.check_file(file_path)

                for violation in result.violations:
                    severity = ReviewSeverity.HIGH if violation.severity == "high" else ReviewSeverity.MEDIUM
                    issues.append(ReviewIssue(
                        severity=severity,
                        category="quality",
                        message=violation.message,
                        file_path=file_path,
                        line_number=violation.line_number
                    ))

        except Exception as e:
            logger.exception("Error in quality gate stage")
            return StageResult(
                stage=ReviewStage.QUALITY_GATE,
                success=False,
                duration_seconds=0.0,
                error=str(e)
            )

        return StageResult(
            stage=ReviewStage.QUALITY_GATE,
            success=True,
            duration_seconds=0.0,
            issues=issues
        )

    async def _run_formatting(self, file_paths: List[str]) -> StageResult:
        """Check code formatting."""
        issues = []

        try:
            from pr_agent.formatting.manager import FormatterManager, FormatLanguage

            formatter = FormatterManager()

            for file_path in file_paths:
                # Determine language
                ext = Path(file_path).suffix
                lang_map = {
                    '.py': FormatLanguage.PYTHON,
                    '.js': FormatLanguage.JAVASCRIPT,
                    '.ts': FormatLanguage.TYPESCRIPT,
                }

                if ext not in lang_map:
                    continue

                result = formatter.format_file(file_path)

                if not result.success:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.LOW,
                        category="formatting",
                        message=f"Formatting issues found: {result.error}",
                        file_path=file_path,
                        auto_fixable=True
                    ))
                elif result.changed:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.INFO,
                        category="formatting",
                        message="Code formatting can be improved",
                        file_path=file_path,
                        auto_fixable=True
                    ))

        except Exception as e:
            logger.exception("Error in formatting stage")
            return StageResult(
                stage=ReviewStage.FORMATTING,
                success=False,
                duration_seconds=0.0,
                error=str(e)
            )

        return StageResult(
            stage=ReviewStage.FORMATTING,
            success=True,
            duration_seconds=0.0,
            issues=issues
        )

    async def _run_metrics(self, file_paths: List[str]) -> StageResult:
        """Calculate code metrics."""
        issues = []

        try:
            from pr_agent.metrics.analyzer import MetricsAnalyzer

            analyzer = MetricsAnalyzer()

            for file_path in file_paths:
                if not file_path.endswith('.py'):
                    continue

                metrics = analyzer.analyze_file(file_path)

                # Check complexity
                if metrics.cyclomatic_complexity > self.config.max_complexity:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.HIGH,
                        category="complexity",
                        message=f"High cyclomatic complexity: {metrics.cyclomatic_complexity}",
                        file_path=file_path,
                        suggestion="Consider refactoring to reduce complexity"
                    ))

                # Check maintainability
                if metrics.maintainability_index < self.config.min_maintainability:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.MEDIUM,
                        category="maintainability",
                        message=f"Low maintainability index: {metrics.maintainability_index:.1f}",
                        file_path=file_path,
                        suggestion="Improve code structure and documentation"
                    ))

                # Check file size
                if metrics.total_lines > self.config.max_file_lines:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.MEDIUM,
                        category="size",
                        message=f"Large file: {metrics.total_lines} lines",
                        file_path=file_path,
                        suggestion="Consider splitting into smaller modules"
                    ))

        except Exception as e:
            logger.exception("Error in metrics stage")
            return StageResult(
                stage=ReviewStage.METRICS,
                success=False,
                duration_seconds=0.0,
                error=str(e)
            )

        return StageResult(
            stage=ReviewStage.METRICS,
            success=True,
            duration_seconds=0.0,
            issues=issues
        )

    async def _run_ai_review(self, file_paths: List[str]) -> StageResult:
        """Run AI-powered code review."""
        issues = []

        if not self.config.enable_ai:
            return StageResult(
                stage=ReviewStage.AI_REVIEW,
                success=True,
                duration_seconds=0.0,
                issues=issues,
                metadata={"skipped": True}
            )

        try:
            from pr_agent.ai_review.reviewer import AIReviewer

            reviewer = AIReviewer()

            for file_path in file_paths:
                if not file_path.endswith('.py'):
                    continue

                result = reviewer.review_file(file_path)

                for finding in result.findings:
                    severity_map = {
                        "critical": ReviewSeverity.CRITICAL,
                        "high": ReviewSeverity.HIGH,
                        "medium": ReviewSeverity.MEDIUM,
                        "low": ReviewSeverity.LOW,
                    }

                    issues.append(ReviewIssue(
                        severity=severity_map.get(finding.severity, ReviewSeverity.MEDIUM),
                        category=finding.category,
                        message=finding.message,
                        file_path=file_path,
                        line_number=finding.line_number,
                        suggestion=finding.suggestion
                    ))

        except Exception as e:
            logger.exception("Error in AI review stage")
            return StageResult(
                stage=ReviewStage.AI_REVIEW,
                success=False,
                duration_seconds=0.0,
                error=str(e)
            )

        return StageResult(
            stage=ReviewStage.AI_REVIEW,
            success=True,
            duration_seconds=0.0,
            issues=issues
        )

    async def _run_security(self, file_paths: List[str]) -> StageResult:
        """Run security checks."""
        issues = []

        # Basic security checks
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Check for common security issues
                if 'eval(' in content:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.CRITICAL,
                        category="security",
                        message="Use of eval() detected - potential code injection risk",
                        file_path=file_path,
                        suggestion="Avoid using eval(), use safer alternatives"
                    ))

                if 'exec(' in content:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.CRITICAL,
                        category="security",
                        message="Use of exec() detected - potential code injection risk",
                        file_path=file_path,
                        suggestion="Avoid using exec(), use safer alternatives"
                    ))

                # Check for hardcoded secrets (basic patterns)
                import re
                secret_patterns = [
                    (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password detected"),
                    (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key detected"),
                    (r'secret\s*=\s*["\'][^"\']+["\']', "Hardcoded secret detected"),
                ]

                for pattern, message in secret_patterns:
                    if re.search(pattern, content, re.IGNORECASE):
                        issues.append(ReviewIssue(
                            severity=ReviewSeverity.HIGH,
                            category="security",
                            message=message,
                            file_path=file_path,
                            suggestion="Use environment variables or secure vaults"
                        ))

            except Exception as e:
                logger.warning(f"Error checking security for {file_path}: {e}")

        return StageResult(
            stage=ReviewStage.SECURITY,
            success=True,
            duration_seconds=0.0,
            issues=issues
        )

    async def _run_documentation(self, file_paths: List[str]) -> StageResult:
        """Check documentation coverage."""
        issues = []

        if not self.config.require_docstrings:
            return StageResult(
                stage=ReviewStage.DOCUMENTATION,
                success=True,
                duration_seconds=0.0,
                issues=issues,
                metadata={"skipped": True}
            )

        try:
            from pr_agent.documentation.generator import PythonDocExtractor

            extractor = PythonDocExtractor()

            for file_path in file_paths:
                if not file_path.endswith('.py'):
                    continue

                module_doc = extractor.extract_module(file_path)

                # Check module docstring
                if not module_doc.docstring:
                    issues.append(ReviewIssue(
                        severity=ReviewSeverity.LOW,
                        category="documentation",
                        message="Missing module docstring",
                        file_path=file_path,
                        suggestion="Add a module-level docstring"
                    ))

                # Check class docstrings
                for class_doc in module_doc.classes:
                    if not class_doc.docstring:
                        issues.append(ReviewIssue(
                            severity=ReviewSeverity.LOW,
                            category="documentation",
                            message=f"Missing docstring for class {class_doc.name}",
                            file_path=file_path,
                            line_number=class_doc.line_number,
                            suggestion="Add a class docstring"
                        ))

                # Check function docstrings
                for func_doc in module_doc.functions:
                    if not func_doc.docstring and not func_doc.name.startswith('_'):
                        issues.append(ReviewIssue(
                            severity=ReviewSeverity.LOW,
                            category="documentation",
                            message=f"Missing docstring for function {func_doc.name}",
                            file_path=file_path,
                            line_number=func_doc.line_number,
                            suggestion="Add a function docstring"
                        ))

        except Exception as e:
            logger.exception("Error in documentation stage")
            return StageResult(
                stage=ReviewStage.DOCUMENTATION,
                success=False,
                duration_seconds=0.0,
                error=str(e)
            )

        return StageResult(
            stage=ReviewStage.DOCUMENTATION,
            success=True,
            duration_seconds=0.0,
            issues=issues
        )

    async def _run_finalization(self, file_paths: List[str]) -> StageResult:
        """Finalize review pipeline."""
        return StageResult(
            stage=ReviewStage.FINALIZATION,
            success=True,
            duration_seconds=0.0,
            issues=[],
            metadata={"files_reviewed": len(file_paths)}
        )


def format_review_report(result: ReviewResult, format: str = "text") -> str:
    """
    Format review result as a report.

    Args:
        result: Review result to format
        format: Output format ("text", "markdown", "json")

    Returns:
        Formatted report string
    """
    if format == "json":
        import json
        return json.dumps({
            "success": result.success,
            "duration": result.total_duration_seconds,
            "summary": result.summary,
            "issues": [
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                    "file": i.file_path,
                    "line": i.line_number,
                    "suggestion": i.suggestion,
                    "auto_fixable": i.auto_fixable,
                }
                for i in result.issues
            ]
        }, indent=2)

    elif format == "markdown":
        lines = [
            "# Code Review Report",
            "",
            f"**Status:** {'✅ Passed' if result.success else '❌ Failed'}",
            f"**Duration:** {result.total_duration_seconds:.2f}s",
            f"**Total Issues:** {result.summary['total_issues']}",
            "",
            "## Summary",
            "",
        ]

        # Severity breakdown
        lines.append("### Issues by Severity")
        for severity, count in result.summary['severity_counts'].items():
            if count > 0:
                lines.append(f"- **{severity.upper()}:** {count}")

        lines.append("")

        # Category breakdown
        if result.summary['category_counts']:
            lines.append("### Issues by Category")
            for category, count in result.summary['category_counts'].items():
                lines.append(f"- **{category}:** {count}")
            lines.append("")

        # Issues
        if result.issues:
            lines.append("## Issues")
            lines.append("")

            for issue in sorted(result.issues, key=lambda x: x.severity.value):
                lines.append(f"### {issue.severity.value.upper()}: {issue.message}")
                if issue.file_path:
                    location = issue.file_path
                    if issue.line_number:
                        location += f":{issue.line_number}"
                    lines.append(f"**Location:** `{location}`")
                lines.append(f"**Category:** {issue.category}")
                if issue.suggestion:
                    lines.append(f"**Suggestion:** {issue.suggestion}")
                if issue.auto_fixable:
                    lines.append("**Auto-fixable:** Yes")
                lines.append("")

        return "\n".join(lines)

    else:  # text format
        lines = [
            "=" * 80,
            "CODE REVIEW REPORT",
            "=" * 80,
            "",
            f"Status: {'PASSED' if result.success else 'FAILED'}",
            f"Duration: {result.total_duration_seconds:.2f}s",
            f"Total Issues: {result.summary['total_issues']}",
            "",
            "SUMMARY",
            "-" * 80,
        ]

        # Severity breakdown
        for severity, count in result.summary['severity_counts'].items():
            if count > 0:
                lines.append(f"  {severity.upper()}: {count}")

        lines.append("")

        # Issues
        if result.issues:
            lines.append("ISSUES")
            lines.append("-" * 80)

            for i, issue in enumerate(result.issues, 1):
                lines.append(f"\n{i}. [{issue.severity.value.upper()}] {issue.message}")
                if issue.file_path:
                    location = issue.file_path
                    if issue.line_number:
                        location += f":{issue.line_number}"
                    lines.append(f"   Location: {location}")
                lines.append(f"   Category: {issue.category}")
                if issue.suggestion:
                    lines.append(f"   Suggestion: {issue.suggestion}")
                if issue.auto_fixable:
                    lines.append("   Auto-fixable: Yes")

        lines.append("")
        lines.append("=" * 80)

        return "\n".join(lines)
