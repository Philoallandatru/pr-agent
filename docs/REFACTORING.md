# Code Refactoring

Automated code refactoring tools for safe code transformations.

## Features

### Supported Refactorings

1. **Rename Symbol**
   - Rename classes, functions, variables across workspace
   - Scope restriction support
   - Validation for Python keywords and naming conventions

2. **Extract Method**
   - Extract code blocks into new methods
   - Automatic parameter detection
   - Return value analysis

3. **Inline Variable**
   - Replace variable uses with its value
   - Automatic definition removal
   - Safe inlining validation

## Usage

### Python API

```python
from pr_agent.refactoring import get_refactoring_engine

engine = get_refactoring_engine()

# Rename a symbol
result = engine.rename_symbol(
    workspace="/path/to/project",
    old_name="OldClass",
    new_name="NewClass",
    scope=None  # Optional: restrict to specific file
)

# Extract method
result = engine.extract_method(
    file_path="/path/to/file.py",
    start_line=10,
    end_line=15,
    method_name="extracted_method"
)

# Inline variable
result = engine.inline_variable(
    file_path="/path/to/file.py",
    variable_name="temp",
    line=5
)

# Apply refactoring
if result.success:
    engine.apply_refactoring(result)
```

### REST API

#### Rename Symbol

```bash
POST /api/refactoring/rename
Content-Type: application/json

{
  "workspace": "/path/to/project",
  "old_name": "OldClass",
  "new_name": "NewClass",
  "scope": null,
  "apply": false
}
```

Response:
```json
{
  "success": true,
  "refactoring_type": "rename_symbol",
  "affected_files": ["/path/to/file1.py", "/path/to/file2.py"],
  "edit_count": 5,
  "warnings": [],
  "severity": "safe",
  "preview": "Total edits: 5\n/path/to/file1.py:\n  Line 1: OldClass → NewClass",
  "applied": false
}
```

#### Extract Method

```bash
POST /api/refactoring/extract-method
Content-Type: application/json

{
  "file_path": "/path/to/file.py",
  "start_line": 10,
  "end_line": 15,
  "method_name": "extracted_method",
  "apply": false
}
```

#### Inline Variable

```bash
POST /api/refactoring/inline-variable
Content-Type: application/json

{
  "file_path": "/path/to/file.py",
  "variable_name": "temp",
  "line": 5,
  "apply": false
}
```

#### Preview Refactoring

```bash
POST /api/refactoring/preview
Content-Type: application/json

{
  "refactoring_type": "rename_symbol",
  "params": {
    "workspace": "/path/to/project",
    "old_name": "OldClass",
    "new_name": "NewClass"
  }
}
```

Response includes detailed edits:
```json
{
  "success": true,
  "refactoring_type": "rename_symbol",
  "affected_files": ["/path/to/file.py"],
  "edits": [
    {
      "file_path": "/path/to/file.py",
      "start_line": 1,
      "start_col": 6,
      "end_line": 1,
      "end_col": 14,
      "old_text": "OldClass",
      "new_text": "NewClass"
    }
  ],
  "warnings": [],
  "severity": "safe",
  "preview": "..."
}
```

## Refactoring Result

Each refactoring operation returns a `RefactoringResult`:

```python
@dataclass
class RefactoringResult:
    success: bool                    # Whether refactoring succeeded
    refactoring_type: RefactoringType  # Type of refactoring
    edits: List[RefactoringEdit]     # List of edits to apply
    affected_files: List[str]        # Files that will be modified
    warnings: List[str]              # Warnings about the refactoring
    severity: RefactoringSeverity    # Safety level
    preview: str                     # Human-readable preview
```

## Severity Levels

- **SAFE**: Refactoring is safe to apply
- **WARNING**: Refactoring may have side effects
- **UNSAFE**: Refactoring is not recommended

## Safety Features

### Validation

- Python keyword checking
- Identifier validation
- Scope analysis
- Conflict detection

### Preview Mode

Always preview refactorings before applying:

```python
# Get preview
result = engine.rename_symbol(workspace, "old", "new")
print(result.preview)

# Review warnings
if result.warnings:
    print("Warnings:", result.warnings)

# Check severity
if result.severity == RefactoringSeverity.SAFE:
    engine.apply_refactoring(result)
```

### Atomic Operations

Refactorings are applied atomically per file. If any file fails, others are not affected.

## Examples

### Example 1: Rename Class

Before:
```python
class OldClass:
    def method(self):
        pass

def use_class():
    obj = OldClass()
    return obj
```

After renaming `OldClass` to `NewClass`:
```python
class NewClass:
    def method(self):
        pass

def use_class():
    obj = NewClass()
    return obj
```

### Example 2: Extract Method

Before:
```python
def complex_function():
    x = 10
    y = 20
    result = x + y
    print(result)
    return result
```

After extracting lines 3-4 to `calculate_sum`:
```python
def calculate_sum(x, y):
    result = x + y
    return result

def complex_function():
    x = 10
    y = 20
    result = calculate_sum(x, y)
    print(result)
    return result
```

### Example 3: Inline Variable

Before:
```python
def test_function():
    temp = 42
    result = temp * 2
    return result
```

After inlining `temp`:
```python
def test_function():
    result = (42) * 2
    return result
```

## Best Practices

1. **Always Preview First**
   - Review the preview before applying
   - Check affected files and edit count
   - Read warnings carefully

2. **Use Version Control**
   - Commit before refactoring
   - Review diffs after applying
   - Easy rollback if needed

3. **Test After Refactoring**
   - Run tests to verify correctness
   - Check for runtime errors
   - Validate behavior unchanged

4. **Start Small**
   - Refactor one thing at a time
   - Use scope restrictions when possible
   - Build confidence gradually

5. **Handle Warnings**
   - Don't ignore warnings
   - Understand severity levels
   - Manual review for UNSAFE operations

## Limitations

- Python files only
- AST-based analysis (syntax must be valid)
- No cross-language refactoring
- Limited semantic analysis
- May miss dynamic references

## Integration

### With CI/CD

```yaml
# Example GitHub Actions workflow
- name: Preview Refactoring
  run: |
    curl -X POST http://localhost:8000/api/refactoring/preview \
      -H "Content-Type: application/json" \
      -d '{"refactoring_type": "rename_symbol", "params": {...}}'
```

### With IDE

The refactoring engine can be integrated with IDEs through the REST API or Python API.

## Troubleshooting

### Circular Import Errors

The refactoring engine uses standard `logging` to avoid circular imports with `pr_agent.log`.

### Invalid Syntax

Ensure all Python files have valid syntax before refactoring. The engine uses AST parsing which requires syntactically correct code.

### Large Workspaces

For large workspaces, use scope restrictions to limit the search space:

```python
result = engine.rename_symbol(
    workspace="/large/project",
    old_name="Symbol",
    new_name="NewSymbol",
    scope="/large/project/specific/module.py"
)
```

## API Reference

### RefactoringEngine

Main engine class coordinating all refactoring operations.

**Methods:**
- `rename_symbol(workspace, old_name, new_name, scope=None) -> RefactoringResult`
- `extract_method(file_path, start_line, end_line, method_name) -> RefactoringResult`
- `inline_variable(file_path, variable_name, line) -> RefactoringResult`
- `apply_refactoring(result) -> bool`

### RefactoringType

Enum of supported refactoring types:
- `RENAME_SYMBOL`
- `EXTRACT_METHOD`
- `INLINE_VARIABLE`
- `EXTRACT_VARIABLE`
- `MOVE_METHOD`
- `CHANGE_SIGNATURE`

### RefactoringSeverity

Safety levels:
- `SAFE`
- `WARNING`
- `UNSAFE`

## See Also

- [Code Search](CODE_SEARCH.md) - Find symbols before refactoring
- [Dependency Graph](DEPENDENCY_GRAPH.md) - Understand impact
- [AI Review](AI_REVIEW.md) - Validate refactored code
