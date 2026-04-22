# Code Formatting and Beautification

Automated code formatting system with support for multiple languages and formatters.

## Features

### Supported Languages

- **Python**: Black formatter
- **JavaScript**: Prettier
- **TypeScript**: Prettier
- **JSON**: Prettier
- **YAML**: Prettier
- **Markdown**: Prettier
- **HTML**: Prettier
- **CSS**: Prettier
- **Go**: gofmt
- **Rust**: rustfmt

### Capabilities

- **Format Code**: Automatically format code according to language standards
- **Check Format**: Verify if code is properly formatted
- **Custom Configuration**: Configure line length, indentation, quotes, etc.
- **Multiple Formatters**: Support for different formatter tools per language
- **Batch Processing**: Format multiple files at once

## Installation

### Python (Black)

```bash
pip install black
```

### JavaScript/TypeScript (Prettier)

```bash
npm install -g prettier
```

### Go (gofmt)

Included with Go installation.

### Rust (rustfmt)

```bash
rustup component add rustfmt
```

## Usage

### Python API

#### Basic Formatting

```python
from pr_agent.formatting import get_formatter_manager, FormatterLanguage

# Get manager
manager = get_formatter_manager()

# Format Python code
code = "x=1+2"
result = manager.format(code, FormatterLanguage.PYTHON)

if result.success:
    print(result.formatted_code)  # "x = 1 + 2\n"
    print(f"Changes made: {result.changes_made}")
else:
    print(f"Error: {result.error}")
```

#### Custom Configuration

```python
from pr_agent.formatting import get_formatter_manager, FormatConfig, FormatterLanguage

# Create custom config
config = FormatConfig(
    line_length=100,
    indent_size=2,
    use_tabs=False,
    trailing_comma=True,
    quote_style="single"
)

# Get manager with config
manager = get_formatter_manager(config)

# Format code
code = 'const message = "hello";'
result = manager.format(code, FormatterLanguage.JAVASCRIPT)

print(result.formatted_code)  # Uses single quotes
```

#### Check Format

```python
from pr_agent.formatting import get_formatter_manager, FormatterLanguage

manager = get_formatter_manager()

# Check if code is formatted
code = "x = 1 + 2\n"
is_formatted = manager.check(code, FormatterLanguage.PYTHON)

if is_formatted:
    print("Code is properly formatted")
else:
    print("Code needs formatting")
```

#### Format Files

```python
from pathlib import Path
from pr_agent.formatting import get_formatter_manager

manager = get_formatter_manager()

# Format single file
file_path = Path("src/main.py")
result = manager.format_file(file_path)

if result.success:
    # Write formatted code back
    file_path.write_text(result.formatted_code)

# Format multiple files
files = [
    Path("src/main.py"),
    Path("src/utils.py"),
    Path("src/config.py")
]

results = manager.format_multiple(files)

for file_path, result in results.items():
    if result.success and result.changes_made:
        print(f"Formatted: {file_path}")
        file_path.write_text(result.formatted_code)
```

#### Check Available Formatters

```python
from pr_agent.formatting import get_formatter_manager

manager = get_formatter_manager()

# Get available formatters
available = manager.get_available_formatters()

for language, is_available in available.items():
    status = "✓" if is_available else "✗"
    print(f"{status} {language.value}")
```

### REST API

#### Format Code

```bash
POST /api/format
Content-Type: application/json
Authorization: Bearer <token>

{
  "code": "x=1+2",
  "language": "python",
  "config": {
    "line_length": 100,
    "indent_size": 4
  }
}

Response:
{
  "success": true,
  "formatted_code": "x = 1 + 2\n",
  "changes_made": true,
  "error": null,
  "formatter": "black"
}
```

#### Check Format

```bash
POST /api/format/check
Content-Type: application/json
Authorization: Bearer <token>

{
  "code": "x = 1 + 2\n",
  "language": "python"
}

Response:
{
  "is_formatted": true,
  "language": "python"
}
```

#### Get Available Formatters

```bash
GET /api/format/available
Authorization: Bearer <token>

Response:
{
  "formatters": {
    "python": true,
    "javascript": true,
    "typescript": true,
    "json": true,
    "yaml": false,
    "markdown": true,
    "go": false,
    "rust": false,
    "html": true,
    "css": true
  }
}
```

## Configuration

### FormatConfig Options

```python
from pr_agent.formatting import FormatConfig

config = FormatConfig(
    line_length=88,        # Maximum line length
    indent_size=4,         # Number of spaces for indentation
    use_tabs=False,        # Use tabs instead of spaces
    trailing_comma=True,   # Add trailing commas
    quote_style="double",  # "single" or "double" quotes
    custom_options={}      # Formatter-specific options
)
```

### Language-Specific Configuration

#### Python (Black)

```python
config = FormatConfig(
    line_length=88,  # Black default
    custom_options={
        "skip_string_normalization": False,
        "skip_magic_trailing_comma": False
    }
)
```

#### JavaScript/TypeScript (Prettier)

```python
config = FormatConfig(
    line_length=80,      # Prettier default
    indent_size=2,       # Common for JS/TS
    quote_style="single",
    trailing_comma=True,
    custom_options={
        "semi": True,
        "arrow_parens": "always"
    }
)
```

## Examples

### Example 1: Format Python Module

```python
from pathlib import Path
from pr_agent.formatting import get_formatter_manager, FormatterLanguage

manager = get_formatter_manager()

# Read Python file
file_path = Path("my_module.py")
code = file_path.read_text()

# Format
result = manager.format(code, FormatterLanguage.PYTHON)

if result.success:
    if result.changes_made:
        # Write back formatted code
        file_path.write_text(result.formatted_code)
        print(f"Formatted {file_path}")
    else:
        print(f"{file_path} already formatted")
else:
    print(f"Error: {result.error}")
```

### Example 2: Format JavaScript Project

```python
from pathlib import Path
from pr_agent.formatting import get_formatter_manager, FormatConfig

# Custom config for JavaScript
config = FormatConfig(
    line_length=100,
    indent_size=2,
    quote_style="single",
    trailing_comma=True
)

manager = get_formatter_manager(config)

# Find all JS files
js_files = list(Path("src").rglob("*.js"))

# Format all files
results = manager.format_multiple(js_files)

formatted_count = sum(
    1 for r in results.values()
    if r.success and r.changes_made
)

print(f"Formatted {formatted_count}/{len(js_files)} files")
```

### Example 3: Pre-commit Hook

```python
#!/usr/bin/env python3
"""Pre-commit hook to format staged files."""

import subprocess
import sys
from pathlib import Path
from pr_agent.formatting import get_formatter_manager

def get_staged_files():
    """Get list of staged files."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True
    )
    return [Path(f) for f in result.stdout.strip().split("\n") if f]

def main():
    manager = get_formatter_manager()
    staged_files = get_staged_files()
    
    # Filter supported files
    supported_extensions = {".py", ".js", ".ts", ".json", ".md"}
    files_to_format = [
        f for f in staged_files
        if f.suffix in supported_extensions and f.exists()
    ]
    
    if not files_to_format:
        return 0
    
    # Format files
    results = manager.format_multiple(files_to_format)
    
    # Check for errors
    errors = [
        (f, r) for f, r in results.items()
        if not r.success
    ]
    
    if errors:
        print("Formatting errors:")
        for file_path, result in errors:
            print(f"  {file_path}: {result.error}")
        return 1
    
    # Write formatted files and re-stage
    for file_path, result in results.items():
        if result.changes_made:
            file_path.write_text(result.formatted_code)
            subprocess.run(["git", "add", str(file_path)])
            print(f"Formatted and re-staged: {file_path}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### Example 4: CI/CD Integration

```yaml
# .github/workflows/format-check.yml
name: Format Check

on: [pull_request]

jobs:
  format:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install black prettier
          npm install -g prettier
      
      - name: Check formatting
        run: |
          python -c "
          from pathlib import Path
          from pr_agent.formatting import get_formatter_manager
          
          manager = get_formatter_manager()
          
          # Check all Python files
          py_files = list(Path('src').rglob('*.py'))
          unformatted = []
          
          for f in py_files:
              if not manager.check_file(f):
                  unformatted.append(f)
          
          if unformatted:
              print('Unformatted files:')
              for f in unformatted:
                  print(f'  {f}')
              exit(1)
          "
```

## Formatter Details

### Black (Python)

- **Line Length**: 88 characters (default)
- **String Quotes**: Double quotes
- **Trailing Commas**: Added automatically
- **Magic Trailing Comma**: Respected

### Prettier (JavaScript/TypeScript/JSON/etc.)

- **Line Length**: 80 characters (default)
- **Indentation**: 2 spaces (default)
- **Semicolons**: Added automatically
- **Quotes**: Double quotes (configurable)
- **Trailing Commas**: ES5 compatible

### gofmt (Go)

- **Indentation**: Tabs
- **Formatting**: Go standard style
- **Simplification**: Automatic code simplification

### rustfmt (Rust)

- **Line Length**: 100 characters (default)
- **Indentation**: 4 spaces
- **Style**: Rust standard style

## Best Practices

1. **Format Before Commit**: Always format code before committing
2. **Use Pre-commit Hooks**: Automate formatting with git hooks
3. **CI/CD Checks**: Verify formatting in CI/CD pipeline
4. **Team Configuration**: Share formatter config across team
5. **Editor Integration**: Configure editor to format on save
6. **Consistent Style**: Use same formatter configuration project-wide

## Troubleshooting

### Formatter Not Available

If a formatter is not available:

```python
from pr_agent.formatting import get_formatter_manager

manager = get_formatter_manager()
available = manager.get_available_formatters()

# Check specific formatter
if not available[FormatterLanguage.PYTHON]:
    print("Black is not installed")
    print("Install with: pip install black")
```

### Formatting Timeout

If formatting times out (large files):

```python
# Formatters have 30-second timeout by default
# For large files, consider splitting or increasing timeout
```

### Custom Formatter Options

For formatter-specific options not in FormatConfig:

```python
config = FormatConfig(
    custom_options={
        "black_option": "value",
        "prettier_option": "value"
    }
)
```

## See Also

- [Code Templates](CODE_TEMPLATES.md) - Generate formatted code
- [Refactoring](REFACTORING.md) - Refactor and format code
- [Code Search](CODE_SEARCH.md) - Find code to format
