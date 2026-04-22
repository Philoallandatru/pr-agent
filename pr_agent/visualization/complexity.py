"""
Code complexity visualization system.

Generates visual representations of code complexity including:
- Complexity heatmaps
- Dependency graphs
- Function call graphs
- Module structure diagrams
"""

import ast
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set, Tuple

if TYPE_CHECKING:
    import graphviz

try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False
    graphviz = None  # type: ignore


@dataclass
class FunctionNode:
    """Represents a function in the call graph."""
    name: str
    module: str
    complexity: int
    line_number: int
    calls: List[str] = field(default_factory=list)
    called_by: List[str] = field(default_factory=list)


@dataclass
class ModuleNode:
    """Represents a module in the dependency graph."""
    name: str
    path: str
    imports: List[str] = field(default_factory=list)
    imported_by: List[str] = field(default_factory=list)
    complexity: int = 0
    function_count: int = 0


class ComplexityVisualizer:
    """
    Generate visual representations of code complexity.
    """

    def __init__(self, project_root: str):
        """
        Initialize complexity visualizer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.functions: Dict[str, FunctionNode] = {}
        self.modules: Dict[str, ModuleNode] = {}

    def analyze_project(self, source_dirs: Optional[List[str]] = None):
        """
        Analyze project structure and complexity.

        Args:
            source_dirs: Source directories to analyze (default: project root)
        """
        if source_dirs is None:
            source_dirs = ["."]

        for source_dir in source_dirs:
            source_path = self.project_root / source_dir
            if not source_path.exists():
                continue

            for py_file in source_path.rglob("*.py"):
                if "__pycache__" in str(py_file):
                    continue

                self._analyze_file(py_file)

        # Build call relationships
        self._build_call_graph()

    def _analyze_file(self, file_path: Path):
        """Analyze a single Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            module_name = self._get_module_name(file_path)

            # Create module node
            module = ModuleNode(
                name=module_name,
                path=str(file_path.relative_to(self.project_root))
            )

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module.imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module.imports.append(node.module)

            # Extract functions
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_name = f"{module_name}.{node.name}"
                    complexity = self._calculate_complexity(node)

                    # Extract function calls
                    calls = []
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            if isinstance(child.func, ast.Name):
                                calls.append(child.func.id)
                            elif isinstance(child.func, ast.Attribute):
                                calls.append(child.func.attr)

                    function = FunctionNode(
                        name=func_name,
                        module=module_name,
                        complexity=complexity,
                        line_number=node.lineno,
                        calls=calls,
                    )

                    self.functions[func_name] = function
                    module.complexity += complexity
                    module.function_count += 1

            self.modules[module_name] = module

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _get_module_name(self, file_path: Path) -> str:
        """Get module name from file path."""
        rel_path = file_path.relative_to(self.project_root)
        parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        return ".".join(parts)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, (ast.And, ast.Or)):
                complexity += 1
        return complexity

    def _build_call_graph(self):
        """Build function call relationships."""
        for func_name, func in self.functions.items():
            for call in func.calls:
                # Try to find the called function
                for target_name, target in self.functions.items():
                    if target_name.endswith(f".{call}"):
                        target.called_by.append(func_name)

    def generate_complexity_heatmap(
        self,
        output_path: str,
        format: str = "svg"
    ) -> str:
        """
        Generate complexity heatmap.

        Args:
            output_path: Output file path (without extension)
            format: Output format (svg, png, pdf)

        Returns:
            Path to generated file
        """
        if not GRAPHVIZ_AVAILABLE:
            raise RuntimeError("graphviz package is required for visualization")

        dot = graphviz.Digraph(comment="Complexity Heatmap")
        dot.attr(rankdir="TB")
        dot.attr("node", shape="box", style="filled")

        # Group functions by module
        modules_funcs = defaultdict(list)
        for func_name, func in self.functions.items():
            modules_funcs[func.module].append(func)

        # Create subgraphs for each module
        for module_name, funcs in modules_funcs.items():
            with dot.subgraph(name=f"cluster_{module_name}") as c:
                c.attr(label=module_name)

                for func in funcs:
                    # Color based on complexity
                    color = self._get_complexity_color(func.complexity)
                    label = f"{func.name.split('.')[-1]}\\n({func.complexity})"

                    c.node(
                        func.name,
                        label=label,
                        fillcolor=color,
                        fontcolor="white" if func.complexity > 10 else "black"
                    )

        # Render
        output_file = dot.render(output_path, format=format, cleanup=True)
        return output_file

    def generate_dependency_graph(
        self,
        output_path: str,
        format: str = "svg"
    ) -> str:
        """
        Generate module dependency graph.

        Args:
            output_path: Output file path (without extension)
            format: Output format (svg, png, pdf)

        Returns:
            Path to generated file
        """
        if not GRAPHVIZ_AVAILABLE:
            raise RuntimeError("graphviz package is required for visualization")

        dot = graphviz.Digraph(comment="Module Dependencies")
        dot.attr(rankdir="LR")
        dot.attr("node", shape="box", style="filled")

        # Add module nodes
        for module_name, module in self.modules.items():
            # Color based on complexity
            color = self._get_complexity_color(module.complexity)
            label = f"{module_name}\\n({module.function_count} funcs)"

            dot.node(
                module_name,
                label=label,
                fillcolor=color,
                fontcolor="white" if module.complexity > 50 else "black"
            )

        # Add dependency edges
        for module_name, module in self.modules.items():
            for imported in module.imports:
                # Only show internal dependencies
                if imported in self.modules:
                    dot.edge(module_name, imported)

        # Render
        output_file = dot.render(output_path, format=format, cleanup=True)
        return output_file

    def generate_call_graph(
        self,
        output_path: str,
        format: str = "svg",
        max_depth: int = 3
    ) -> str:
        """
        Generate function call graph.

        Args:
            output_path: Output file path (without extension)
            format: Output format (svg, png, pdf)
            max_depth: Maximum call depth to show

        Returns:
            Path to generated file
        """
        if not GRAPHVIZ_AVAILABLE:
            raise RuntimeError("graphviz package is required for visualization")

        dot = graphviz.Digraph(comment="Function Call Graph")
        dot.attr(rankdir="TB")
        dot.attr("node", shape="ellipse", style="filled")

        # Find entry points (functions not called by others)
        entry_points = [
            func for func in self.functions.values()
            if not func.called_by
        ]

        # Build graph from entry points
        visited = set()
        for entry in entry_points[:10]:  # Limit to 10 entry points
            self._add_call_subgraph(dot, entry, visited, 0, max_depth)

        # Render
        output_file = dot.render(output_path, format=format, cleanup=True)
        return output_file

    def _add_call_subgraph(
        self,
        dot: Any,
        func: FunctionNode,
        visited: Set[str],
        depth: int,
        max_depth: int
    ):
        """Recursively add function calls to graph."""
        if depth > max_depth or func.name in visited:
            return

        visited.add(func.name)

        # Add node
        color = self._get_complexity_color(func.complexity)
        label = f"{func.name.split('.')[-1]}\\n({func.complexity})"

        dot.node(
            func.name,
            label=label,
            fillcolor=color,
            fontcolor="white" if func.complexity > 10 else "black"
        )

        # Add edges to called functions
        for call in func.calls:
            for target_name, target in self.functions.items():
                if target_name.endswith(f".{call}"):
                    dot.edge(func.name, target_name)
                    self._add_call_subgraph(dot, target, visited, depth + 1, max_depth)

    def _get_complexity_color(self, complexity: int) -> str:
        """Get color based on complexity value."""
        if complexity <= 5:
            return "#90EE90"  # Light green
        elif complexity <= 10:
            return "#FFD700"  # Gold
        elif complexity <= 20:
            return "#FFA500"  # Orange
        else:
            return "#FF4500"  # Red-orange

    def generate_json_report(self, output_path: str):
        """
        Generate JSON report of complexity data.

        Args:
            output_path: Output file path
        """
        report = {
            "modules": [
                {
                    "name": m.name,
                    "path": m.path,
                    "complexity": m.complexity,
                    "function_count": m.function_count,
                    "imports": m.imports,
                }
                for m in self.modules.values()
            ],
            "functions": [
                {
                    "name": f.name,
                    "module": f.module,
                    "complexity": f.complexity,
                    "line_number": f.line_number,
                    "calls": f.calls,
                    "called_by": f.called_by,
                }
                for f in self.functions.values()
            ],
            "summary": {
                "total_modules": len(self.modules),
                "total_functions": len(self.functions),
                "average_complexity": sum(f.complexity for f in self.functions.values()) / len(self.functions) if self.functions else 0,
                "max_complexity": max((f.complexity for f in self.functions.values()), default=0),
            }
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

    def get_most_complex_functions(self, limit: int = 10) -> List[FunctionNode]:
        """
        Get most complex functions.

        Args:
            limit: Maximum number of functions to return

        Returns:
            List of most complex functions
        """
        return sorted(
            self.functions.values(),
            key=lambda f: f.complexity,
            reverse=True
        )[:limit]

    def get_most_complex_modules(self, limit: int = 10) -> List[ModuleNode]:
        """
        Get most complex modules.

        Args:
            limit: Maximum number of modules to return

        Returns:
            List of most complex modules
        """
        return sorted(
            self.modules.values(),
            key=lambda m: m.complexity,
            reverse=True
        )[:limit]

    def get_hotspots(self, complexity_threshold: int = 10) -> List[FunctionNode]:
        """
        Get complexity hotspots (high complexity + many callers).

        Args:
            complexity_threshold: Minimum complexity to consider

        Returns:
            List of hotspot functions
        """
        hotspots = [
            func for func in self.functions.values()
            if func.complexity >= complexity_threshold and len(func.called_by) > 0
        ]

        return sorted(
            hotspots,
            key=lambda f: f.complexity * len(f.called_by),
            reverse=True
        )


# Global visualizer instance
_visualizer: Optional[ComplexityVisualizer] = None


def get_complexity_visualizer(project_root: Optional[str] = None) -> ComplexityVisualizer:
    """
    Get global complexity visualizer instance.

    Args:
        project_root: Project root directory (required on first call)

    Returns:
        Complexity visualizer instance
    """
    global _visualizer

    if _visualizer is None:
        if project_root is None:
            project_root = os.getcwd()
        _visualizer = ComplexityVisualizer(project_root)

    return _visualizer


def configure_complexity_visualizer(project_root: str):
    """
    Configure global complexity visualizer.

    Args:
        project_root: Project root directory
    """
    global _visualizer
    _visualizer = ComplexityVisualizer(project_root)
