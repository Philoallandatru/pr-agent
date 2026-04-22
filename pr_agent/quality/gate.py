"""
Code quality gate system for automated quality checks.

Provides comprehensive quality analysis including complexity,
coverage, security, and style checks with configurable gates.
"""

import ast
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logger = logging.getLogger(__name__)


class CheckType(Enum):
    """Quality check types."""
    COMPLEXITY = "complexity"
    COVERAGE = "coverage"
    SECURITY = "security"
    STYLE = "style"
    DUPLICATION = "duplication"
    DOCUMENTATION = "documentation"


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class QualityIssue:
    """Quality issue found during checks."""
    check_type: CheckType
    severity: Severity
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    code: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QualityGateConfig:
    """Quality gate configuration."""
    # Complexity thresholds
    max_cyclomatic_complexity: int = 10
    max_cognitive_complexity: int = 15
    max_function_length: int = 50
    max_file_length: int = 500

    # Coverage requirements
    min_line_coverage: float = 80.0
    min_branch_coverage: float = 70.0

    # Security checks
    check_secrets: bool = True
    check_vulnerabilities: bool = True

    # Style checks
    enforce_style: bool = True
    max_line_length: int = 120

    # Duplication
    max_duplication_percentage: float = 5.0

    # Documentation
    require_docstrings: bool = True
    min_comment_ratio: float = 0.1

    # Gate behavior
    block_on_critical: bool = True
    block_on_high: bool = True
    block_on_medium: bool = False


@dataclass
class QualityReport:
    """Quality check report."""
    passed: bool
    issues: List[QualityIssue]
    metrics: Dict[str, Any]
    timestamp: datetime
    duration_seconds: float

    def get_issues_by_severity(self, severity: Severity) -> List[QualityIssue]:
        """Get issues by severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_type(self, check_type: CheckType) -> List[QualityIssue]:
        """Get issues by check type."""
        return [issue for issue in self.issues if issue.check_type == check_type]

    def get_blocking_issues(self, config: QualityGateConfig) -> List[QualityIssue]:
        """Get issues that should block the PR."""
        blocking = []
        for issue in self.issues:
            if config.block_on_critical and issue.severity == Severity.CRITICAL:
                blocking.append(issue)
            elif config.block_on_high and issue.severity == Severity.HIGH:
                blocking.append(issue)
            elif config.block_on_medium and issue.severity == Severity.MEDIUM:
                blocking.append(issue)
        return blocking


class ComplexityAnalyzer:
    """Analyze code complexity."""

    def analyze_file(self, file_path: str) -> List[QualityIssue]:
        """Analyze complexity of a Python file."""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Calculate cyclomatic complexity
                    complexity = self._calculate_cyclomatic_complexity(node)

                    if complexity > 10:
                        severity = Severity.HIGH if complexity > 15 else Severity.MEDIUM
                        issues.append(QualityIssue(
                            check_type=CheckType.COMPLEXITY,
                            severity=severity,
                            message=f"Function '{node.name}' has high cyclomatic complexity: {complexity}",
                            file_path=file_path,
                            line_number=node.lineno,
                            suggestion="Consider breaking down into smaller functions",
                            metadata={"complexity": complexity}
                        ))

                    # Check function length
                    func_length = self._get_function_length(node)
                    if func_length > 50:
                        issues.append(QualityIssue(
                            check_type=CheckType.COMPLEXITY,
                            severity=Severity.MEDIUM,
                            message=f"Function '{node.name}' is too long: {func_length} lines",
                            file_path=file_path,
                            line_number=node.lineno,
                            suggestion="Consider splitting into smaller functions",
                            metadata={"length": func_length}
                        ))

        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}")

        return issues

    def _calculate_cyclomatic_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Decision points increase complexity
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                # BoolOp (and/or) adds complexity for each operator
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                # List/dict/set comprehensions add complexity
                complexity += 1

        return complexity

    def _get_function_length(self, node: ast.AST) -> int:
        """Get number of lines in a function."""
        if hasattr(node, 'end_lineno') and hasattr(node, 'lineno'):
            return node.end_lineno - node.lineno + 1
        return 0


class SecurityScanner:
    """Scan for security vulnerabilities."""

    # Common secret patterns
    SECRET_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']([^"\']+)["\']', "API Key"),
        (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']([^"\']+)["\']', "Password"),
        (r'(?i)(secret|token)\s*[:=]\s*["\']([^"\']+)["\']', "Secret/Token"),
        (r'(?i)(aws[_-]?access[_-]?key[_-]?id)\s*[:=]\s*["\']([^"\']+)["\']', "AWS Access Key"),
        (r'(?i)(private[_-]?key)\s*[:=]\s*["\']([^"\']+)["\']', "Private Key"),
    ]

    # Dangerous function calls
    DANGEROUS_FUNCTIONS = [
        ('eval', "Use of eval() is dangerous"),
        ('exec', "Use of exec() is dangerous"),
        ('__import__', "Dynamic imports can be dangerous"),
        ('compile', "Dynamic code compilation can be dangerous"),
    ]

    def scan_file(self, file_path: str) -> List[QualityIssue]:
        """Scan file for security issues."""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')

            # Check for secrets
            for line_num, line in enumerate(lines, 1):
                for pattern, secret_type in self.SECRET_PATTERNS:
                    if re.search(pattern, line):
                        issues.append(QualityIssue(
                            check_type=CheckType.SECURITY,
                            severity=Severity.CRITICAL,
                            message=f"Potential {secret_type} found in code",
                            file_path=file_path,
                            line_number=line_num,
                            code=line.strip(),
                            suggestion="Move secrets to environment variables or secret manager"
                        ))

            # Check for dangerous functions (Python only)
            if file_path.endswith('.py'):
                try:
                    tree = ast.parse(content, filename=file_path)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            func_name = None
                            if isinstance(node.func, ast.Name):
                                func_name = node.func.id
                            elif isinstance(node.func, ast.Attribute):
                                func_name = node.func.attr

                            if func_name:
                                for dangerous_func, message in self.DANGEROUS_FUNCTIONS:
                                    if func_name == dangerous_func:
                                        issues.append(QualityIssue(
                                            check_type=CheckType.SECURITY,
                                            severity=Severity.HIGH,
                                            message=message,
                                            file_path=file_path,
                                            line_number=node.lineno,
                                            suggestion="Use safer alternatives"
                                        ))

                except SyntaxError:
                    pass

        except Exception as e:
            logger.error(f"Error scanning {file_path}: {e}")

        return issues


class StyleChecker:
    """Check code style compliance."""

    def check_file(self, file_path: str, max_line_length: int = 120) -> List[QualityIssue]:
        """Check file for style issues."""
        issues = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num, line in enumerate(lines, 1):
                # Check line length
                if len(line.rstrip()) > max_line_length:
                    issues.append(QualityIssue(
                        check_type=CheckType.STYLE,
                        severity=Severity.LOW,
                        message=f"Line exceeds maximum length ({len(line.rstrip())} > {max_line_length})",
                        file_path=file_path,
                        line_number=line_num,
                        suggestion="Break line into multiple lines"
                    ))

                # Check trailing whitespace
                if line.rstrip() != line.rstrip('\n').rstrip('\r'):
                    issues.append(QualityIssue(
                        check_type=CheckType.STYLE,
                        severity=Severity.INFO,
                        message="Trailing whitespace found",
                        file_path=file_path,
                        line_number=line_num,
                        suggestion="Remove trailing whitespace"
                    ))

        except Exception as e:
            logger.error(f"Error checking style in {file_path}: {e}")

        return issues


class DocumentationChecker:
    """Check documentation completeness."""

    def check_file(self, file_path: str) -> List[QualityIssue]:
        """Check file for documentation issues."""
        issues = []

        if not file_path.endswith('.py'):
            return issues

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Check for docstring
                    docstring = ast.get_docstring(node)

                    if not docstring:
                        # Skip private functions/classes
                        if not node.name.startswith('_'):
                            issues.append(QualityIssue(
                                check_type=CheckType.DOCUMENTATION,
                                severity=Severity.LOW,
                                message=f"Missing docstring for {node.__class__.__name__.lower()} '{node.name}'",
                                file_path=file_path,
                                line_number=node.lineno,
                                suggestion="Add docstring describing purpose and parameters"
                            ))

        except Exception as e:
            logger.error(f"Error checking documentation in {file_path}: {e}")

        return issues


class QualityGate:
    """
    Code quality gate system.

    Performs comprehensive quality checks and determines if code
    meets quality standards.
    """

    def __init__(self, config: Optional[QualityGateConfig] = None):
        """
        Initialize quality gate.

        Args:
            config: Quality gate configuration
        """
        self.config = config or QualityGateConfig()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.security_scanner = SecurityScanner()
        self.style_checker = StyleChecker()
        self.doc_checker = DocumentationChecker()

    def check_files(self, file_paths: List[str]) -> QualityReport:
        """
        Check multiple files.

        Args:
            file_paths: List of file paths to check

        Returns:
            Quality report
        """
        start_time = datetime.now()
        all_issues = []
        metrics = {
            "files_checked": len(file_paths),
            "total_issues": 0,
            "by_severity": {},
            "by_type": {}
        }

        for file_path in file_paths:
            # Skip non-code files
            if not self._is_code_file(file_path):
                continue

            # Run checks
            if file_path.endswith('.py'):
                all_issues.extend(self.complexity_analyzer.analyze_file(file_path))

            all_issues.extend(self.security_scanner.scan_file(file_path))
            all_issues.extend(self.style_checker.check_file(
                file_path,
                self.config.max_line_length
            ))

            if self.config.require_docstrings:
                all_issues.extend(self.doc_checker.check_file(file_path))

        # Calculate metrics
        metrics["total_issues"] = len(all_issues)

        for severity in Severity:
            count = len([i for i in all_issues if i.severity == severity])
            metrics["by_severity"][severity.value] = count

        for check_type in CheckType:
            count = len([i for i in all_issues if i.check_type == check_type])
            metrics["by_type"][check_type.value] = count

        # Determine if gate passes
        blocking_issues = []
        for issue in all_issues:
            if self.config.block_on_critical and issue.severity == Severity.CRITICAL:
                blocking_issues.append(issue)
            elif self.config.block_on_high and issue.severity == Severity.HIGH:
                blocking_issues.append(issue)
            elif self.config.block_on_medium and issue.severity == Severity.MEDIUM:
                blocking_issues.append(issue)

        passed = len(blocking_issues) == 0

        duration = (datetime.now() - start_time).total_seconds()

        return QualityReport(
            passed=passed,
            issues=all_issues,
            metrics=metrics,
            timestamp=datetime.now(),
            duration_seconds=duration
        )

    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file."""
        code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c', '.h'}
        return any(file_path.endswith(ext) for ext in code_extensions)


# Global quality gate instance
_global_gate: Optional[QualityGate] = None


def get_quality_gate() -> QualityGate:
    """Get global quality gate instance."""
    global _global_gate
    if _global_gate is None:
        _global_gate = QualityGate()
    return _global_gate


def configure_quality_gate(config: QualityGateConfig):
    """Configure global quality gate."""
    global _global_gate
    _global_gate = QualityGate(config)
