"""
Tests for dependency graph analyzer.
"""

import pytest
from pathlib import Path
from pr_agent.dependency_graph import (
    DependencyGraphAnalyzer,
    DependencyGraph,
    DependencyNode,
    DependencyEdge,
    NodeType,
    EdgeType,
)


class TestDependencyNode:
    """Test DependencyNode dataclass."""

    def test_node_creation(self):
        """Test creating a dependency node."""
        node = DependencyNode(
            id="test_id",
            name="test_module",
            type=NodeType.MODULE,
            file_path="/path/to/file.py",
            line_number=1,
            metadata={"key": "value"}
        )

        assert node.id == "test_id"
        assert node.name == "test_module"
        assert node.type == NodeType.MODULE
        assert node.file_path == "/path/to/file.py"
        assert node.line_number == 1
        assert node.metadata == {"key": "value"}

    def test_node_to_dict(self):
        """Test converting node to dictionary."""
        node = DependencyNode(
            id="test_id",
            name="test_module",
            type=NodeType.CLASS,
            file_path="/path/to/file.py",
            line_number=10
        )

        node_dict = node.to_dict()

        assert node_dict["id"] == "test_id"
        assert node_dict["name"] == "test_module"
        assert node_dict["type"] == "class"
        assert node_dict["file_path"] == "/path/to/file.py"
        assert node_dict["line_number"] == 10


class TestDependencyEdge:
    """Test DependencyEdge dataclass."""

    def test_edge_creation(self):
        """Test creating a dependency edge."""
        edge = DependencyEdge(
            source="node1",
            target="node2",
            type=EdgeType.IMPORTS,
            metadata={"weight": 1}
        )

        assert edge.source == "node1"
        assert edge.target == "node2"
        assert edge.type == EdgeType.IMPORTS
        assert edge.metadata == {"weight": 1}

    def test_edge_to_dict(self):
        """Test converting edge to dictionary."""
        edge = DependencyEdge(
            source="node1",
            target="node2",
            type=EdgeType.CALLS
        )

        edge_dict = edge.to_dict()

        assert edge_dict["source"] == "node1"
        assert edge_dict["target"] == "node2"
        assert edge_dict["type"] == "calls"


class TestDependencyGraph:
    """Test DependencyGraph."""

    def test_graph_creation(self):
        """Test creating an empty graph."""
        graph = DependencyGraph()

        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self):
        """Test adding nodes to graph."""
        graph = DependencyGraph()

        node1 = DependencyNode(
            id="node1",
            name="Module1",
            type=NodeType.MODULE,
            file_path="file1.py",
            line_number=1
        )
        node2 = DependencyNode(
            id="node2",
            name="Module2",
            type=NodeType.MODULE,
            file_path="file2.py",
            line_number=1
        )

        graph.add_node(node1)
        graph.add_node(node2)

        assert len(graph.nodes) == 2
        assert "node1" in graph.nodes
        assert "node2" in graph.nodes

    def test_add_edge(self):
        """Test adding edges to graph."""
        graph = DependencyGraph()

        edge = DependencyEdge(
            source="node1",
            target="node2",
            type=EdgeType.IMPORTS
        )

        graph.add_edge(edge)

        assert len(graph.edges) == 1
        assert graph.edges[0].source == "node1"
        assert graph.edges[0].target == "node2"

    def test_get_dependencies(self):
        """Test getting dependencies of a node."""
        graph = DependencyGraph()

        graph.add_edge(DependencyEdge("node1", "node2", EdgeType.IMPORTS))
        graph.add_edge(DependencyEdge("node1", "node3", EdgeType.IMPORTS))
        graph.add_edge(DependencyEdge("node2", "node3", EdgeType.IMPORTS))

        deps = graph.get_dependencies("node1")

        assert len(deps) == 2
        assert "node2" in deps
        assert "node3" in deps

    def test_get_dependents(self):
        """Test getting dependents of a node."""
        graph = DependencyGraph()

        graph.add_edge(DependencyEdge("node1", "node3", EdgeType.IMPORTS))
        graph.add_edge(DependencyEdge("node2", "node3", EdgeType.IMPORTS))

        dependents = graph.get_dependents("node3")

        assert len(dependents) == 2
        assert "node1" in dependents
        assert "node2" in dependents

    def test_to_dict(self):
        """Test converting graph to dictionary."""
        graph = DependencyGraph()

        node = DependencyNode(
            id="node1",
            name="Module1",
            type=NodeType.MODULE,
            file_path="file1.py",
            line_number=1
        )
        edge = DependencyEdge("node1", "node2", EdgeType.IMPORTS)

        graph.add_node(node)
        graph.add_edge(edge)

        graph_dict = graph.to_dict()

        assert "nodes" in graph_dict
        assert "edges" in graph_dict
        assert len(graph_dict["nodes"]) == 1
        assert len(graph_dict["edges"]) == 1

    def test_to_json(self):
        """Test converting graph to JSON."""
        graph = DependencyGraph()

        node = DependencyNode(
            id="node1",
            name="Module1",
            type=NodeType.MODULE,
            file_path="file1.py",
            line_number=1
        )

        graph.add_node(node)

        json_str = graph.to_json()

        assert isinstance(json_str, str)
        assert "node1" in json_str
        assert "Module1" in json_str


class TestPythonDependencyAnalyzer:
    """Test Python dependency analyzer."""

    def test_analyze_imports(self, tmp_path):
        """Test analyzing import statements."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
import os
import sys
from pathlib import Path
""")

        analyzer = DependencyGraphAnalyzer(str(tmp_path))
        graph = analyzer.analyze_file(str(test_file))

        # Should have module node and import edges
        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_analyze_class(self, tmp_path):
        """Test analyzing class definitions."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class MyClass:
    def method(self):
        pass
""")

        analyzer = DependencyGraphAnalyzer(str(tmp_path))
        graph = analyzer.analyze_file(str(test_file))

        # Should have class node
        class_nodes = [n for n in graph.nodes.values() if n.type == NodeType.CLASS]
        assert len(class_nodes) > 0
        assert any(n.name == "MyClass" for n in class_nodes)

    def test_analyze_function(self, tmp_path):
        """Test analyzing function definitions."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
def my_function():
    pass
""")

        analyzer = DependencyGraphAnalyzer(str(tmp_path))
        graph = analyzer.analyze_file(str(test_file))

        # Should have function node
        func_nodes = [n for n in graph.nodes.values() if n.type == NodeType.FUNCTION]
        assert len(func_nodes) > 0

    def test_analyze_inheritance(self, tmp_path):
        """Test analyzing class inheritance."""
        test_file = tmp_path / "test.py"
        test_file.write_text("""
class Base:
    pass

class Derived(Base):
    pass
""")

        analyzer = DependencyGraphAnalyzer(str(tmp_path))
        graph = analyzer.analyze_file(str(test_file))

        # Should have inheritance edge
        inherit_edges = [e for e in graph.edges if e.type == EdgeType.INHERITS]
        assert len(inherit_edges) > 0


class TestDependencyGraphAnalyzer:
    """Test DependencyGraphAnalyzer."""

    def test_analyzer_creation(self, tmp_path):
        """Test creating analyzer."""
        analyzer = DependencyGraphAnalyzer(str(tmp_path))

        assert analyzer.root_path == tmp_path
        assert isinstance(analyzer.graph, DependencyGraph)

    def test_analyze_directory(self, tmp_path):
        """Test analyzing a directory."""
        # Create test files
        (tmp_path / "file1.py").write_text("import os")
        (tmp_path / "file2.py").write_text("import sys")

        analyzer = DependencyGraphAnalyzer(str(tmp_path))
        graph = analyzer.analyze_directory()

        assert len(graph.nodes) > 0
        assert len(graph.edges) > 0

    def test_analyze_with_exclusions(self, tmp_path):
        """Test analyzing with exclusion patterns."""
        # Create test files
        (tmp_path / "file1.py").write_text("import os")
        test_dir = tmp_path / "test"
        test_dir.mkdir()
        (test_dir / "file2.py").write_text("import sys")

        analyzer = DependencyGraphAnalyzer(str(tmp_path))
        graph = analyzer.analyze_directory(exclude_patterns=["test"])

        # Should not include files in test directory
        test_files = [n for n in graph.nodes.values() if "test" in n.file_path]
        assert len(test_files) == 0

    def test_get_circular_dependencies(self, tmp_path):
        """Test detecting circular dependencies."""
        analyzer = DependencyGraphAnalyzer(str(tmp_path))

        # Create circular dependency
        analyzer.graph.add_node(DependencyNode("A", "A", NodeType.MODULE, "a.py", 1))
        analyzer.graph.add_node(DependencyNode("B", "B", NodeType.MODULE, "b.py", 1))
        analyzer.graph.add_node(DependencyNode("C", "C", NodeType.MODULE, "c.py", 1))

        analyzer.graph.add_edge(DependencyEdge("A", "B", EdgeType.IMPORTS))
        analyzer.graph.add_edge(DependencyEdge("B", "C", EdgeType.IMPORTS))
        analyzer.graph.add_edge(DependencyEdge("C", "A", EdgeType.IMPORTS))

        cycles = analyzer.get_circular_dependencies()

        assert len(cycles) > 0

    def test_get_dependency_depth(self, tmp_path):
        """Test calculating dependency depth."""
        analyzer = DependencyGraphAnalyzer(str(tmp_path))

        # Create dependency chain
        analyzer.graph.add_node(DependencyNode("A", "A", NodeType.MODULE, "a.py", 1))
        analyzer.graph.add_node(DependencyNode("B", "B", NodeType.MODULE, "b.py", 1))
        analyzer.graph.add_node(DependencyNode("C", "C", NodeType.MODULE, "c.py", 1))

        analyzer.graph.add_edge(DependencyEdge("A", "B", EdgeType.IMPORTS))
        analyzer.graph.add_edge(DependencyEdge("B", "C", EdgeType.IMPORTS))

        depth = analyzer.get_dependency_depth("A")

        assert depth == 2

    def test_get_most_depended_on(self, tmp_path):
        """Test finding most depended on modules."""
        analyzer = DependencyGraphAnalyzer(str(tmp_path))

        # Create nodes
        for i in range(5):
            analyzer.graph.add_node(
                DependencyNode(f"node{i}", f"Node{i}", NodeType.MODULE, f"file{i}.py", 1)
            )

        # Make node0 most depended on
        for i in range(1, 5):
            analyzer.graph.add_edge(DependencyEdge(f"node{i}", "node0", EdgeType.IMPORTS))

        most_depended = analyzer.get_most_depended_on(top_n=1)

        assert len(most_depended) == 1
        assert most_depended[0][0] == "node0"
        assert most_depended[0][1] == 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
