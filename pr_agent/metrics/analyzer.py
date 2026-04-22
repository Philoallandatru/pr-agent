"""
Code Metrics Analyzer

Analyzes code to compute various metrics including:
- Lines of code (LOC, SLOC, comments)
- Cyclomatic complexity
- Maintainability index
- Code duplication
- Technical debt
"""

import ast
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict
import hashlib


class MetricType(str, Enum):
    """Types of code metrics."""
    LOC = "loc"  # Lines of code
    SLOC = "sloc"  # Source lines of code (non-blank, non-comment)
    COMMENTS = "comments"  # Comment lines
    COMPLEXITY = "complexity"  # Cyclomatic complexity
    MAINTAINABILITY = "maintainability"  # Maintainability index
    DUPLICATION = "duplication"  # Code duplication percentage
    DEBT = "debt"  # Technical debt hours


class Severity(str, Enum):
    """Severity levels for metrics."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FileMetrics:
    """Metrics for a single file."""
    path: str
    language: str
    loc: int = 0  # Total lines
    sloc: int = 0  # Source lines (non-blank, non-comment)
    comments: int = 0  # Comment lines
    blank: int = 0  # Blank lines
    complexity: int = 0  # Cyclomatic complexity
    maintainability: float = 0.0  # Maintainability index (0-100)
    functions: int = 0  # Number of functions
    classes: int = 0  # Number of classes
    duplicates: List[Tuple[int, int, str]] = field(default_factory=list)  # (start, end, hash)
    issues: List[str] = field(default_factory=list)


@dataclass
class ProjectMetrics:
    """Aggregated metrics for entire project."""
    total_files: int = 0
    total_loc: int = 0
    total_sloc: int = 0
    total_comments: int = 0
    total_blank: int = 0
    avg_complexity: float = 0.0
    avg_maintainability: float = 0.0
    total_functions: int = 0
    total_classes: int = 0
    duplication_percentage: float = 0.0
    technical_debt_hours: float = 0.0
    files: List[FileMetrics] = field(default_factory=list)
    language_breakdown: Dict[str, int] = field(default_factory=dict)
    complexity_distribution: Dict[str, int] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class MetricsTrend:
    """Trend data for metrics over time."""
    metric: MetricType
    timestamps: List[str] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    change_percentage: float = 0.0
    trend: str = "stable"  # "improving", "degrading", "stable"


class ComplexityVisitor(ast.NodeVisitor):
    """AST visitor to calculate cyclomatic complexity."""

    def __init__(self):
        self.complexity = 1  # Base complexity
        self.functions = 0
        self.classes = 0

    def visit_FunctionDef(self, node):
        self.functions += 1
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        self.functions += 1
        self.complexity += 1
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        self.classes += 1
        self.generic_visit(node)

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_With(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_AsyncWith(self, node):
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


class MetricsAnalyzer:
    """Analyzes code metrics for projects."""

    def __init__(self):
        self.duplicate_threshold = 6  # Minimum lines for duplication detection
        self.complexity_thresholds = {
            Severity.LOW: 10,
            Severity.MEDIUM: 20,
            Severity.HIGH: 30,
            Severity.CRITICAL: 50
        }

    def analyze_file(self, file_path: str) -> FileMetrics:
        """Analyze metrics for a single file."""
        path = Path(file_path)
        language = self._detect_language(path)

        metrics = FileMetrics(
            path=str(path),
            language=language
        )

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            lines = content.split('\n')
            metrics.loc = len(lines)

            if language == "python":
                self._analyze_python(content, lines, metrics)
            else:
                self._analyze_generic(lines, metrics)

            # Calculate maintainability index
            metrics.maintainability = self._calculate_maintainability(metrics)

            # Detect issues
            self._detect_issues(metrics)

        except Exception as e:
            metrics.issues.append(f"Failed to analyze: {str(e)}")

        return metrics

    def analyze_project(
        self,
        project_dir: str,
        patterns: Optional[List[str]] = None
    ) -> ProjectMetrics:
        """Analyze metrics for entire project."""
        project_path = Path(project_dir)

        if not project_path.exists():
            raise ValueError(f"Project directory not found: {project_dir}")

        patterns = patterns or ["*.py", "*.js", "*.ts", "*.java", "*.go"]
        files = []

        for pattern in patterns:
            files.extend(project_path.rglob(pattern))

        metrics = ProjectMetrics()
        file_metrics_list = []

        for file_path in files:
            if self._should_skip(file_path):
                continue

            file_metrics = self.analyze_file(str(file_path))
            file_metrics_list.append(file_metrics)

            # Aggregate
            metrics.total_files += 1
            metrics.total_loc += file_metrics.loc
            metrics.total_sloc += file_metrics.sloc
            metrics.total_comments += file_metrics.comments
            metrics.total_blank += file_metrics.blank
            metrics.total_functions += file_metrics.functions
            metrics.total_classes += file_metrics.classes

            # Language breakdown
            lang = file_metrics.language
            metrics.language_breakdown[lang] = metrics.language_breakdown.get(lang, 0) + 1

        metrics.files = file_metrics_list

        # Calculate averages
        if metrics.total_files > 0:
            total_complexity = sum(f.complexity for f in file_metrics_list)
            total_maintainability = sum(f.maintainability for f in file_metrics_list)

            metrics.avg_complexity = total_complexity / metrics.total_files
            metrics.avg_maintainability = total_maintainability / metrics.total_files

        # Detect duplication
        metrics.duplication_percentage = self._detect_duplication(file_metrics_list)

        # Calculate technical debt
        metrics.technical_debt_hours = self._calculate_technical_debt(metrics)

        # Complexity distribution
        metrics.complexity_distribution = self._get_complexity_distribution(file_metrics_list)

        return metrics

    def _analyze_python(self, content: str, lines: List[str], metrics: FileMetrics):
        """Analyze Python-specific metrics."""
        # Count lines
        for line in lines:
            stripped = line.strip()
            if not stripped:
                metrics.blank += 1
            elif stripped.startswith('#'):
                metrics.comments += 1
            else:
                metrics.sloc += 1

        # Parse AST for complexity
        try:
            tree = ast.parse(content)
            visitor = ComplexityVisitor()
            visitor.visit(tree)

            metrics.complexity = visitor.complexity
            metrics.functions = visitor.functions
            metrics.classes = visitor.classes
        except SyntaxError:
            metrics.issues.append("Syntax error in file")

    def _analyze_generic(self, lines: List[str], metrics: FileMetrics):
        """Analyze generic file metrics."""
        comment_patterns = [
            r'^\s*#',  # Python, Shell
            r'^\s*//',  # C++, Java, JavaScript
            r'^\s*/\*',  # C-style block comment start
            r'^\s*\*',  # C-style block comment middle
        ]

        for line in lines:
            stripped = line.strip()
            if not stripped:
                metrics.blank += 1
            elif any(re.match(pattern, line) for pattern in comment_patterns):
                metrics.comments += 1
            else:
                metrics.sloc += 1

    def _calculate_maintainability(self, metrics: FileMetrics) -> float:
        """Calculate maintainability index (0-100)."""
        if metrics.sloc == 0:
            return 100.0

        # Simplified maintainability index
        # MI = 171 - 5.2 * ln(V) - 0.23 * G - 16.2 * ln(LOC)
        # Where V = Halstead Volume, G = Cyclomatic Complexity, LOC = Lines of Code

        import math

        loc = max(metrics.sloc, 1)
        complexity = max(metrics.complexity, 1)

        # Simplified formula (without Halstead volume)
        mi = 171 - 0.23 * complexity - 16.2 * math.log(loc)

        # Normalize to 0-100
        mi = max(0, min(100, mi))

        return round(mi, 2)

    def _detect_issues(self, metrics: FileMetrics):
        """Detect code quality issues."""
        # High complexity
        if metrics.complexity > self.complexity_thresholds[Severity.CRITICAL]:
            metrics.issues.append(f"Critical complexity: {metrics.complexity}")
        elif metrics.complexity > self.complexity_thresholds[Severity.HIGH]:
            metrics.issues.append(f"High complexity: {metrics.complexity}")

        # Low maintainability
        if metrics.maintainability < 20:
            metrics.issues.append(f"Low maintainability: {metrics.maintainability}")

        # Large file
        if metrics.sloc > 1000:
            metrics.issues.append(f"Large file: {metrics.sloc} SLOC")

    def _detect_duplication(self, files: List[FileMetrics]) -> float:
        """Detect code duplication across files."""
        if not files:
            return 0.0

        # Simple hash-based duplication detection
        line_hashes = defaultdict(list)
        total_lines = 0

        for file_metrics in files:
            try:
                with open(file_metrics.path, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]

                total_lines += len(lines)

                # Hash consecutive line groups
                for i in range(len(lines) - self.duplicate_threshold + 1):
                    group = '\n'.join(lines[i:i + self.duplicate_threshold])
                    hash_val = hashlib.md5(group.encode()).hexdigest()
                    line_hashes[hash_val].append((file_metrics.path, i))
            except Exception:
                continue

        # Count duplicated lines
        duplicated_lines = 0
        for hash_val, occurrences in line_hashes.items():
            if len(occurrences) > 1:
                duplicated_lines += self.duplicate_threshold * len(occurrences)

        if total_lines == 0:
            return 0.0

        return round((duplicated_lines / total_lines) * 100, 2)

    def _calculate_technical_debt(self, metrics: ProjectMetrics) -> float:
        """Calculate technical debt in hours."""
        debt_hours = 0.0

        for file_metrics in metrics.files:
            # Complexity debt (5 min per point over threshold)
            if file_metrics.complexity > self.complexity_thresholds[Severity.LOW]:
                excess = file_metrics.complexity - self.complexity_thresholds[Severity.LOW]
                debt_hours += (excess * 5) / 60

            # Maintainability debt (1 hour per 10 points below 65)
            if file_metrics.maintainability < 65:
                deficit = 65 - file_metrics.maintainability
                debt_hours += deficit / 10

            # Large file debt (2 hours per 1000 lines over 500)
            if file_metrics.sloc > 500:
                excess = (file_metrics.sloc - 500) / 1000
                debt_hours += excess * 2

        # Duplication debt (1 hour per 1% duplication)
        debt_hours += metrics.duplication_percentage

        return round(debt_hours, 2)

    def _get_complexity_distribution(self, files: List[FileMetrics]) -> Dict[str, int]:
        """Get distribution of complexity levels."""
        distribution = {
            "low": 0,
            "medium": 0,
            "high": 0,
            "critical": 0
        }

        for file_metrics in files:
            complexity = file_metrics.complexity

            if complexity <= self.complexity_thresholds[Severity.LOW]:
                distribution["low"] += 1
            elif complexity <= self.complexity_thresholds[Severity.MEDIUM]:
                distribution["medium"] += 1
            elif complexity <= self.complexity_thresholds[Severity.HIGH]:
                distribution["high"] += 1
            else:
                distribution["critical"] += 1

        return distribution

    def _detect_language(self, path: Path) -> str:
        """Detect programming language from file extension."""
        ext = path.suffix.lower()

        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
        }

        return language_map.get(ext, 'unknown')

    def _should_skip(self, path: Path) -> bool:
        """Check if file should be skipped."""
        skip_dirs = {
            'node_modules', 'venv', '.venv', '__pycache__',
            '.git', '.pytest_cache', 'dist', 'build'
        }

        return any(skip_dir in path.parts for skip_dir in skip_dirs)

    def generate_report(self, metrics: ProjectMetrics, format: str = "text") -> str:
        """Generate metrics report."""
        if format == "text":
            return self._generate_text_report(metrics)
        elif format == "json":
            import json
            return json.dumps(self._metrics_to_dict(metrics), indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _generate_text_report(self, metrics: ProjectMetrics) -> str:
        """Generate text report."""
        lines = [
            "=" * 60,
            "CODE METRICS REPORT",
            "=" * 60,
            "",
            f"Generated: {metrics.timestamp}",
            "",
            "SUMMARY",
            "-" * 60,
            f"Total Files:              {metrics.total_files}",
            f"Total Lines:              {metrics.total_loc:,}",
            f"Source Lines:             {metrics.total_sloc:,}",
            f"Comment Lines:            {metrics.total_comments:,}",
            f"Blank Lines:              {metrics.total_blank:,}",
            f"Functions:                {metrics.total_functions}",
            f"Classes:                  {metrics.total_classes}",
            "",
            f"Average Complexity:       {metrics.avg_complexity:.2f}",
            f"Average Maintainability:  {metrics.avg_maintainability:.2f}",
            f"Code Duplication:         {metrics.duplication_percentage:.2f}%",
            f"Technical Debt:           {metrics.technical_debt_hours:.2f} hours",
            "",
            "LANGUAGE BREAKDOWN",
            "-" * 60,
        ]

        for lang, count in sorted(metrics.language_breakdown.items()):
            lines.append(f"{lang:20} {count:5} files")

        lines.extend([
            "",
            "COMPLEXITY DISTRIBUTION",
            "-" * 60,
        ])

        for level, count in metrics.complexity_distribution.items():
            lines.append(f"{level.capitalize():20} {count:5} files")

        # Top issues
        files_with_issues = [f for f in metrics.files if f.issues]
        if files_with_issues:
            lines.extend([
                "",
                "TOP ISSUES",
                "-" * 60,
            ])

            for file_metrics in files_with_issues[:10]:
                lines.append(f"\n{file_metrics.path}")
                for issue in file_metrics.issues:
                    lines.append(f"  - {issue}")

        lines.append("\n" + "=" * 60)

        return '\n'.join(lines)

    def _metrics_to_dict(self, metrics: ProjectMetrics) -> dict:
        """Convert metrics to dictionary."""
        return {
            "summary": {
                "total_files": metrics.total_files,
                "total_loc": metrics.total_loc,
                "total_sloc": metrics.total_sloc,
                "total_comments": metrics.total_comments,
                "total_blank": metrics.total_blank,
                "total_functions": metrics.total_functions,
                "total_classes": metrics.total_classes,
                "avg_complexity": metrics.avg_complexity,
                "avg_maintainability": metrics.avg_maintainability,
                "duplication_percentage": metrics.duplication_percentage,
                "technical_debt_hours": metrics.technical_debt_hours,
            },
            "language_breakdown": metrics.language_breakdown,
            "complexity_distribution": metrics.complexity_distribution,
            "timestamp": metrics.timestamp,
            "files": [
                {
                    "path": f.path,
                    "language": f.language,
                    "loc": f.loc,
                    "sloc": f.sloc,
                    "complexity": f.complexity,
                    "maintainability": f.maintainability,
                    "issues": f.issues
                }
                for f in metrics.files
            ]
        }


# Singleton instance
_analyzer = None


def get_metrics_analyzer() -> MetricsAnalyzer:
    """Get singleton metrics analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = MetricsAnalyzer()
    return _analyzer
