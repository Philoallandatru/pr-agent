"""
Code change impact analysis system.

Analyzes the impact of code changes on the system, including:
- Direct and indirect dependencies
- Affected tests
- Risk assessment
- Change visualization
"""

import ast
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ChangeType(str, Enum):
    """Type of code change."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


class RiskLevel(str, Enum):
    """Risk level of change."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FileChange:
    """Represents a file change."""
    file_path: str
    change_type: ChangeType
    lines_added: int = 0
    lines_deleted: int = 0
    functions_changed: List[str] = field(default_factory=list)
    classes_changed: List[str] = field(default_factory=list)


@dataclass
class ImpactedFile:
    """Represents a file impacted by changes."""
    file_path: str
    impact_type: str  # "direct", "indirect", "test"
    distance: int  # Dependency distance from changed file
    reason: str  # Why this file is impacted


@dataclass
class RiskAssessment:
    """Risk assessment for changes."""
    level: RiskLevel
    score: float  # 0-100
    factors: List[str]
    recommendations: List[str]


@dataclass
class ImpactAnalysisResult:
    """Result of impact analysis."""
    changes: List[FileChange]
    impacted_files: List[ImpactedFile]
    affected_tests: List[str]
    risk_assessment: RiskAssessment
    dependency_graph: Dict[str, List[str]]
    analysis_time: datetime
    metadata: Dict = field(default_factory=dict)


class ImpactAnalyzer:
    """Analyzes the impact of code changes."""

    def __init__(self, repo_path: str):
        """
        Initialize impact analyzer.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = Path(repo_path)
        self.dependency_cache: Dict[str, Set[str]] = {}
        self.reverse_dependency_cache: Dict[str, Set[str]] = {}

    def analyze_changes(
        self,
        changed_files: List[str],
        include_tests: bool = True,
        max_depth: int = 3
    ) -> ImpactAnalysisResult:
        """
        Analyze impact of file changes.

        Args:
            changed_files: List of changed file paths
            include_tests: Whether to identify affected tests
            max_depth: Maximum dependency depth to analyze

        Returns:
            Impact analysis result
        """
        start_time = datetime.now(timezone.utc)

        # Parse changes
        changes = self._parse_changes(changed_files)

        # Build dependency graph
        dependency_graph = self._build_dependency_graph(changed_files)

        # Find impacted files
        impacted_files = self._find_impacted_files(
            changed_files,
            dependency_graph,
            max_depth
        )

        # Find affected tests
        affected_tests = []
        if include_tests:
            affected_tests = self._find_affected_tests(
                changed_files,
                impacted_files
            )

        # Assess risk
        risk_assessment = self._assess_risk(
            changes,
            impacted_files,
            affected_tests
        )

        return ImpactAnalysisResult(
            changes=changes,
            impacted_files=impacted_files,
            affected_tests=affected_tests,
            risk_assessment=risk_assessment,
            dependency_graph=dependency_graph,
            analysis_time=start_time,
            metadata={
                "total_changes": len(changes),
                "total_impacted": len(impacted_files),
                "total_tests": len(affected_tests),
                "max_depth": max_depth
            }
        )

    def _parse_changes(self, changed_files: List[str]) -> List[FileChange]:
        """Parse file changes to extract details."""
        changes = []

        for file_path in changed_files:
            full_path = self.repo_path / file_path

            if not full_path.exists():
                # File was deleted
                changes.append(FileChange(
                    file_path=file_path,
                    change_type=ChangeType.DELETED
                ))
                continue

            # Analyze file content
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                functions, classes = self._extract_definitions(content)

                changes.append(FileChange(
                    file_path=file_path,
                    change_type=ChangeType.MODIFIED,
                    functions_changed=functions,
                    classes_changed=classes
                ))
            except Exception as e:
                logger.warning(f"Error parsing {file_path}: {e}")
                changes.append(FileChange(
                    file_path=file_path,
                    change_type=ChangeType.MODIFIED
                ))

        return changes

    def _extract_definitions(
        self,
        content: str
    ) -> Tuple[List[str], List[str]]:
        """Extract function and class definitions from Python code."""
        functions = []
        classes = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
        except SyntaxError:
            pass

        return functions, classes

    def _build_dependency_graph(
        self,
        changed_files: List[str]
    ) -> Dict[str, List[str]]:
        """Build dependency graph for changed files."""
        graph = {}

        for file_path in changed_files:
            dependencies = self._get_file_dependencies(file_path)
            graph[file_path] = list(dependencies)

            # Build reverse dependencies
            for dep in dependencies:
                if dep not in self.reverse_dependency_cache:
                    self.reverse_dependency_cache[dep] = set()
                self.reverse_dependency_cache[dep].add(file_path)

        return graph

    def _get_file_dependencies(self, file_path: str) -> Set[str]:
        """Get dependencies for a file."""
        if file_path in self.dependency_cache:
            return self.dependency_cache[file_path]

        dependencies = set()
        full_path = self.repo_path / file_path

        if not full_path.exists() or not file_path.endswith('.py'):
            return dependencies

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep_path = self._resolve_import(alias.name)
                        if dep_path:
                            dependencies.add(dep_path)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dep_path = self._resolve_import(node.module)
                        if dep_path:
                            dependencies.add(dep_path)

        except Exception as e:
            logger.debug(f"Error analyzing dependencies for {file_path}: {e}")

        self.dependency_cache[file_path] = dependencies
        return dependencies

    def _resolve_import(self, module_name: str) -> Optional[str]:
        """Resolve import to file path."""
        # Convert module name to file path
        parts = module_name.split('.')

        # Try as direct module (e.g., "utils" -> "utils.py")
        if len(parts) == 1:
            module_path = self.repo_path / f"{parts[0]}.py"
            if module_path.exists():
                return str(module_path.relative_to(self.repo_path))

        # Try as package
        package_path = self.repo_path / '/'.join(parts) / '__init__.py'
        if package_path.exists():
            return str(package_path.relative_to(self.repo_path))

        # Try as nested module
        if len(parts) > 1:
            module_path = self.repo_path / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
            if module_path.exists():
                return str(module_path.relative_to(self.repo_path))

        return None

    def _find_impacted_files(
        self,
        changed_files: List[str],
        dependency_graph: Dict[str, List[str]],
        max_depth: int
    ) -> List[ImpactedFile]:
        """Find files impacted by changes."""
        impacted = []
        visited = set(changed_files)

        # Build reverse dependencies by scanning all Python files
        self._build_reverse_dependencies()

        # Direct dependencies
        for file_path in changed_files:
            for dep in dependency_graph.get(file_path, []):
                if dep not in visited:
                    impacted.append(ImpactedFile(
                        file_path=dep,
                        impact_type="direct",
                        distance=1,
                        reason=f"Directly imported by {file_path}"
                    ))
                    visited.add(dep)

        # Reverse dependencies (files that import changed files)
        for file_path in changed_files:
            for importer in self.reverse_dependency_cache.get(file_path, []):
                if importer not in visited:
                    impacted.append(ImpactedFile(
                        file_path=importer,
                        impact_type="direct",
                        distance=1,
                        reason=f"Imports {file_path}"
                    ))
                    visited.add(importer)

        # Indirect dependencies (up to max_depth)
        current_level = [f.file_path for f in impacted if f.distance == 1]
        for depth in range(2, max_depth + 1):
            next_level = []

            for file_path in current_level:
                # Forward dependencies
                for dep in self._get_file_dependencies(file_path):
                    if dep not in visited:
                        impacted.append(ImpactedFile(
                            file_path=dep,
                            impact_type="indirect",
                            distance=depth,
                            reason=f"Dependency chain through {file_path}"
                        ))
                        visited.add(dep)
                        next_level.append(dep)

                # Reverse dependencies
                for importer in self.reverse_dependency_cache.get(file_path, []):
                    if importer not in visited:
                        impacted.append(ImpactedFile(
                            file_path=importer,
                            impact_type="indirect",
                            distance=depth,
                            reason=f"Dependency chain through {file_path}"
                        ))
                        visited.add(importer)
                        next_level.append(importer)

            current_level = next_level

        return impacted

    def _build_reverse_dependencies(self):
        """Build reverse dependency cache by scanning all Python files."""
        if self.reverse_dependency_cache:
            return  # Already built

        # Find all Python files
        for py_file in self.repo_path.rglob("*.py"):
            try:
                rel_path = str(py_file.relative_to(self.repo_path))

                # Get dependencies for this file
                dependencies = self._get_file_dependencies(rel_path)

                # Update reverse dependencies
                for dep in dependencies:
                    if dep not in self.reverse_dependency_cache:
                        self.reverse_dependency_cache[dep] = set()
                    self.reverse_dependency_cache[dep].add(rel_path)
            except Exception as e:
                logger.debug(f"Error processing {py_file}: {e}")

    def _find_affected_tests(
        self,
        changed_files: List[str],
        impacted_files: List[ImpactedFile]
    ) -> List[str]:
        """Find tests affected by changes."""
        affected_tests = set()

        # All files that might need testing
        all_files = set(changed_files)
        all_files.update(f.file_path for f in impacted_files)

        # Find corresponding test files
        for file_path in all_files:
            test_paths = self._find_test_files(file_path)
            affected_tests.update(test_paths)

        return sorted(affected_tests)

    def _find_test_files(self, file_path: str) -> List[str]:
        """Find test files for a given file."""
        tests = []
        path = Path(file_path)

        # Common test patterns
        patterns = [
            f"test_{path.stem}.py",
            f"{path.stem}_test.py",
            f"test{path.stem}.py"
        ]

        # Check in same directory
        for pattern in patterns:
            test_path = path.parent / pattern
            full_test_path = self.repo_path / test_path
            if full_test_path.exists():
                tests.append(str(test_path))

        # Check in tests directory
        tests_dir = self.repo_path / "tests"
        if tests_dir.exists():
            for pattern in patterns:
                test_path = tests_dir / pattern
                if test_path.exists():
                    tests.append(str(test_path.relative_to(self.repo_path)))

        return tests

    def _assess_risk(
        self,
        changes: List[FileChange],
        impacted_files: List[ImpactedFile],
        affected_tests: List[str]
    ) -> RiskAssessment:
        """Assess risk level of changes."""
        score = 0.0
        factors = []
        recommendations = []

        # Factor 1: Number of changed files
        if len(changes) > 10:
            score += 20
            factors.append(f"Large number of changed files ({len(changes)})")
            recommendations.append("Consider breaking changes into smaller PRs")
        elif len(changes) > 5:
            score += 10
            factors.append(f"Moderate number of changed files ({len(changes)})")

        # Factor 2: Impact scope
        if len(impacted_files) > 20:
            score += 30
            factors.append(f"Wide impact scope ({len(impacted_files)} files)")
            recommendations.append("Extensive testing required")
        elif len(impacted_files) > 10:
            score += 15
            factors.append(f"Moderate impact scope ({len(impacted_files)} files)")

        # Factor 3: Deleted files
        deleted_count = sum(1 for c in changes if c.change_type == ChangeType.DELETED)
        if deleted_count > 0:
            score += deleted_count * 5
            factors.append(f"{deleted_count} file(s) deleted")
            recommendations.append("Verify no broken imports")

        # Factor 4: Test coverage
        if len(affected_tests) == 0 and len(changes) > 0:
            score += 25
            factors.append("No tests found for changes")
            recommendations.append("Add tests for changed code")
        elif len(affected_tests) < len(changes):
            score += 10
            factors.append("Incomplete test coverage")
            recommendations.append("Consider adding more tests")

        # Factor 5: Core file changes
        core_patterns = ['__init__.py', 'config', 'settings', 'main']
        core_changes = [
            c for c in changes
            if any(pattern in c.file_path for pattern in core_patterns)
        ]
        if core_changes:
            score += len(core_changes) * 10
            factors.append(f"{len(core_changes)} core file(s) changed")
            recommendations.append("Extra caution with core files")

        # Determine risk level
        if score >= 70:
            level = RiskLevel.CRITICAL
            recommendations.insert(0, "Critical risk - thorough review required")
        elif score >= 50:
            level = RiskLevel.HIGH
            recommendations.insert(0, "High risk - careful review needed")
        elif score >= 30:
            level = RiskLevel.MEDIUM
            recommendations.insert(0, "Medium risk - standard review process")
        else:
            level = RiskLevel.LOW
            recommendations.insert(0, "Low risk - routine review")

        return RiskAssessment(
            level=level,
            score=min(score, 100.0),
            factors=factors,
            recommendations=recommendations
        )

    def visualize_impact(
        self,
        result: ImpactAnalysisResult,
        output_format: str = "text"
    ) -> str:
        """
        Visualize impact analysis result.

        Args:
            result: Impact analysis result
            output_format: Output format ("text", "dot")

        Returns:
            Visualization string
        """
        if output_format == "dot":
            return self._generate_dot_graph(result)
        else:
            return self._generate_text_visualization(result)

    def _generate_text_visualization(
        self,
        result: ImpactAnalysisResult
    ) -> str:
        """Generate text visualization."""
        lines = [
            "=" * 80,
            "CODE CHANGE IMPACT ANALYSIS",
            "=" * 80,
            "",
            f"Analysis Time: {result.analysis_time.isoformat()}",
            f"Total Changes: {len(result.changes)}",
            f"Impacted Files: {len(result.impacted_files)}",
            f"Affected Tests: {len(result.affected_tests)}",
            "",
            "RISK ASSESSMENT",
            "-" * 80,
            f"Level: {result.risk_assessment.level.value.upper()}",
            f"Score: {result.risk_assessment.score:.1f}/100",
            "",
            "Risk Factors:",
        ]

        for factor in result.risk_assessment.factors:
            lines.append(f"  - {factor}")

        lines.extend([
            "",
            "Recommendations:",
        ])

        for rec in result.risk_assessment.recommendations:
            lines.append(f"  - {rec}")

        lines.extend([
            "",
            "CHANGED FILES",
            "-" * 80,
        ])

        for change in result.changes:
            lines.append(f"  [{change.change_type.value}] {change.file_path}")
            if change.functions_changed:
                lines.append(f"    Functions: {', '.join(change.functions_changed)}")
            if change.classes_changed:
                lines.append(f"    Classes: {', '.join(change.classes_changed)}")

        if result.impacted_files:
            lines.extend([
                "",
                "IMPACTED FILES",
                "-" * 80,
            ])

            # Group by distance
            by_distance = {}
            for impacted in result.impacted_files:
                if impacted.distance not in by_distance:
                    by_distance[impacted.distance] = []
                by_distance[impacted.distance].append(impacted)

            for distance in sorted(by_distance.keys()):
                lines.append(f"  Distance {distance}:")
                for impacted in by_distance[distance]:
                    lines.append(f"    - {impacted.file_path}")
                    lines.append(f"      {impacted.reason}")

        if result.affected_tests:
            lines.extend([
                "",
                "AFFECTED TESTS",
                "-" * 80,
            ])
            for test in result.affected_tests:
                lines.append(f"  - {test}")

        lines.append("=" * 80)

        return "\n".join(lines)

    def _generate_dot_graph(self, result: ImpactAnalysisResult) -> str:
        """Generate DOT graph visualization."""
        lines = [
            "digraph impact {",
            "  rankdir=LR;",
            "  node [shape=box];",
            ""
        ]

        # Changed files (red)
        for change in result.changes:
            label = change.file_path.split('/')[-1]
            lines.append(f'  "{change.file_path}" [label="{label}", color=red, style=filled, fillcolor=lightcoral];')

        # Impacted files (yellow/orange by distance)
        colors = {1: "lightyellow", 2: "lightgoldenrod", 3: "orange"}
        for impacted in result.impacted_files:
            label = impacted.file_path.split('/')[-1]
            color = colors.get(impacted.distance, "lightgray")
            lines.append(f'  "{impacted.file_path}" [label="{label}", style=filled, fillcolor={color}];')

        # Dependencies
        for file_path, deps in result.dependency_graph.items():
            for dep in deps:
                lines.append(f'  "{file_path}" -> "{dep}";')

        lines.append("}")

        return "\n".join(lines)
