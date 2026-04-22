# Code Search and Navigation

Powerful code search and navigation features for exploring codebases.

## Features

- **Full-Text Search**: Search for any text in your codebase
- **Regex Search**: Use regular expressions for advanced patterns
- **Symbol Search**: Find classes, functions, methods, variables
- **Go to Definition**: Jump to symbol definitions
- **Find References**: Find all usages of a symbol
- **File Outline**: View structure of a file
- **Workspace Symbols**: Browse all symbols in workspace
- **Fuzzy Matching**: Find symbols with similar names

## Usage

### Indexing Codebase

```python
from pr_agent.code_search import get_search_engine

# Create search engine
engine = get_search_engine("/path/to/project")

# Index directory
engine.index_directory(
    extensions=[".py"],
    exclude_patterns=["test", "__pycache__", ".git"]
)
```

### Full-Text Search

```python
# Simple search
results = engine.search_full_text("hello world")

# Case-sensitive search
results = engine.search_full_text("HelloWorld", case_sensitive=True)

# Whole word search
results = engine.search_full_text("test", whole_word=True)

# Limit results
results = engine.search_full_text("function", max_results=50)

for result in results:
    print(f"{result.file_path}:{result.line_number} - {result.match_text}")
```

### Regex Search

```python
# Find all function definitions
results = engine.search_regex(r"def \w+\(")

# Find all class definitions
results = engine.search_regex(r"class \w+:")

# Find TODO comments
results = engine.search_regex(r"# TODO:.*")
```

### Symbol Search

```python
from pr_agent.code_search import SymbolType

# Find specific symbol
symbols = engine.search_symbol("MyClass")

# Find by type
symbols = engine.search_symbol(
    "test_function",
    symbol_type=SymbolType.FUNCTION
)

# Fuzzy search
symbols = engine.search_symbol("test", fuzzy=True)

for symbol in symbols:
    print(f"{symbol.name} ({symbol.type.value}) at {symbol.file_path}:{symbol.line_number}")
```

### Navigation

```python
from pr_agent.code_search import get_code_navigator

navigator = get_code_navigator()

# Go to definition
symbol = navigator.go_to_definition("MyClass", "file.py", 10)
if symbol:
    print(f"Definition at {symbol.file_path}:{symbol.line_number}")

# Find all references
references = navigator.find_all_references("MyClass")
print(f"Found {len(references)} references")

# Get file outline
outline = navigator.get_file_outline("module.py")
print(f"Classes: {len(outline['classes'])}")
print(f"Functions: {len(outline['functions'])}")

# Get workspace symbols
symbols = navigator.get_workspace_symbols()
print(f"Total classes: {len(symbols['classes'])}")
print(f"Total functions: {len(symbols['functions'])}")
```

### Similar Symbols

```python
# Find symbols with similar names
similar = navigator.find_similar_symbols("TestCase", limit=10)

for symbol in similar:
    print(f"{symbol.name} - {symbol.file_path}")
```

## REST API

### Index Codebase

```bash
POST /api/code-search/index
Content-Type: application/json

{
  "directory": "/path/to/project",
  "extensions": [".py"],
  "exclude_patterns": ["test", "__pycache__"]
}
```

Response:
```json
{
  "status": "indexed",
  "total_files": 150,
  "total_symbols": 1250
}
```

### Search Code

```bash
POST /api/code-search/search
Content-Type: application/json

{
  "query": "hello world",
  "search_type": "full_text",
  "case_sensitive": false,
  "whole_word": false,
  "max_results": 100
}
```

Response:
```json
{
  "query": "hello world",
  "search_type": "full_text",
  "result_count": 5,
  "results": [
    {
      "file_path": "/path/to/file.py",
      "line_number": 10,
      "column": 5,
      "match_text": "hello world",
      "context_before": "def test():",
      "context_after": "    return True"
    }
  ]
}
```

### Search Symbols

```bash
POST /api/code-search/symbols
Content-Type: application/json

{
  "symbol_name": "MyClass",
  "symbol_type": "class",
  "fuzzy": false
}
```

Response:
```json
{
  "symbol_name": "MyClass",
  "result_count": 1,
  "symbols": [
    {
      "name": "MyClass",
      "type": "class",
      "file_path": "/path/to/file.py",
      "line_number": 5,
      "column": 0,
      "scope": "<module>",
      "signature": "class MyClass",
      "docstring": "My class documentation"
    }
  ]
}
```

### Find Definition

```bash
POST /api/code-search/definition
Content-Type: application/json

{
  "symbol_name": "MyClass",
  "file_path": "/path/to/file.py",
  "line_number": 10
}
```

Response:
```json
{
  "found": true,
  "symbol": {
    "name": "MyClass",
    "type": "class",
    "file_path": "/path/to/file.py",
    "line_number": 5,
    "column": 0
  }
}
```

### Find References

```bash
POST /api/code-search/references
Content-Type: application/json

{
  "symbol_name": "MyClass"
}
```

Response:
```json
{
  "symbol_name": "MyClass",
  "reference_count": 10,
  "references": [
    {
      "file_path": "/path/to/file.py",
      "line_number": 15,
      "column": 10,
      "match_text": "MyClass"
    }
  ]
}
```

### Get File Outline

```bash
GET /api/code-search/outline/path/to/file.py
```

Response:
```json
{
  "file_path": "/path/to/file.py",
  "outline": {
    "classes": [...],
    "functions": [...],
    "methods": [...],
    "variables": [...],
    "constants": [...],
    "imports": [...]
  }
}
```

### Get Workspace Symbols

```bash
GET /api/code-search/workspace-symbols
```

Response:
```json
{
  "symbols": {
    "classes": [...],
    "functions": [...],
    "methods": [...],
    "variables": [...],
    "constants": [...]
  },
  "total_count": 1250
}
```

## Symbol Types

- `CLASS`: Class definitions
- `FUNCTION`: Function definitions
- `METHOD`: Class methods
- `VARIABLE`: Variables
- `CONSTANT`: Constants (uppercase names)
- `IMPORT`: Import statements

## Search Types

- `full_text`: Full-text search
- `regex`: Regular expression search
- `symbol`: Symbol name search

## Best Practices

1. **Index Before Search**: Always index the codebase before searching
2. **Use Appropriate Search Type**: Choose the right search type for your needs
3. **Limit Results**: Use max_results to avoid overwhelming results
4. **Fuzzy Search**: Use fuzzy matching when you're not sure of exact names
5. **Cache Results**: Search engine caches file contents for fast searches

## Examples

### Example 1: Find All TODO Comments

```python
engine = get_search_engine("./src")
engine.index_directory()

todos = engine.search_regex(r"# TODO:.*")

print(f"Found {len(todos)} TODO comments:")
for todo in todos:
    print(f"  {todo.file_path}:{todo.line_number} - {todo.match_text}")
```

### Example 2: Find All Test Functions

```python
engine = get_search_engine("./tests")
engine.index_directory()

test_functions = engine.search_symbol("test", fuzzy=True)
test_functions = [s for s in test_functions if s.name.startswith("test_")]

print(f"Found {len(test_functions)} test functions")
```

### Example 3: Navigate to Definition

```python
navigator = get_code_navigator()

# User clicks on "MyClass" at line 50 in file.py
symbol = navigator.go_to_definition("MyClass", "file.py", 50)

if symbol:
    # Open editor at definition location
    print(f"Jump to {symbol.file_path}:{symbol.line_number}")
```

### Example 4: Find All Usages

```python
navigator = get_code_navigator()

# Find all places where "calculate_total" is used
references = navigator.find_all_references("calculate_total")

print(f"Found {len(references)} usages:")
for ref in references:
    print(f"  {ref.file_path}:{ref.line_number}")
```

## Performance Tips

- Index only necessary file types
- Use exclude patterns to skip large directories
- Limit max_results for faster searches
- Use whole_word for more precise matches
- Cache search engine instance for repeated searches

## Limitations

- Currently supports Python code only
- Large codebases may take time to index
- Dynamic code may not be fully indexed
- Regex search can be slow on large codebases

## Future Enhancements

- Support for JavaScript/TypeScript
- Support for Java
- Incremental indexing
- Search result ranking
- Code completion suggestions
- Semantic search using embeddings
