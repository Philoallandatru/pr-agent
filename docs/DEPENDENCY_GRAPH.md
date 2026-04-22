# Dependency Graph Visualization

Analyze and visualize code dependencies across your codebase.

## Features

- **Multi-level Analysis**: Analyze dependencies at module, class, and function levels
- **Circular Dependency Detection**: Identify circular dependencies that can cause issues
- **Impact Analysis**: Understand the impact of changing a module
- **Multiple Visualizations**: Generate SVG, DOT, and HTML dependency matrices
- **Python Support**: Full support for Python code analysis

## Usage

### Analyzing Dependencies

```python
from pr_agent.dependency_graph import DependencyGraphAnalyzer

# Create analyzer
analyzer = DependencyGraphAnalyzer("/path/to/project")

# Analyze entire directory
graph = analyzer.analyze_directory()

# Analyze with filters
graph = analyzer.analyze_directory(
    extensions=[".py"],
    exclude_patterns=["test", "__pycache__"]
)

# Analyze single file
graph = analyzer.analyze_file("module.py")
```

### Detecting Circular Dependencies

```python
# Find circular dependencies
cycles = analyzer.get_circular_dependencies()

for cycle in cycles:
    print(f"Circular dependency: {' -> '.join(cycle)}")
```

### Impact Analysis

```python
# Calculate dependency depth
depth = analyzer.get_dependency_depth("module_id")
print(f"Dependency depth: {depth}")

# Find most depended on modules
top_modules = analyzer.get_most_depended_on(top_n=10)

for module_id, count in top_modules:
    print(f"{module_id}: {count} dependents")
```

### Visualization

```python
from pr_agent.dependency_graph import get_dependency_visualizer

visualizer = get_dependency_visualizer()

# Generate SVG visualization
svg = visualizer.generate_svg(graph)

# Generate module-level graph
module_svg = visualizer.generate_module_graph(graph)

# Generate class-level graph
class_svg = visualizer.generate_class_graph(graph)

# Generate function-level graph
function_svg = visualizer.generate_function_graph(graph)

# Generate dependency matrix
matrix_html = visualizer.generate_dependency_matrix(graph)
```

### DOT Format

```python
# Generate DOT format for Graphviz
dot = visualizer.generate_dot(graph)

# Filter by node types
from pr_agent.dependency_graph import NodeType

dot = visualizer.generate_dot(
    graph,
    filter_types=[NodeType.MODULE, NodeType.CLASS]
)
```

## REST API

### Analyze Dependencies

```bash
POST /api/dependency-graph/analyze
Content-Type: application/json

{
  "directory": "/path/to/project",
  "patterns": ["*.py"]
}
```

Response:
```json
{
  "nodes": ["module1", "module2"],
  "edges": [
    {"source": "module1", "target": "module2"}
  ],
  "node_count": 2,
  "edge_count": 1
}
```

### Generate Visualization

```bash
POST /api/dependency-graph/visualize
Content-Type: application/json

{
  "directory": "/path/to/project",
  "output_path": "/tmp/graph",
  "format": "svg",
  "layout": "dot",
  "patterns": ["*.py"]
}
```

### Detect Circular Dependencies

```bash
POST /api/dependency-graph/cycles
Content-Type: application/json

{
  "directory": "/path/to/project",
  "patterns": ["*.py"]
}
```

Response:
```json
{
  "cycles": [
    ["module1", "module2", "module1"]
  ],
  "cycle_count": 1,
  "has_cycles": true
}
```

### Impact Analysis

```bash
POST /api/dependency-graph/impact
Content-Type: application/json

{
  "directory": "/path/to/project",
  "module": "module1",
  "patterns": ["*.py"]
}
```

Response:
```json
{
  "module": "module1",
  "direct_dependents": ["module2", "module3"],
  "all_dependents": ["module2", "module3", "module4"],
  "impact_score": 3
}
```

## Graph Structure

### Node Types

- `MODULE`: Python module/file
- `CLASS`: Class definition
- `FUNCTION`: Function definition
- `METHOD`: Class method
- `VARIABLE`: Variable/constant

### Edge Types

- `IMPORTS`: Import relationship
- `INHERITS`: Class inheritance
- `CALLS`: Function call
- `USES`: Variable usage
- `CONTAINS`: Containment relationship

## Visualization Colors

- **Modules**: Light blue (#E3F2FD)
- **Classes**: Light yellow (#FFF9C4)
- **Functions**: Light green (#C8E6C9)
- **Methods**: Light teal (#B2DFDB)
- **Variables**: Light pink (#F8BBD0)

## Best Practices

1. **Regular Analysis**: Run dependency analysis regularly to catch issues early
2. **Monitor Cycles**: Keep track of circular dependencies and resolve them
3. **Impact Assessment**: Check impact before making changes to core modules
4. **Documentation**: Use visualizations to document architecture
5. **Code Reviews**: Include dependency graphs in code reviews

## Examples

### Example 1: Find Circular Dependencies

```python
analyzer = DependencyGraphAnalyzer("./src")
graph = analyzer.analyze_directory()
cycles = analyzer.get_circular_dependencies()

if cycles:
    print("⚠️  Circular dependencies detected:")
    for cycle in cycles:
        print(f"  {' -> '.join(cycle)}")
else:
    print("✓ No circular dependencies found")
```

### Example 2: Identify High-Impact Modules

```python
analyzer = DependencyGraphAnalyzer("./src")
graph = analyzer.analyze_directory()
top_modules = analyzer.get_most_depended_on(top_n=5)

print("Top 5 most depended on modules:")
for module_id, count in top_modules:
    node = graph.nodes[module_id]
    print(f"  {node.name}: {count} dependents")
```

### Example 3: Generate Architecture Diagram

```python
analyzer = DependencyGraphAnalyzer("./src")
graph = analyzer.analyze_directory()

visualizer = get_dependency_visualizer()

# Generate module-level architecture
svg = visualizer.generate_module_graph(graph)

with open("architecture.svg", "w") as f:
    f.write(svg)
```

## Limitations

- Currently supports Python code only
- Large codebases may take time to analyze
- Graphviz required for advanced visualizations (optional)
- Dynamic imports may not be detected

## Future Enhancements

- Support for JavaScript/TypeScript
- Support for Java
- Interactive web-based visualizations
- Dependency change tracking over time
- Integration with CI/CD pipelines
