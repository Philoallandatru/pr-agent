# Code Templates and Snippets

Code template and snippet management system for rapid code generation.

## Features

### Template Engine

- **Variable Substitution**: `{{variable}}` syntax
- **Conditionals**: `{% if condition %}...{% endif %}`
- **Loops**: `{% for item in list %}...{% endfor %}`
- **Multi-language Support**: Python, JavaScript, TypeScript, Java, Go, Rust, C++, C#, Ruby, PHP

### Template Categories

- **Class**: Class definitions and structures
- **Function**: Function and method templates
- **Test**: Unit test templates
- **API**: REST API endpoint templates
- **Database**: Database query and model templates
- **UI**: User interface component templates
- **Utility**: Utility function templates
- **Boilerplate**: Project boilerplate templates
- **Pattern**: Design pattern implementations
- **Custom**: User-defined templates

### Built-in Templates

1. **Python Class**: Basic class with constructor and repr
2. **Python Function**: Function with docstring
3. **Python Test**: pytest test function (Arrange-Act-Assert)
4. **FastAPI Endpoint**: REST API endpoint with error handling

## Usage

### Python API

```python
from pr_agent.templates import get_template_manager, CodeTemplate, TemplateVariable, TemplateLanguage, TemplateCategory

# Get manager
manager = get_template_manager()

# List templates
templates = manager.list_templates(
    language=TemplateLanguage.PYTHON,
    category=TemplateCategory.FUNCTION
)

# Get specific template
template = manager.get_template("python-function")

# Instantiate template
instance = manager.instantiate_template(
    "python-function",
    {
        "function_name": "calculate_sum",
        "description": "Calculate sum of two numbers",
        "params": "a: int, b: int",
        "param_list": ["a", "b"],
        "return_type": "int",
        "return_description": "Sum of a and b",
        "has_implementation": True,
        "implementation": "return a + b"
    }
)

print(instance.content)
```

Output:
```python
def calculate_sum(a: int, b: int):
    """
    Calculate sum of two numbers

    Args:
        a: a description
        b: b description

    Returns:
        int: Sum of a and b
    """
    return a + b
```

### Creating Custom Templates

```python
from pr_agent.templates import CodeTemplate, TemplateVariable, TemplateLanguage, TemplateCategory

# Define template
template = CodeTemplate(
    id="my-custom-template",
    name="My Custom Template",
    description="A custom code template",
    language=TemplateLanguage.PYTHON,
    category=TemplateCategory.CUSTOM,
    content='''
class {{class_name}}:
    """{{description}}"""
    
    {% if has_init %}
    def __init__(self):
        """Initialize {{class_name}}."""
        pass
    {% endif %}
    
    {% for method in methods %}
    def {{method}}(self):
        """{{method}} method."""
        pass
    {% endfor %}
''',
    variables=[
        TemplateVariable("class_name", "Class name", required=True),
        TemplateVariable("description", "Class description", required=True),
        TemplateVariable("has_init", "Include __init__", default="true", type="boolean"),
        TemplateVariable("methods", "List of methods", default="[]", type="list"),
    ],
    tags=["python", "class", "custom"]
)

# Create template
manager = get_template_manager()
manager.create_template(template)

# Use template
instance = manager.instantiate_template(
    "my-custom-template",
    {
        "class_name": "MyClass",
        "description": "My custom class",
        "has_init": True,
        "methods": ["method1", "method2"]
    }
)
```

### Template Variables

Variables support different types:

- **string**: Text values (default)
- **number**: Numeric values
- **boolean**: True/False values
- **list**: Array of values

```python
TemplateVariable(
    name="port",
    description="Server port",
    default="8000",
    type="number",
    required=False
)

TemplateVariable(
    name="enable_auth",
    description="Enable authentication",
    default="false",
    type="boolean",
    required=False
)

TemplateVariable(
    name="methods",
    description="HTTP methods",
    default='["GET", "POST"]',
    type="list",
    choices=["GET", "POST", "PUT", "DELETE"]
)
```

### REST API

#### List Templates

```bash
GET /api/templates?language=python&category=function&tags=test

Response:
{
  "templates": [
    {
      "id": "python-test",
      "name": "Python Test Function",
      "description": "pytest test function template",
      "language": "python",
      "category": "test",
      "tags": ["python", "test", "pytest"],
      "author": "system",
      "usage_count": 42,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "total": 1
}
```

#### Get Template

```bash
GET /api/templates/python-function

Response:
{
  "id": "python-function",
  "name": "Python Function",
  "description": "Python function with docstring",
  "language": "python",
  "category": "function",
  "content": "def {{function_name}}({{params}}):\n    ...",
  "variables": [
    {
      "name": "function_name",
      "description": "Function name",
      "default": null,
      "required": true,
      "type": "string",
      "choices": null
    }
  ],
  "tags": ["python", "function"],
  "author": "system",
  "usage_count": 156,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

#### Create Template

```bash
POST /api/templates
Content-Type: application/json
Authorization: Bearer <token>

{
  "id": "custom-template",
  "name": "Custom Template",
  "description": "My custom template",
  "language": "python",
  "category": "custom",
  "content": "# {{comment}}",
  "variables": [
    {
      "name": "comment",
      "description": "Comment text",
      "required": true
    }
  ],
  "tags": ["custom"]
}

Response:
{
  "id": "custom-template",
  "message": "Template created successfully"
}
```

#### Update Template

```bash
PUT /api/templates/custom-template
Content-Type: application/json
Authorization: Bearer <token>

{
  "description": "Updated description",
  "content": "# Updated: {{comment}}"
}

Response:
{
  "id": "custom-template",
  "message": "Template updated successfully"
}
```

#### Delete Template

```bash
DELETE /api/templates/custom-template
Authorization: Bearer <token>

Response:
{
  "message": "Template deleted successfully"
}
```

#### Search Templates

```bash
POST /api/templates/search?query=python

Response:
{
  "results": [
    {
      "id": "python-class",
      "name": "Python Class",
      "description": "Basic Python class template",
      "language": "python",
      "category": "class",
      "tags": ["python", "class", "oop"],
      "usage_count": 89
    }
  ],
  "total": 1
}
```

#### Instantiate Template

```bash
POST /api/templates/python-function/instantiate
Content-Type: application/json
Authorization: Bearer <token>

{
  "function_name": "my_function",
  "description": "My function",
  "params": "",
  "param_list": [],
  "return_type": "None",
  "return_description": ""
}

Response:
{
  "template_id": "python-function",
  "content": "def my_function():\n    \"\"\"My function...",
  "variables": {...},
  "created_at": "2024-01-01T12:00:00"
}
```

#### Preview Template

```bash
POST /api/templates/python-function/preview
Content-Type: application/json
Authorization: Bearer <token>

{
  "function_name": "test_func",
  "description": "Test function",
  "params": "x: int",
  "param_list": ["x"],
  "return_type": "int",
  "return_description": "Result"
}

Response:
{
  "template_id": "python-function",
  "content": "def test_func(x: int):\n    ..."
}
```

## Template Syntax

### Variables

```
{{variable_name}}
```

Variables are replaced with their values. Missing variables show as `{{MISSING:variable_name}}`.

### Conditionals

```
{% if condition %}
  Content shown when condition is truthy
{% endif %}
```

Conditionals check if a variable is truthy (not None, False, 0, or empty).

### Loops

```
{% for item in list_variable %}
  {{item}} - process each item
{% endfor %}
```

Loops iterate over list variables. The loop variable is available inside the block.

### Example: Complex Template

```python
template_content = '''
class {{class_name}}:
    """{{description}}"""
    
    {% if has_constructor %}
    def __init__(self{% for param in params %}, {{param}}{% endfor %}):
        """Initialize {{class_name}}."""
        {% for param in params %}
        self.{{param}} = {{param}}
        {% endfor %}
    {% endif %}
    
    {% for method in methods %}
    def {{method}}(self):
        """{{method}} implementation."""
        pass
    {% endfor %}
    
    {% if has_repr %}
    def __repr__(self):
        return f"{{class_name}}({% for param in params %}{{param}}={{self.{{param}}}}{% endfor %})"
    {% endif %}
'''
```

## Import/Export

### Export Templates

```python
from pathlib import Path

manager = get_template_manager()
count = manager.export_templates(Path("templates.json"))
print(f"Exported {count} templates")
```

### Import Templates

```python
from pathlib import Path

manager = get_template_manager()
count = manager.import_templates(Path("templates.json"), overwrite=False)
print(f"Imported {count} templates")
```

## Storage

Templates are stored in `~/.pr_agent/templates/templates.json` by default.

Configure custom storage:

```python
from pathlib import Path
from pr_agent.templates import configure_template_manager

configure_template_manager(storage_dir=Path("/custom/path"))
```

## Best Practices

1. **Use Descriptive IDs**: Use kebab-case IDs like `python-async-function`
2. **Document Variables**: Provide clear descriptions for all variables
3. **Set Defaults**: Provide sensible defaults for optional variables
4. **Tag Appropriately**: Use tags for better searchability
5. **Test Templates**: Preview templates before using in production
6. **Version Control**: Export templates and commit to version control
7. **Share Templates**: Export and share useful templates with team

## Examples

### Example 1: REST API Endpoint

```python
instance = manager.instantiate_template(
    "fastapi-endpoint",
    {
        "method": "post",
        "path": "/api/users",
        "function_name": "create_user",
        "description": "Create a new user",
        "has_params": True,
        "params": "user: UserCreate",
        "param_list": ["user"],
        "return_type": "User",
        "return_description": "Created user",
        "implementation": "new_user = db.create_user(user)\nreturn new_user",
        "return_value": "new_user"
    }
)
```

### Example 2: Test Function

```python
instance = manager.instantiate_template(
    "python-test",
    {
        "test_name": "user_creation",
        "description": "user can be created successfully",
        "fixtures": "db_session",
        "arrange": "user_data = {'name': 'Alice', 'email': 'alice@example.com'}",
        "act": "user = create_user(db_session, user_data)",
        "assert_statement": "assert user.name == 'Alice'\nassert user.email == 'alice@example.com'"
    }
)
```

### Example 3: Class with Methods

```python
instance = manager.instantiate_template(
    "python-class",
    {
        "class_name": "UserRepository",
        "description": "Repository for user data access",
        "has_params": True,
        "params": "db_session",
        "param_list": ["db_session"]
    }
)
```

## Integration

### With IDE

Templates can be integrated with IDEs through the REST API or Python API.

### With CI/CD

```yaml
# Example: Generate code in CI
- name: Generate Code
  run: |
    python -c "
    from pr_agent.templates import get_template_manager
    manager = get_template_manager()
    instance = manager.instantiate_template('python-function', {...})
    with open('generated.py', 'w') as f:
        f.write(instance.content)
    "
```

## See Also

- [Code Search](CODE_SEARCH.md) - Find existing code patterns
- [Refactoring](REFACTORING.md) - Refactor generated code
- [AI Review](AI_REVIEW.md) - Review generated code
