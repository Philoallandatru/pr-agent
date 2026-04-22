# Code Complexity Visualization

This document describes the code complexity visualization system in PR-Agent.

## Overview

The complexity visualization system provides visual representations of code complexity metrics, helping developers identify hotspots and understand code structure at a glance.

## Features

- **Complexity Analysis**: Calculate cyclomatic and cognitive complexity for functions and modules
- **Heatmap Generation**: Visual heatmaps showing complexity distribution
- **Call Graph**: Visualize function call relationships
- **Dependency Graph**: Show module dependencies
- **Hotspot Detection**: Identify high-complexity areas requiring attention
- **JSON Reports**: Export complexity data for further analysis

## Installation

The visualization features require additional dependencies:

```bash
pip install radon graphviz
```

Note: `graphviz` also requires the Graphviz system package to be installed.

## Usage

### Basic Analysis

```python
from pr_agent.visualization import get_complexity_visualizer

visualizer = get_complexity_visualizer()

# Analyze a project
visualizer.analyze_project("/path/to/source")

# Get most complex functions
complex_funcs = visualizer.get_most_complex_functions(limit=10)
for func in complex_funcs:
    print(f"{func.name}: complexity={func.cyclomatic_complexity}")

# Get hotspots (high complexity + high change frequency)
hotspots = visualizer.get_hotspots(threshold=10)
```

### Generate Visualizations

```python
# Generate complexity heatmap
heatmap_path = visualizer.generate_complexity_heatmap(
    source_dir="/path/to/source",
    output_path="complexity_heatmap.png"
)

# Generate call graph for a file
call_graph = visualizer.generate_call_graph(
    source_file="/path/to/file.py",
    output_path="call_graph.png",
    max_depth=3
)

# Generate dependency graph
dep_graph = visualizer.generate_dependency_graph(
    source_dir="/path/to/source",
    output_path="dependencies.png"
)
```

### Export Reports

```python
# Generate JSON report
report = visualizer.generate_json_report()
print(f"Total functions: {report['summary']['total_functions']}")
print(f"Average complexity: {report['summary']['average_complexity']:.2f}")
```

## API Endpoints

### Analyze Project

```http
POST /api/visualization/analyze
Content-Type: application/json

{
  "source_dir": "/path/to/source"
}
```

Response:
```json
{
  "total_functions": 150,
  "total_modules": 25,
  "average_complexity": 4.2,
  "max_complexity": 18
}
```

### Get Complex Functions

```http
GET /api/visualization/complex-functions?limit=10
```

Response:
```json
{
  "functions": [
    {
      "name": "process_data",
      "file": "processor.py",
      "line": 45,
      "cyclomatic_complexity": 18,
      "cognitive_complexity": 22
    }
  ]
}
```

### Get Hotspots

```http
GET /api/visualization/hotspots?threshold=10
```

Response:
```json
{
  "hotspots": [
    {
      "name": "legacy_handler",
      "file": "handlers.py",
      "complexity": 15,
      "change_frequency": 8
    }
  ]
}
```

### Generate Heatmap

```http
POST /api/visualization/heatmap
Content-Type: application/json

{
  "source_dir": "/path/to/source",
  "output_path": "heatmap.png"
}
```

Response:
```json
{
  "output_path": "heatmap.png",
  "generated_at": "2024-01-15T10:30:00Z"
}
```

### Generate Call Graph

```http
POST /api/visualization/call-graph
Content-Type: application/json

{
  "source_file": "/path/to/file.py",
  "output_path": "calls.png",
  "max_depth": 3
}
```

### Generate Dependency Graph

```http
POST /api/visualization/dependency-graph
Content-Type: application/json

{
  "source_dir": "/path/to/source",
  "output_path": "deps.png"
}
```

### Export JSON Report

```http
GET /api/visualization/report
```

Response:
```json
{
  "summary": {
    "total_functions": 150,
    "total_modules": 25,
    "average_complexity": 4.2,
    "max_complexity": 18
  },
  "functions": [...],
  "modules": [...]
}
```

## Complexity Metrics

### Cyclomatic Complexity

Measures the number of linearly independent paths through code:
- **1-5**: Simple, low risk
- **6-10**: Moderate complexity
- **11-20**: High complexity, consider refactoring
- **21+**: Very high complexity, refactor recommended

### Cognitive Complexity

Measures how difficult code is to understand:
- **0-5**: Easy to understand
- **6-10**: Moderate difficulty
- **11-20**: Difficult to understand
- **21+**: Very difficult, refactor recommended

## Color Coding

Visualizations use color coding to indicate complexity levels:
- **Green**: Low complexity (1-5)
- **Yellow**: Moderate complexity (6-10)
- **Orange**: High complexity (11-20)
- **Red**: Very high complexity (21+)

## Best Practices

1. **Regular Analysis**: Run complexity analysis regularly to track trends
2. **Set Thresholds**: Define acceptable complexity limits for your project
3. **Focus on Hotspots**: Prioritize refactoring high-complexity, frequently-changed code
4. **Use Visualizations**: Share heatmaps and graphs with the team for better understanding
5. **Track Progress**: Monitor complexity metrics over time to measure improvement

## Configuration

Configure complexity visualization in `configuration.toml`:

```toml
[visualization]
enabled = true
max_complexity_threshold = 10
cognitive_complexity_threshold = 15
heatmap_width = 1200
heatmap_height = 800
call_graph_max_depth = 3
```

## Integration with CI/CD

Add complexity checks to your CI pipeline:

```yaml
- name: Check Code Complexity
  run: |
    python -m pr_agent.cli.complexity check \
      --source-dir src \
      --max-complexity 10 \
      --fail-on-high-complexity
```

## Troubleshooting

### Graphviz Not Found

If you see "Graphviz not installed" errors:

```bash
# Ubuntu/Debian
sudo apt-get install graphviz

# macOS
brew install graphviz

# Windows
choco install graphviz
```

### Large Projects

For large projects, analysis may take time. Use filters:

```python
visualizer.analyze_project(
    source_dir="/path/to/source",
    exclude_patterns=["tests/*", "migrations/*"]
)
```

## Examples

### Identify Refactoring Candidates

```python
# Find functions that need refactoring
complex_funcs = visualizer.get_most_complex_functions(limit=20)
for func in complex_funcs:
    if func.cyclomatic_complexity > 15:
        print(f"Refactor: {func.file}:{func.line} - {func.name}")
```

### Track Complexity Trends

```python
# Compare complexity over time
report_v1 = visualizer.generate_json_report()
# ... make changes ...
visualizer.analyze_project("/path/to/source")
report_v2 = visualizer.generate_json_report()

avg_before = report_v1['summary']['average_complexity']
avg_after = report_v2['summary']['average_complexity']
print(f"Complexity change: {avg_after - avg_before:.2f}")
```

### Generate Team Report

```python
# Create comprehensive report for team review
visualizer.analyze_project("/path/to/source")
visualizer.generate_complexity_heatmap("reports/heatmap.png")
visualizer.generate_dependency_graph("reports/dependencies.png")
report = visualizer.generate_json_report()

# Save report
with open("reports/complexity_report.json", "w") as f:
    json.dump(report, f, indent=2)
```

## See Also

- [Quality Gate Documentation](QUALITY_GATE.md)
- [Code Suggestions Documentation](CODE_SUGGESTIONS.md)
- [Coverage Tracking Documentation](COVERAGE_TRACKING.md)
