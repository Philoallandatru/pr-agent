# Code Documentation Generation

Automatic documentation generation from source code with support for multiple languages and output formats.

## Features

- **Multi-Language Support**: Python (with more languages coming)
- **Multiple Output Formats**: Markdown, HTML, reStructuredText, JSON
- **AST-Based Extraction**: Accurate parsing of code structure
- **Type Annotations**: Extracts and documents type hints
- **Docstring Parsing**: Supports Google, NumPy, and Sphinx docstring styles
- **API Documentation**: Generates complete API reference documentation
- **Customizable Templates**: Flexible output formatting

## Quick Start

### Python API

```python
from pr_agent.documentation import get_doc_generator, DocLanguage, DocFormat

# Initialize generator
generator = get_doc_generator()

# Generate documentation
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs",
    language=DocLanguage.PYTHON,
    format=DocFormat.MARKDOWN
)

if result.success:
    print(f"Generated docs at: {result.output_path}")
    print(f"Processed {len(result.modules)} modules")
else:
    print(f"Errors: {result.errors}")
```

### Extract Module Documentation

```python
from pr_agent.documentation.generator import PythonDocExtractor

extractor = PythonDocExtractor()
module_doc = extractor.extract_module("path/to/file.py")

print(f"Module: {module_doc.name}")
print(f"Docstring: {module_doc.docstring}")

for cls in module_doc.classes:
    print(f"  Class: {cls.name}")
    for method in cls.methods:
        print(f"    Method: {method.name}{method.signature}")
```

## REST API

### Generate Documentation

```bash
POST /api/docs/generate
Content-Type: application/json
Authorization: Bearer <token>

{
  "source_dir": "./src",
  "output_dir": "./docs",
  "language": "python",
  "format": "markdown",
  "patterns": ["*.py"]
}
```

Response:
```json
{
  "success": true,
  "output_path": "./docs/index.md",
  "modules_count": 42,
  "errors": [],
  "warnings": []
}
```

### Extract Documentation from Code

```bash
POST /api/docs/extract
Content-Type: application/json
Authorization: Bearer <token>

{
  "code": "def hello(name: str) -> str:\n    \"\"\"Say hello.\"\"\"\n    return f\"Hello {name}\"",
  "language": "python"
}
```

Response:
```json
{
  "name": "<module>",
  "docstring": "",
  "classes": [],
  "functions": [
    {
      "name": "hello",
      "docstring": "Say hello.",
      "signature": "(name: str) -> str",
      "parameters": ["name: str"],
      "return_type": "str"
    }
  ]
}
```

### Get Available Formats

```bash
GET /api/docs/formats
Authorization: Bearer <token>
```

Response:
```json
{
  "formats": ["markdown", "html", "rst", "json"],
  "languages": ["python", "javascript", "typescript", "java", "go"]
}
```

## Supported Languages

### Python
- Full AST-based parsing
- Type annotations extraction
- Docstring parsing (Google, NumPy, Sphinx styles)
- Class and function documentation
- Module-level documentation
- Import tracking
- Constant extraction

### Coming Soon
- JavaScript/TypeScript
- Java
- Go
- Rust

## Output Formats

### Markdown
Human-readable documentation with proper formatting:
```markdown
# Module: my_module

Module description here.

## Classes

### MyClass

Class description.

#### Methods

##### my_method(arg1: str, arg2: int) -> bool

Method description.

**Parameters:**
- arg1 (str): First argument
- arg2 (int): Second argument

**Returns:**
- bool: Success status
```

### HTML
Styled HTML documentation with navigation:
```html
<!DOCTYPE html>
<html>
<head>
    <title>API Documentation</title>
    <style>/* ... */</style>
</head>
<body>
    <h1>Module: my_module</h1>
    <!-- ... -->
</body>
</html>
```

### reStructuredText
Sphinx-compatible documentation:
```rst
my_module
=========

Module description here.

Classes
-------

MyClass
~~~~~~~

Class description.

.. py:method:: my_method(arg1: str, arg2: int) -> bool

   Method description.

   :param arg1: First argument
   :type arg1: str
   :param arg2: Second argument
   :type arg2: int
   :return: Success status
   :rtype: bool
```

### JSON
Machine-readable structured data:
```json
{
  "modules": [
    {
      "name": "my_module",
      "docstring": "Module description",
      "classes": [
        {
          "name": "MyClass",
          "docstring": "Class description",
          "methods": [
            {
              "name": "my_method",
              "signature": "(arg1: str, arg2: int) -> bool",
              "docstring": "Method description",
              "parameters": ["arg1: str", "arg2: int"],
              "return_type": "bool"
            }
          ]
        }
      ]
    }
  ]
}
```

## Configuration

### File Patterns

Specify which files to include:
```python
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs",
    patterns=["*.py", "!*_test.py", "!*/tests/*"]
)
```

### Custom Output

Control the output structure:
```python
# Single file output
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs/api.md",
    format=DocFormat.MARKDOWN
)

# Directory output (one file per module)
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs/",
    format=DocFormat.HTML
)
```

## Advanced Usage

### Extract Specific Elements

```python
from pr_agent.documentation.generator import PythonDocExtractor

extractor = PythonDocExtractor()

# Extract only classes
module_doc = extractor.extract_module("file.py")
for cls in module_doc.classes:
    print(f"{cls.name}: {cls.docstring}")

# Extract only functions
for func in module_doc.functions:
    print(f"{func.name}{func.signature}")

# Get imports
for imp in module_doc.imports:
    print(f"import {imp}")

# Get constants
for const in module_doc.constants:
    print(f"{const['name']} = {const['value']}")
```

### Handle Syntax Errors

```python
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs"
)

if not result.success:
    for error in result.errors:
        print(f"Error: {error}")
    
for warning in result.warnings:
    print(f"Warning: {warning}")
```

## Best Practices

1. **Write Good Docstrings**: The quality of generated documentation depends on your docstrings
2. **Use Type Annotations**: Type hints are automatically extracted and documented
3. **Follow Conventions**: Use standard docstring formats (Google, NumPy, Sphinx)
4. **Keep It Updated**: Regenerate documentation after code changes
5. **Review Output**: Check generated docs for accuracy and completeness

## Examples

### Complete Project Documentation

```python
from pr_agent.documentation import get_doc_generator, DocFormat

generator = get_doc_generator()

# Generate Markdown docs
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs/api.md",
    format=DocFormat.MARKDOWN
)

# Generate HTML docs
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs/html",
    format=DocFormat.HTML
)

# Generate Sphinx-compatible RST
result = generator.generate_docs(
    source_dir="./src",
    output_dir="./docs/sphinx",
    format=DocFormat.RST
)
```

### API Reference Generation

```python
# Generate JSON API reference
result = generator.generate_docs(
    source_dir="./src/api",
    output_dir="./docs/api.json",
    format=DocFormat.JSON,
    patterns=["*.py", "!*_internal.py"]
)

# Load and use the JSON
import json
with open("./docs/api.json") as f:
    api_docs = json.load(f)
    
for module in api_docs["modules"]:
    print(f"Module: {module['name']}")
    for func in module["functions"]:
        print(f"  - {func['name']}{func['signature']}")
```

## Troubleshooting

### No Files Found
```
Error: No python files found in ./src
```
- Check that the source directory exists
- Verify file patterns match your files
- Ensure files have correct extensions

### Syntax Errors
```
Warning: Failed to parse file.py: invalid syntax
```
- Fix syntax errors in source files
- Check Python version compatibility
- Review error messages for details

### Missing Docstrings
```
Warning: Function 'my_func' has no docstring
```
- Add docstrings to undocumented code
- Use proper docstring format
- Include parameter and return descriptions

## See Also

- [Code Search](CODE_SEARCH.md) - Find code elements
- [Code Formatting](CODE_FORMATTING.md) - Format code
- [Code Templates](CODE_TEMPLATES.md) - Generate code from templates
