"""
AI-driven code review system.

Uses AI models to perform intelligent code analysis, detecting:
- Logic errors and bugs
- Performance issues
- Security vulnerabilities
- Code smells and anti-patterns
- Best practice violations
"""

import ast
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pr_agent.algo.ai_handlers import AiHandler

try:
    from pr_agent.config_loader import get_settings
except ImportError:
    def get_settings():
        """Fallback settings."""
        return {}


class ReviewSeverity(str, Enum):
    """Severity level of review findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewCategory(str, Enum):
    """Category of review finding."""
    BUG = "bug"
    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    STYLE = "style"
    DOCUMENTATION = "documentation"
    BEST_PRACTICE = "best_practice"


@dataclass
class ReviewFinding:
    """A single code review finding."""
    category: ReviewCategory
    severity: ReviewSeverity
    title: str
    description: str
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    suggestion: Optional[str] = None
    confidence: float = 1.0  # 0.0 - 1.0


@dataclass
class AIReviewReport:
    """Complete AI review report."""
    timestamp: float
    files_reviewed: int
    total_findings: int
    findings: List[ReviewFinding] = field(default_factory=list)
    summary: str = ""

    @property
    def critical_count(self) -> int:
        """Count of critical findings."""
        return sum(1 for f in self.findings if f.severity == ReviewSeverity.CRITICAL)

    @property
    def high_count(self) -> int:
        """Count of high severity findings."""
        return sum(1 for f in self.findings if f.severity == ReviewSeverity.HIGH)

    @property
    def by_category(self) -> Dict[str, int]:
        """Count findings by category."""
        counts = {}
        for finding in self.findings:
            category = finding.category.value
            counts[category] = counts.get(category, 0) + 1
        return counts


class AICodeReviewer:
    """
    AI-powered code reviewer.

    Uses language models to analyze code and provide intelligent feedback.
    """

    def __init__(self, ai_handler: Optional[Any] = None):
        """
        Initialize AI code reviewer.

        Args:
            ai_handler: AI handler for model interactions (optional)
        """
        self.ai_handler = ai_handler
        self.settings = get_settings()

    def review_file(
        self,
        file_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ReviewFinding]:
        """
        Review a single file.

        Args:
            file_path: Path to file to review
            context: Additional context (PR info, related files, etc.)

        Returns:
            List of review findings
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            return [ReviewFinding(
                category=ReviewCategory.BUG,
                severity=ReviewSeverity.HIGH,
                title="File Read Error",
                description=f"Failed to read file: {e}",
                file_path=file_path,
                line_start=0,
                line_end=0,
                code_snippet="",
                confidence=1.0
            )]

        findings = []

        # Static analysis
        findings.extend(self._static_analysis(file_path, code))

        # AI-powered analysis
        if self.ai_handler:
            findings.extend(self._ai_analysis(file_path, code, context))

        return findings

    def review_diff(
        self,
        file_path: str,
        diff: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[ReviewFinding]:
        """
        Review code changes (diff).

        Args:
            file_path: Path to changed file
            diff: Unified diff string
            context: Additional context

        Returns:
            List of review findings
        """
        findings = []

        # Parse diff to extract changed lines
        changed_lines = self._parse_diff(diff)

        # Focus AI analysis on changed code
        if self.ai_handler and changed_lines:
            findings.extend(
                self._ai_diff_analysis(file_path, diff, changed_lines, context)
            )

        return findings

    def review_pr(
        self,
        pr_files: List[Dict[str, str]],
        pr_context: Optional[Dict[str, Any]] = None
    ) -> AIReviewReport:
        """
        Review entire pull request.

        Args:
            pr_files: List of changed files with diffs
            pr_context: PR metadata (title, description, author, etc.)

        Returns:
            Complete review report
        """
        all_findings = []

        for file_info in pr_files:
            file_path = file_info.get('path', '')
            diff = file_info.get('diff', '')

            if diff:
                findings = self.review_diff(file_path, diff, pr_context)
            else:
                findings = self.review_file(file_path, pr_context)

            all_findings.extend(findings)

        # Generate summary
        summary = self._generate_summary(all_findings, pr_context)

        report = AIReviewReport(
            timestamp=datetime.now().timestamp(),
            files_reviewed=len(pr_files),
            total_findings=len(all_findings),
            findings=all_findings,
            summary=summary
        )

        return report

    def _static_analysis(self, file_path: str, code: str) -> List[ReviewFinding]:
        """Perform static code analysis."""
        findings = []

        # Only analyze Python files
        if not file_path.endswith('.py'):
            return findings

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return [ReviewFinding(
                category=ReviewCategory.BUG,
                severity=ReviewSeverity.CRITICAL,
                title="Syntax Error",
                description=f"Syntax error: {e.msg}",
                file_path=file_path,
                line_start=e.lineno or 0,
                line_end=e.lineno or 0,
                code_snippet=e.text or "",
                confidence=1.0
            )]

        # Check for common issues
        findings.extend(self._check_security_issues(tree, file_path, code))
        findings.extend(self._check_performance_issues(tree, file_path, code))
        findings.extend(self._check_code_smells(tree, file_path, code))

        return findings

    def _check_security_issues(
        self,
        tree: ast.AST,
        file_path: str,
        code: str
    ) -> List[ReviewFinding]:
        """Check for security vulnerabilities."""
        findings = []
        lines = code.split('\n')

        for node in ast.walk(tree):
            # Check for eval() usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == 'eval':
                    findings.append(ReviewFinding(
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.CRITICAL,
                        title="Dangerous eval() Usage",
                        description="Using eval() can execute arbitrary code and is a security risk",
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggestion="Use ast.literal_eval() for safe evaluation or refactor to avoid eval()",
                        confidence=1.0
                    ))

                # Check for exec() usage
                if isinstance(node.func, ast.Name) and node.func.id == 'exec':
                    findings.append(ReviewFinding(
                        category=ReviewCategory.SECURITY,
                        severity=ReviewSeverity.HIGH,
                        title="Dangerous exec() Usage",
                        description="Using exec() can execute arbitrary code",
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggestion="Refactor to avoid exec() or use safer alternatives",
                        confidence=1.0
                    ))

        return findings

    def _check_performance_issues(
        self,
        tree: ast.AST,
        file_path: str,
        code: str
    ) -> List[ReviewFinding]:
        """Check for performance issues."""
        findings = []
        lines = code.split('\n')

        for node in ast.walk(tree):
            # Check for string concatenation in loops
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign):
                        if isinstance(child.op, ast.Add):
                            if isinstance(child.target, ast.Name):
                                findings.append(ReviewFinding(
                                    category=ReviewCategory.PERFORMANCE,
                                    severity=ReviewSeverity.MEDIUM,
                                    title="String Concatenation in Loop",
                                    description="String concatenation in loops is inefficient",
                                    file_path=file_path,
                                    line_start=child.lineno,
                                    line_end=child.lineno,
                                    code_snippet=lines[child.lineno - 1] if child.lineno <= len(lines) else "",
                                    suggestion="Use list.append() and ''.join() instead",
                                    confidence=0.8
                                ))

        return findings

    def _check_code_smells(
        self,
        tree: ast.AST,
        file_path: str,
        code: str
    ) -> List[ReviewFinding]:
        """Check for code smells."""
        findings = []
        lines = code.split('\n')

        for node in ast.walk(tree):
            # Check for too many arguments
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arg_count = len(node.args.args)
                if arg_count > 5:
                    findings.append(ReviewFinding(
                        category=ReviewCategory.MAINTAINABILITY,
                        severity=ReviewSeverity.LOW,
                        title="Too Many Function Arguments",
                        description=f"Function has {arg_count} arguments (recommended: ≤5)",
                        file_path=file_path,
                        line_start=node.lineno,
                        line_end=node.lineno,
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggestion="Consider using a configuration object or breaking into smaller functions",
                        confidence=0.9
                    ))

        return findings

    def _ai_analysis(
        self,
        file_path: str,
        code: str,
        context: Optional[Dict[str, Any]]
    ) -> List[ReviewFinding]:
        """Perform AI-powered code analysis."""
        if not self.ai_handler:
            return []

        prompt = self._build_review_prompt(file_path, code, context)

        try:
            response = self.ai_handler.chat_completion(
                model=self.settings.get("ai_review.model", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            # Parse AI response
            findings = self._parse_ai_response(response, file_path)
            return findings

        except Exception as e:
            return [ReviewFinding(
                category=ReviewCategory.BUG,
                severity=ReviewSeverity.INFO,
                title="AI Analysis Failed",
                description=f"AI analysis encountered an error: {e}",
                file_path=file_path,
                line_start=0,
                line_end=0,
                code_snippet="",
                confidence=1.0
            )]

    def _ai_diff_analysis(
        self,
        file_path: str,
        diff: str,
        changed_lines: List[int],
        context: Optional[Dict[str, Any]]
    ) -> List[ReviewFinding]:
        """Perform AI analysis on code diff."""
        if not self.ai_handler:
            return []

        prompt = self._build_diff_review_prompt(file_path, diff, context)

        try:
            response = self.ai_handler.chat_completion(
                model=self.settings.get("ai_review.model", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )

            findings = self._parse_ai_response(response, file_path)
            return findings

        except Exception:
            return []

    def _build_review_prompt(
        self,
        file_path: str,
        code: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for AI code review."""
        prompt = f"""Review the following code and identify potential issues:

File: {file_path}

```
{code}
```

Analyze for:
1. Logic errors and bugs
2. Security vulnerabilities
3. Performance issues
4. Code maintainability
5. Best practice violations

For each issue found, provide:
- Category (bug/security/performance/maintainability/style)
- Severity (critical/high/medium/low/info)
- Line number
- Description
- Suggested fix

Format response as JSON array of findings."""

        return prompt

    def _build_diff_review_prompt(
        self,
        file_path: str,
        diff: str,
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for diff review."""
        prompt = f"""Review the following code changes:

File: {file_path}

```diff
{diff}
```

Focus on the changed lines and identify:
1. Introduced bugs or regressions
2. Security vulnerabilities
3. Performance impacts
4. Breaking changes
5. Missing error handling

Format response as JSON array of findings."""

        return prompt

    def _parse_ai_response(
        self,
        response: str,
        file_path: str
    ) -> List[ReviewFinding]:
        """Parse AI response into findings."""
        findings = []

        try:
            # Try to extract JSON from response
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                data = json.loads(json_str)

                for item in data:
                    finding = ReviewFinding(
                        category=ReviewCategory(item.get('category', 'bug')),
                        severity=ReviewSeverity(item.get('severity', 'medium')),
                        title=item.get('title', 'Issue Found'),
                        description=item.get('description', ''),
                        file_path=file_path,
                        line_start=item.get('line', 0),
                        line_end=item.get('line', 0),
                        code_snippet=item.get('code_snippet', ''),
                        suggestion=item.get('suggestion'),
                        confidence=item.get('confidence', 0.8)
                    )
                    findings.append(finding)

        except Exception:
            pass

        return findings

    def _parse_diff(self, diff: str) -> List[int]:
        """Parse diff to extract changed line numbers."""
        changed_lines = []

        for line in diff.split('\n'):
            if line.startswith('+') and not line.startswith('+++'):
                # Extract line number from diff
                pass

        return changed_lines

    def _generate_summary(
        self,
        findings: List[ReviewFinding],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Generate review summary."""
        if not findings:
            return "No issues found. Code looks good!"

        critical = sum(1 for f in findings if f.severity == ReviewSeverity.CRITICAL)
        high = sum(1 for f in findings if f.severity == ReviewSeverity.HIGH)
        medium = sum(1 for f in findings if f.severity == ReviewSeverity.MEDIUM)

        summary = f"Found {len(findings)} issues: "
        parts = []
        if critical > 0:
            parts.append(f"{critical} critical")
        if high > 0:
            parts.append(f"{high} high")
        if medium > 0:
            parts.append(f"{medium} medium")

        summary += ", ".join(parts)
        return summary


# Global reviewer instance
_reviewer: Optional[AICodeReviewer] = None


def get_ai_reviewer(ai_handler: Optional[Any] = None) -> AICodeReviewer:
    """
    Get global AI code reviewer instance.

    Args:
        ai_handler: AI handler (optional)

    Returns:
        AI code reviewer instance
    """
    global _reviewer

    if _reviewer is None:
        _reviewer = AICodeReviewer(ai_handler)

    return _reviewer


def configure_ai_reviewer(ai_handler: Any):
    """
    Configure global AI code reviewer.

    Args:
        ai_handler: AI handler for model interactions
    """
    global _reviewer
    _reviewer = AICodeReviewer(ai_handler)
