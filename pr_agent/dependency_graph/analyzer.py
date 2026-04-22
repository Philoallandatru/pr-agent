"""
Dependency graph analyzer for code relationships.

Analyzes and visualizes dependencies between modules, classes, and functions.
"""

import ast
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import json


class NodeType(Enum):
    """Type of dependency node."""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"


class EdgeType(Enum):
    """Type of dependency edge."""
    IMPORTS = "imports"
    INHERITS = "inherits"
    CALLS = "calls"
    USES = "uses"
    CONTAINS = "contains"


@dataclass
class DependencyNode:
    """Represents a node in the dependency graph."""
    id: str
    name: str
    type: NodeType
    file_path: str
    line_number: int
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "metadata": self.metadata,
        }


@dataclass
class DependencyEdge:
    """Represents an edge in the dependency graph."""
    source: str
    target: str
    type: EdgeType
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "metadata": self.metadata,
        }


@dataclass
class DependencyGraph:
    """Complete dependency graph."""
    nodes: Dict[str, DependencyNode] = field(default_factory=dict)
    edges: List[DependencyEdge] = field(default_factory=list)

    def add_node(self, node: DependencyNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node

    def add_edge(self, edge: DependencyEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)

    def get_dependencies(self, node_id: str) -> List[str]:
        """Get all dependencies of a node."""
        return [
            edge.target
            for edge in self.edges
            if edge.source == node_id
        ]

    def get_dependents(self, node_id: str) -> List[str]:
        """Get all nodes that depend on this node."""
        return [
            edge.source
            for edge in self.edges
            if edge.target == node_id
        ]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


class PythonDependencyAnalyzer(ast.NodeVisitor):
    """Analyzes Python code to extract dependencies."""

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.graph = DependencyGraph()
        self.current_scope: List[str] = []
        self.imports: Dict[str, str] = {}  # alias -> full_name

    def analyze(self) -> DependencyGraph:
        """Analyze the source code and build dependency graph."""
        try:
            tree = ast.parse(self.source_code)
            self.visit(tree)
        except SyntaxError:
            pass
        return self.graph

    def _make_node_id(self, name: str) -> str:
        """Create a unique node ID."""
        scope = ".".join(self.current_scope)
        if scope:
            return f"{self.file_path}::{scope}.{name}"
        return f"{self.file_path}::{name}"

    def visit_Import(self, node: ast.Import) -> None:
        """Handle import statements."""
        for alias in node.names:
            module_name = alias.name
            import_name = alias.asname or alias.name

            self.imports[import_name] = module_name

            # Add module node
            node_id = f"module::{module_name}"
            dep_node = DependencyNode(
                id=node_id,
                name=module_name,
                type=NodeType.MODULE,
                file_path="<external>",
                line_number=node.lineno,
            )
            self.graph.add_node(dep_node)

            # Add import edge
            current_module = f"module::{self.file_path}"
            edge = DependencyEdge(
                source=current_module,
                target=node_id,
                type=EdgeType.IMPORTS,
            )
            self.graph.add_edge(edge)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle from...import statements."""
        module_name = node.module or ""

        for alias in node.names:
            import_name = alias.name
            full_name = f"{module_name}.{import_name}" if module_name else import_name
            alias_name = alias.asname or import_name

            self.imports[alias_name] = full_name

            # Add imported item node
            node_id = f"import::{full_name}"
            dep_node = DependencyNode(
                id=node_id,
                name=full_name,
                type=NodeType.FUNCTION,  # Could be class or function
                file_path="<external>",
                line_number=node.lineno,
            )
            self.graph.add_node(dep_node)

            # Add import edge
            current_module = f"module::{self.file_path}"
            edge = DependencyEdge(
                source=current_module,
                target=node_id,
                type=EdgeType.IMPORTS,
            )
            self.graph.add_edge(edge)

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Handle class definitions."""
        node_id = self._make_node_id(node.name)

        # Add class node
        class_node = DependencyNode(
            id=node_id,
            name=node.name,
            type=NodeType.CLASS,
            file_path=self.file_path,
            line_number=node.lineno,
            metadata={
                "bases": [self._get_name(base) for base in node.bases],
                "decorators": [self._get_name(dec) for dec in node.decorator_list],
            },
        )
        self.graph.add_node(class_node)

        # Add inheritance edges
        for base in node.bases:
            base_name = self._get_name(base)
            if base_name in self.imports:
                base_name = self.imports[base_name]

            base_id = f"class::{base_name}"
            edge = DependencyEdge(
                source=node_id,
                target=base_id,
                type=EdgeType.INHERITS,
            )
            self.graph.add_edge(edge)

        # Visit class body
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Handle function definitions."""
        node_id = self._make_node_id(node.name)

        # Determine if it's a method or function
        node_type = NodeType.METHOD if self.current_scope else NodeType.FUNCTION

        # Add function node
        func_node = DependencyNode(
            id=node_id,
            name=node.name,
            type=node_type,
            file_path=self.file_path,
            line_number=node.lineno,
            metadata={
                "args": [arg.arg for arg in node.args.args],
                "decorators": [self._get_name(dec) for dec in node.decorator_list],
            },
        )
        self.graph.add_node(func_node)

        # Visit function body
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_Call(self, node: ast.Call) -> None:
        """Handle function calls."""
        func_name = self._get_name(node.func)

        if func_name:
            # Resolve import aliases
            if func_name in self.imports:
                func_name = self.imports[func_name]

            # Create edge from current scope to called function
            if self.current_scope:
                source_id = self._make_node_id(self.current_scope[-1])
                target_id = f"function::{func_name}"

                edge = DependencyEdge(
                    source=source_id,
                    target=target_id,
                    type=EdgeType.CALLS,
                )
                self.graph.add_edge(edge)

        self.generic_visit(node)

    def _get_name(self, node: ast.AST) -> str:
        """Extract name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_name(node.value)
            return f"{value}.{node.attr}" if value else node.attr
        elif isinstance(node, ast.Call):
            return self._get_name(node.func)
        return ""


class DependencyGraphAnalyzer:
    """Main analyzer for building dependency graphs."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.graph = DependencyGraph()

    def analyze_directory(
        self,
        extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> DependencyGraph:
        """Analyze all files in a directory."""
        if extensions is None:
            extensions = [".py"]
        if exclude_patterns is None:
            exclude_patterns = ["__pycache__", ".git", "venv", "node_modules"]

        for file_path in self._find_files(extensions, exclude_patterns):
            self._analyze_file(file_path)

        return self.graph

    def analyze_file(self, file_path: str) -> DependencyGraph:
        """Analyze a single file."""
        self._analyze_file(file_path)
        return self.graph

    def _find_files(
        self,
        extensions: List[str],
        exclude_patterns: List[str],
    ) -> List[str]:
        """Find all files matching criteria."""
        files = []

        for ext in extensions:
            for file_path in self.root_path.rglob(f"*{ext}"):
                # Check exclusions
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                files.append(str(file_path))

        return files

    def _analyze_file(self, file_path: str) -> None:
        """Analyze a single file and merge into main graph."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            # Add module node
            module_id = f"module::{file_path}"
            module_node = DependencyNode(
                id=module_id,
                name=os.path.basename(file_path),
                type=NodeType.MODULE,
                file_path=file_path,
                line_number=1,
            )
            self.graph.add_node(module_node)

            # Analyze Python files
            if file_path.endswith(".py"):
                analyzer = PythonDependencyAnalyzer(file_path, source_code)
                file_graph = analyzer.analyze()

                # Merge graphs
                for node in file_graph.nodes.values():
                    self.graph.add_node(node)
                for edge in file_graph.edges:
                    self.graph.add_edge(edge)

        except Exception:
            pass

    def get_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies."""
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node_id: str, path: List[str]) -> None:
            visited.add(node_id)
            rec_stack.add(node_id)
            path.append(node_id)

            for dep in self.graph.get_dependencies(node_id):
                if dep not in visited:
                    dfs(dep, path.copy())
                elif dep in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    cycles.append(cycle)

            rec_stack.remove(node_id)

        for node_id in self.graph.nodes:
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    def get_dependency_depth(self, node_id: str) -> int:
        """Calculate maximum dependency depth."""
        visited = set()

        def dfs(current_id: str) -> int:
            if current_id in visited:
                return 0
            visited.add(current_id)

            deps = self.graph.get_dependencies(current_id)
            if not deps:
                return 0

            return 1 + max(dfs(dep) for dep in deps)

        return dfs(node_id)

    def get_most_depended_on(self, top_n: int = 10) -> List[Tuple[str, int]]:
        """Get nodes with most dependents."""
        dependents_count = {}

        for node_id in self.graph.nodes:
            dependents = self.graph.get_dependents(node_id)
            dependents_count[node_id] = len(dependents)

        sorted_nodes = sorted(
            dependents_count.items(),
            key=lambda x: x[1],
            reverse=True,
        )

        return sorted_nodes[:top_n]
