"""
Dependency graph visualization module.

Generates visual representations of code dependencies.
"""

from typing import Dict, List, Optional, TYPE_CHECKING
from pr_agent.dependency_graph.analyzer import (
    DependencyGraph,
    NodeType,
    EdgeType,
)

if TYPE_CHECKING:
    import graphviz


class DependencyGraphVisualizer:
    """Visualizes dependency graphs."""

    def __init__(self):
        self.graphviz_available = False
        try:
            import graphviz
            self.graphviz_available = True
        except ImportError:
            pass

    def generate_dot(
        self,
        graph: DependencyGraph,
        filter_types: Optional[List[NodeType]] = None,
        max_depth: Optional[int] = None,
    ) -> str:
        """Generate DOT format graph."""
        lines = ["digraph Dependencies {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box, style=rounded];')

        # Add nodes
        for node in graph.nodes.values():
            if filter_types and node.type not in filter_types:
                continue

            color = self._get_node_color(node.type)
            label = self._format_node_label(node)

            lines.append(
                f'  "{node.id}" [label="{label}", fillcolor="{color}", style="rounded,filled"];'
            )

        # Add edges
        for edge in graph.edges:
            if filter_types:
                source_node = graph.nodes.get(edge.source)
                target_node = graph.nodes.get(edge.target)
                if (
                    source_node and source_node.type not in filter_types
                ) or (
                    target_node and target_node.type not in filter_types
                ):
                    continue

            style = self._get_edge_style(edge.type)
            lines.append(f'  "{edge.source}" -> "{edge.target}" [{style}];')

        lines.append("}")
        return "\n".join(lines)

    def generate_svg(
        self,
        graph: DependencyGraph,
        filter_types: Optional[List[NodeType]] = None,
    ) -> str:
        """Generate SVG visualization."""
        if not self.graphviz_available:
            return self._generate_svg_fallback(graph, filter_types)

        import graphviz

        dot_source = self.generate_dot(graph, filter_types)
        try:
            graph_viz = graphviz.Source(dot_source)
            return graph_viz.pipe(format="svg").decode("utf-8")
        except Exception:
            return self._generate_svg_fallback(graph, filter_types)

    def _generate_svg_fallback(
        self,
        graph: DependencyGraph,
        filter_types: Optional[List[NodeType]] = None,
    ) -> str:
        """Generate simple SVG without graphviz."""
        nodes = list(graph.nodes.values())
        if filter_types:
            nodes = [n for n in nodes if n.type in filter_types]

        width = 800
        height = max(600, len(nodes) * 40)

        svg_lines = [
            f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
            '<defs>',
            '<marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">',
            '<polygon points="0 0, 10 3.5, 0 7" fill="#666" />',
            '</marker>',
            '</defs>',
        ]

        # Draw nodes
        y_offset = 50
        node_positions = {}

        for i, node in enumerate(nodes):
            x = 100
            y = y_offset + i * 40

            node_positions[node.id] = (x, y)

            color = self._get_node_color(node.type)
            label = node.name

            svg_lines.append(
                f'<rect x="{x}" y="{y}" width="200" height="30" '
                f'fill="{color}" stroke="#333" rx="5" />'
            )
            svg_lines.append(
                f'<text x="{x + 10}" y="{y + 20}" font-family="Arial" '
                f'font-size="12" fill="#000">{label}</text>'
            )

        # Draw edges
        for edge in graph.edges:
            if edge.source in node_positions and edge.target in node_positions:
                x1, y1 = node_positions[edge.source]
                x2, y2 = node_positions[edge.target]

                svg_lines.append(
                    f'<line x1="{x1 + 200}" y1="{y1 + 15}" '
                    f'x2="{x2}" y2="{y2 + 15}" '
                    f'stroke="#666" stroke-width="2" marker-end="url(#arrowhead)" />'
                )

        svg_lines.append("</svg>")
        return "\n".join(svg_lines)

    def generate_module_graph(self, graph: DependencyGraph) -> str:
        """Generate module-level dependency graph."""
        return self.generate_svg(graph, filter_types=[NodeType.MODULE])

    def generate_class_graph(self, graph: DependencyGraph) -> str:
        """Generate class-level dependency graph."""
        return self.generate_svg(graph, filter_types=[NodeType.CLASS])

    def generate_function_graph(self, graph: DependencyGraph) -> str:
        """Generate function-level dependency graph."""
        return self.generate_svg(
            graph,
            filter_types=[NodeType.FUNCTION, NodeType.METHOD],
        )

    def _get_node_color(self, node_type: NodeType) -> str:
        """Get color for node type."""
        colors = {
            NodeType.MODULE: "#E3F2FD",
            NodeType.CLASS: "#FFF9C4",
            NodeType.FUNCTION: "#C8E6C9",
            NodeType.METHOD: "#B2DFDB",
            NodeType.VARIABLE: "#F8BBD0",
        }
        return colors.get(node_type, "#EEEEEE")

    def _get_edge_style(self, edge_type: EdgeType) -> str:
        """Get style for edge type."""
        styles = {
            EdgeType.IMPORTS: 'color="blue", style="solid"',
            EdgeType.INHERITS: 'color="red", style="dashed"',
            EdgeType.CALLS: 'color="green", style="solid"',
            EdgeType.USES: 'color="orange", style="dotted"',
            EdgeType.CONTAINS: 'color="purple", style="solid"',
        }
        return styles.get(edge_type, 'color="gray"')

    def _format_node_label(self, node) -> str:
        """Format node label."""
        label = node.name
        if len(label) > 30:
            label = label[:27] + "..."
        return label

    def generate_dependency_matrix(
        self,
        graph: DependencyGraph,
        node_ids: Optional[List[str]] = None,
    ) -> str:
        """Generate HTML dependency matrix."""
        if node_ids is None:
            node_ids = list(graph.nodes.keys())[:50]  # Limit to 50 nodes

        # Build adjacency matrix
        matrix = {}
        for source in node_ids:
            matrix[source] = {}
            for target in node_ids:
                matrix[source][target] = False

        for edge in graph.edges:
            if edge.source in node_ids and edge.target in node_ids:
                matrix[edge.source][edge.target] = True

        # Generate HTML
        html_lines = [
            '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">',
            '<tr><th></th>',
        ]

        # Header row
        for node_id in node_ids:
            node = graph.nodes.get(node_id)
            name = node.name if node else node_id
            html_lines.append(f'<th style="writing-mode: vertical-rl;">{name}</th>')
        html_lines.append('</tr>')

        # Data rows
        for source in node_ids:
            source_node = graph.nodes.get(source)
            source_name = source_node.name if source_node else source

            html_lines.append(f'<tr><th>{source_name}</th>')

            for target in node_ids:
                has_dep = matrix[source][target]
                color = "#90EE90" if has_dep else "#FFFFFF"
                symbol = "✓" if has_dep else ""
                html_lines.append(
                    f'<td style="background-color: {color}; text-align: center;">{symbol}</td>'
                )

            html_lines.append('</tr>')

        html_lines.append('</table>')
        return "\n".join(html_lines)


# Global instance
_visualizer: Optional[DependencyGraphVisualizer] = None


def get_dependency_visualizer() -> DependencyGraphVisualizer:
    """Get or create the global dependency visualizer."""
    global _visualizer
    if _visualizer is None:
        _visualizer = DependencyGraphVisualizer()
    return _visualizer
