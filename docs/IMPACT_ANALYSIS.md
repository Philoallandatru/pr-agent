# Code Change Impact Analysis

Analyze the impact of code changes on your codebase, including affected files, tests, and risk assessment.

## Features

- **Dependency Analysis**: Identify files that depend on changed code
- **Reverse Dependencies**: Find files that import changed modules
- **Test Impact**: Automatically identify affected test files
- **Risk Assessment**: Calculate risk scores based on change scope and complexity
- **Visualization**: Generate text and graph visualizations of impact
- **Multi-depth Analysis**: Trace dependencies up to configurable depth

## Usage

### Python API

```python
from pr_agent.impact import ImpactAnalyzer

# Create analyzer
analyzer = ImpactAnalyzer("/path/to/repo")

# Analyze changes
result = analyzer.analyze_changes(
    changed_files=["src/utils.py", "src/models.py"],
    include_tests=True,
    max_depth=3
)

# Access results
print(f"Risk Level: {result.risk_assessment.level}")
print(f"Impacted Files: {len(result.impacted_files)}")
print(f"Affected Tests: {len(result.affected_tests)}")

# Visualize impact
text_report = analyzer.visualize_impact(result, output_format="text")
print(text_report)

# Generate dependency graph
dot_graph = analyzer.visualize_impact(result, output_format="dot")
```

### REST API

#### Analyze Impact

```bash
POST /api/impact/analyze
```

**Request:**
```json
{
  "changed_files": ["src/utils.py", "src/models.py"],
  "repo_path": "/path/to/repo",
  "include_tests": true,
  "max_depth": 3
}
```

**Response:**
```json
{
  "analysis_time": "2024-01-15T10:30:00Z",
  "changes": [
    {
      "file_path": "src/utils.py",
      "change_type": "modified",
      "lines_added": 25,
      "lines_deleted": 10,
      "functions_changed": ["helper", "validator"],
      "classes_changed": []
    }
  ],
  "impacted_files": [
    {
      "file_path": "src/main.py",
      "impact_type": "direct",
      "distance": 1,
      "reason": "Imports src/utils.py"
    }
  ],
  "affected_tests": [
    "tests/test_utils.py",
    "tests/test_main.py"
  ],
  "risk_assessment": {
    "level": "medium",
    "score": 45.5,
    "factors": [
      "Multiple files changed",
      "Core utility file modified"
    ],
    "recommendations": [
      "Run full test suite",
      "Review dependent code carefully"
    ]
  },
  "dependency_graph": {
    "src/utils.py": ["src/config.py"],
    "src/models.py": ["src/utils.py"]
  },
  "metadata": {
    "total_changes": 2,
    "total_impacted": 5,
    "total_tests": 8,
    "max_depth": 3
  }
}
```

#### Visualize Impact

```bash
POST /api/impact/visualize?format=text
```

**Request:**
```json
{
  "changed_files": ["src/utils.py"],
  "repo_path": "/path/to/repo",
  "include_tests": true,
  "max_depth": 2
}
```

**Response:**
```json
{
  "format": "text",
  "content": "================================================================================\nCODE CHANGE IMPACT ANALYSIS\n..."
}
```

## Impact Analysis Components

### 1. File Changes

Each changed file is analyzed for:
- **Change Type**: Added, Modified, Deleted, or Renamed
- **Lines Changed**: Lines added and deleted
- **Definitions**: Functions and classes modified
- **Complexity**: Estimated complexity of changes

### 2. Impacted Files

Files affected by changes are categorized as:
- **Direct Impact**: Files that directly import changed modules
- **Indirect Impact**: Files affected through dependency chains
- **Distance**: Number of hops in dependency graph

### 3. Affected Tests

Test files are identified based on:
- Naming conventions (`test_*.py`, `*_test.py`)
- Import relationships with changed files
- Directory structure (`tests/` directory)

### 4. Risk Assessment

Risk is calculated based on:
- **Number of changes**: More changes = higher risk
- **File criticality**: Core files have higher impact
- **Dependency breadth**: More dependents = higher risk
- **Change complexity**: Complex changes increase risk

**Risk Levels:**
- **Low** (0-25): Routine changes, minimal impact
- **Medium** (26-50): Moderate impact, standard review
- **High** (51-75): Significant impact, careful review needed
- **Critical** (76-100): Major impact, extensive testing required

## Configuration

### Analysis Depth

Control how far to trace dependencies:

```python
# Shallow analysis (direct dependencies only)
result = analyzer.analyze_changes(changed_files, max_depth=1)

# Deep analysis (up to 5 levels)
result = analyzer.analyze_changes(changed_files, max_depth=5)
```

### Test Detection

Enable or disable test file detection:

```python
# Include test analysis
result = analyzer.analyze_changes(changed_files, include_tests=True)

# Skip test analysis
result = analyzer.analyze_changes(changed_files, include_tests=False)
```

## Visualization Formats

### Text Format

Human-readable report with sections:
- Summary statistics
- Risk assessment
- Changed files with details
- Impacted files by distance
- Affected tests

```python
text = analyzer.visualize_impact(result, output_format="text")
print(text)
```

### DOT Format

GraphViz graph for visual dependency analysis:

```python
dot = analyzer.visualize_impact(result, output_format="dot")

# Save to file
with open("impact.dot", "w") as f:
    f.write(dot)

# Generate image (requires graphviz)
# dot -Tpng impact.dot -o impact.png
```

## Use Cases

### Pre-Commit Analysis

Analyze impact before committing changes:

```python
import subprocess

# Get changed files from git
result = subprocess.run(
    ["git", "diff", "--name-only", "HEAD"],
    capture_output=True,
    text=True
)
changed_files = result.stdout.strip().split("\n")

# Analyze impact
analyzer = ImpactAnalyzer(".")
impact = analyzer.analyze_changes(changed_files)

# Check risk level
if impact.risk_assessment.level in ["high", "critical"]:
    print("⚠️  High-risk changes detected!")
    print(f"Affected files: {len(impact.impacted_files)}")
    print(f"Tests to run: {len(impact.affected_tests)}")
```

### Pull Request Review

Add impact analysis to PR descriptions:

```python
# Analyze PR changes
pr_files = get_pr_changed_files(pr_number)
impact = analyzer.analyze_changes(pr_files)

# Generate report
report = analyzer.visualize_impact(impact, output_format="text")

# Post as PR comment
post_pr_comment(pr_number, f"## Impact Analysis\n\n```\n{report}\n```")
```

### CI/CD Integration

Fail builds on high-risk changes without adequate testing:

```python
impact = analyzer.analyze_changes(changed_files)

# Check if high-risk changes have test coverage
if impact.risk_assessment.level in ["high", "critical"]:
    if len(impact.affected_tests) == 0:
        raise Exception("High-risk changes require test coverage!")
```

## Advanced Features

### Custom Risk Factors

Extend risk assessment with custom factors:

```python
# Core files that should trigger higher risk
CORE_FILES = ["src/auth.py", "src/database.py", "src/api.py"]

def custom_risk_assessment(result):
    base_risk = result.risk_assessment.score
    
    # Increase risk for core files
    for change in result.changes:
        if change.file_path in CORE_FILES:
            base_risk += 20
    
    return min(base_risk, 100)
```

### Dependency Filtering

Focus on specific types of dependencies:

```python
# Only analyze production code (exclude tests)
impacted = [
    f for f in result.impacted_files
    if not f.file_path.startswith("tests/")
]
```

### Change Categorization

Group changes by type or module:

```python
from collections import defaultdict

changes_by_module = defaultdict(list)
for change in result.changes:
    module = change.file_path.split("/")[0]
    changes_by_module[module].append(change)

for module, changes in changes_by_module.items():
    print(f"{module}: {len(changes)} files changed")
```

## Performance Considerations

- **Caching**: Dependency analysis results are cached per file
- **Lazy Loading**: Files are only parsed when needed
- **Depth Limiting**: Use appropriate `max_depth` to balance thoroughness and speed
- **Large Repos**: Consider analyzing only relevant subdirectories

## Troubleshooting

### Import Resolution Issues

If imports aren't being resolved correctly:

1. Ensure the repository root is correctly identified
2. Check for `__init__.py` files in packages
3. Verify Python path configuration

### Missing Dependencies

If some dependencies aren't detected:

1. Check for dynamic imports (`importlib`)
2. Verify relative import syntax
3. Ensure all Python files are valid syntax

### Performance Issues

If analysis is slow:

1. Reduce `max_depth` parameter
2. Limit scope to specific directories
3. Use caching for repeated analyses

## Examples

### Example 1: Simple Change Analysis

```python
from pr_agent.impact import ImpactAnalyzer

analyzer = ImpactAnalyzer(".")
result = analyzer.analyze_changes(["utils.py"])

print(f"Risk: {result.risk_assessment.level}")
print(f"Impacted: {len(result.impacted_files)} files")
```

### Example 2: Multi-File Analysis with Visualization

```python
analyzer = ImpactAnalyzer("/path/to/repo")
result = analyzer.analyze_changes(
    changed_files=["models.py", "views.py", "utils.py"],
    max_depth=2
)

# Generate text report
report = analyzer.visualize_impact(result, output_format="text")
with open("impact_report.txt", "w") as f:
    f.write(report)

# Generate dependency graph
graph = analyzer.visualize_impact(result, output_format="dot")
with open("impact_graph.dot", "w") as f:
    f.write(graph)
```

### Example 3: CI/CD Integration

```python
import sys
from pr_agent.impact import ImpactAnalyzer, RiskLevel

def check_pr_impact(changed_files):
    analyzer = ImpactAnalyzer(".")
    result = analyzer.analyze_changes(changed_files)
    
    # Print summary
    print(f"Changed: {len(result.changes)} files")
    print(f"Impacted: {len(result.impacted_files)} files")
    print(f"Tests: {len(result.affected_tests)} files")
    print(f"Risk: {result.risk_assessment.level}")
    
    # Fail on critical risk without tests
    if result.risk_assessment.level == RiskLevel.CRITICAL:
        if len(result.affected_tests) == 0:
            print("❌ Critical changes require test coverage!")
            sys.exit(1)
    
    print("✅ Impact analysis passed")

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        capture_output=True,
        text=True
    )
    changed = [f for f in result.stdout.split("\n") if f.endswith(".py")]
    check_pr_impact(changed)
```

## API Reference

### ImpactAnalyzer

Main class for impact analysis.

**Constructor:**
```python
ImpactAnalyzer(repo_path: str)
```

**Methods:**

- `analyze_changes(changed_files, include_tests=True, max_depth=3)`: Analyze impact
- `visualize_impact(result, output_format="text")`: Generate visualization

### Data Classes

**ImpactAnalysisResult:**
- `changes`: List of FileChange objects
- `impacted_files`: List of ImpactedFile objects
- `affected_tests`: List of test file paths
- `risk_assessment`: RiskAssessment object
- `dependency_graph`: Dict of file dependencies
- `analysis_time`: Timestamp of analysis
- `metadata`: Additional analysis metadata

**FileChange:**
- `file_path`: Path to changed file
- `change_type`: ChangeType enum (ADDED, MODIFIED, DELETED, RENAMED)
- `lines_added`: Number of lines added
- `lines_deleted`: Number of lines deleted
- `functions_changed`: List of modified functions
- `classes_changed`: List of modified classes

**ImpactedFile:**
- `file_path`: Path to impacted file
- `impact_type`: "direct" or "indirect"
- `distance`: Dependency distance from changed file
- `reason`: Explanation of impact

**RiskAssessment:**
- `level`: RiskLevel enum (LOW, MEDIUM, HIGH, CRITICAL)
- `score`: Numeric risk score (0-100)
- `factors`: List of risk factors
- `recommendations`: List of recommended actions

## See Also

- [Dependency Graph](DEPENDENCY_GRAPH.md)
- [Code Metrics](CODE_METRICS.md)
- [Workflow](WORKFLOW.md)
