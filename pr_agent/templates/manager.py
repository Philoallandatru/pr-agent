"""
Code template and snippet management system.

Provides template creation, variable substitution, and snippet library management.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import re


logger = logging.getLogger(__name__)


class TemplateLanguage(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    CSHARP = "csharp"
    RUBY = "ruby"
    PHP = "php"
    GENERIC = "generic"


class TemplateCategory(str, Enum):
    """Template categories."""
    CLASS = "class"
    FUNCTION = "function"
    TEST = "test"
    API = "api"
    DATABASE = "database"
    UI = "ui"
    UTILITY = "utility"
    BOILERPLATE = "boilerplate"
    PATTERN = "pattern"
    CUSTOM = "custom"


@dataclass
class TemplateVariable:
    """Template variable definition."""
    name: str
    description: str
    default: Optional[str] = None
    required: bool = True
    type: str = "string"  # string, number, boolean, list
    choices: Optional[List[str]] = None


@dataclass
class CodeTemplate:
    """Code template with variables."""
    id: str
    name: str
    description: str
    language: TemplateLanguage
    category: TemplateCategory
    content: str
    variables: List[TemplateVariable] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    author: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    usage_count: int = 0


@dataclass
class TemplateInstance:
    """Instantiated template with resolved variables."""
    template_id: str
    content: str
    variables: Dict[str, Any]
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TemplateEngine:
    """Template variable substitution engine."""

    def __init__(self):
        self.variable_pattern = re.compile(r'\{\{(\w+)\}\}')
        self.conditional_pattern = re.compile(r'\{\%\s*if\s+(\w+)\s*\%\}(.*?)\{\%\s*endif\s*\%\}', re.DOTALL)
        self.loop_pattern = re.compile(r'\{\%\s*for\s+(\w+)\s+in\s+(\w+)\s*\%\}(.*?)\{\%\s*endfor\s*\%\}', re.DOTALL)

    def render(self, template: str, variables: Dict[str, Any]) -> str:
        """
        Render template with variables.

        Supports:
        - Variable substitution: {{variable}}
        - Conditionals: {% if variable %}...{% endif %}
        - Loops: {% for item in list %}...{% endfor %}
        """
        content = template

        # Process loops
        content = self._process_loops(content, variables)

        # Process conditionals
        content = self._process_conditionals(content, variables)

        # Process variables
        content = self._process_variables(content, variables)

        return content

    def _process_variables(self, content: str, variables: Dict[str, Any]) -> str:
        """Replace {{variable}} with values."""
        def replace_var(match):
            var_name = match.group(1)
            value = variables.get(var_name, f"{{{{MISSING:{var_name}}}}}")
            return str(value)

        return self.variable_pattern.sub(replace_var, content)

    def _process_conditionals(self, content: str, variables: Dict[str, Any]) -> str:
        """Process {% if variable %}...{% endif %} blocks."""
        def replace_conditional(match):
            var_name = match.group(1)
            block_content = match.group(2)

            # Check if variable is truthy
            if variables.get(var_name):
                return block_content
            return ""

        return self.conditional_pattern.sub(replace_conditional, content)

    def _process_loops(self, content: str, variables: Dict[str, Any]) -> str:
        """Process {% for item in list %}...{% endfor %} blocks."""
        def replace_loop(match):
            item_name = match.group(1)
            list_name = match.group(2)
            block_content = match.group(3)

            items = variables.get(list_name, [])
            if not isinstance(items, list):
                return ""

            result = []
            for item in items:
                # Create temporary variables dict with loop item
                loop_vars = variables.copy()
                loop_vars[item_name] = item

                # Render block with loop variables
                rendered = self._process_variables(block_content, loop_vars)
                result.append(rendered)

            return "".join(result)

        return self.loop_pattern.sub(replace_loop, content)

    def extract_variables(self, template: str) -> List[str]:
        """Extract all variable names from template."""
        variables = set()

        # Extract from {{variable}}
        for match in self.variable_pattern.finditer(template):
            variables.add(match.group(1))

        # Extract from conditionals
        for match in self.conditional_pattern.finditer(template):
            variables.add(match.group(1))

        # Extract from loops
        for match in self.loop_pattern.finditer(template):
            variables.add(match.group(2))  # list name

        return sorted(variables)


class TemplateManager:
    """Manage code templates and snippets."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path.home() / ".pr_agent" / "templates"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.templates: Dict[str, CodeTemplate] = {}
        self.engine = TemplateEngine()

        self._load_templates()
        self._load_builtin_templates()

    def _load_templates(self):
        """Load templates from storage."""
        templates_file = self.storage_dir / "templates.json"
        if templates_file.exists():
            try:
                with open(templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for template_data in data:
                        template = CodeTemplate(**template_data)
                        self.templates[template.id] = template
                logger.info(f"Loaded {len(self.templates)} templates")
            except Exception as e:
                logger.error(f"Failed to load templates: {e}")

    def _save_templates(self):
        """Save templates to storage."""
        templates_file = self.storage_dir / "templates.json"
        try:
            data = [asdict(t) for t in self.templates.values()]
            with open(templates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self.templates)} templates")
        except Exception as e:
            logger.error(f"Failed to save templates: {e}")

    def _load_builtin_templates(self):
        """Load built-in templates."""
        builtin = [
            CodeTemplate(
                id="python-class",
                name="Python Class",
                description="Basic Python class template",
                language=TemplateLanguage.PYTHON,
                category=TemplateCategory.CLASS,
                content='''class {{class_name}}:
    """{{description}}"""

    def __init__(self{% if has_params %}, {{params}}{% endif %}):
        """Initialize {{class_name}}."""
        {% for param in param_list %}self.{{param}} = {{param}}
        {% endfor %}

    def __repr__(self):
        return f"{{class_name}}({% for param in param_list %}{{param}}={{self.{{param}}}}{% endfor %})"
''',
                variables=[
                    TemplateVariable("class_name", "Class name", required=True),
                    TemplateVariable("description", "Class description", default="Class description"),
                    TemplateVariable("has_params", "Has constructor parameters", default="false", type="boolean"),
                    TemplateVariable("params", "Constructor parameters", default=""),
                    TemplateVariable("param_list", "List of parameter names", default="[]", type="list"),
                ],
                tags=["python", "class", "oop"],
                author="system"
            ),
            CodeTemplate(
                id="python-function",
                name="Python Function",
                description="Python function with docstring",
                language=TemplateLanguage.PYTHON,
                category=TemplateCategory.FUNCTION,
                content='''def {{function_name}}({{params}}):
    """
    {{description}}

    Args:
        {% for param in param_list %}{{param}}: {{param}} description
        {% endfor %}

    Returns:
        {{return_type}}: {{return_description}}
    """
    {% if has_implementation %}{{implementation}}{% endif %}
    pass
''',
                variables=[
                    TemplateVariable("function_name", "Function name", required=True),
                    TemplateVariable("description", "Function description", required=True),
                    TemplateVariable("params", "Function parameters", default=""),
                    TemplateVariable("param_list", "List of parameter names", default="[]", type="list"),
                    TemplateVariable("return_type", "Return type", default="None"),
                    TemplateVariable("return_description", "Return value description", default=""),
                    TemplateVariable("has_implementation", "Has implementation", default="false", type="boolean"),
                    TemplateVariable("implementation", "Implementation code", default=""),
                ],
                tags=["python", "function"],
                author="system"
            ),
            CodeTemplate(
                id="python-test",
                name="Python Test Function",
                description="pytest test function template",
                language=TemplateLanguage.PYTHON,
                category=TemplateCategory.TEST,
                content='''def test_{{test_name}}({{fixtures}}):
    """Test {{description}}."""
    # Arrange
    {{arrange}}

    # Act
    {{act}}

    # Assert
    {{assert_statement}}
''',
                variables=[
                    TemplateVariable("test_name", "Test name", required=True),
                    TemplateVariable("description", "Test description", required=True),
                    TemplateVariable("fixtures", "pytest fixtures", default=""),
                    TemplateVariable("arrange", "Setup code", default="pass"),
                    TemplateVariable("act", "Action code", default="pass"),
                    TemplateVariable("assert_statement", "Assertion", default="assert True"),
                ],
                tags=["python", "test", "pytest"],
                author="system"
            ),
            CodeTemplate(
                id="fastapi-endpoint",
                name="FastAPI Endpoint",
                description="FastAPI REST endpoint template",
                language=TemplateLanguage.PYTHON,
                category=TemplateCategory.API,
                content='''@app.{{method}}("{{path}}")
async def {{function_name}}({% if has_params %}{{params}}{% endif %}):
    """
    {{description}}

    {% if has_params %}Args:
        {% for param in param_list %}{{param}}: {{param}} description
        {% endfor %}
    {% endif %}
    Returns:
        {{return_type}}: {{return_description}}
    """
    try:
        {{implementation}}
        return {{return_value}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
''',
                variables=[
                    TemplateVariable("method", "HTTP method", default="get", choices=["get", "post", "put", "delete", "patch"]),
                    TemplateVariable("path", "Endpoint path", required=True),
                    TemplateVariable("function_name", "Function name", required=True),
                    TemplateVariable("description", "Endpoint description", required=True),
                    TemplateVariable("has_params", "Has parameters", default="false", type="boolean"),
                    TemplateVariable("params", "Function parameters", default=""),
                    TemplateVariable("param_list", "List of parameter names", default="[]", type="list"),
                    TemplateVariable("return_type", "Return type", default="dict"),
                    TemplateVariable("return_description", "Return value description", default=""),
                    TemplateVariable("implementation", "Implementation code", default="pass"),
                    TemplateVariable("return_value", "Return value", default="{}"),
                ],
                tags=["python", "fastapi", "api", "rest"],
                author="system"
            ),
        ]

        for template in builtin:
            if template.id not in self.templates:
                self.templates[template.id] = template

    def create_template(self, template: CodeTemplate) -> CodeTemplate:
        """Create a new template."""
        if template.id in self.templates:
            raise ValueError(f"Template {template.id} already exists")

        self.templates[template.id] = template
        self._save_templates()
        logger.info(f"Created template: {template.id}")
        return template

    def update_template(self, template_id: str, updates: Dict[str, Any]) -> CodeTemplate:
        """Update an existing template."""
        if template_id not in self.templates:
            raise ValueError(f"Template {template_id} not found")

        template = self.templates[template_id]
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = datetime.now(timezone.utc).isoformat()
        self._save_templates()
        logger.info(f"Updated template: {template_id}")
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id not in self.templates:
            return False

        del self.templates[template_id]
        self._save_templates()
        logger.info(f"Deleted template: {template_id}")
        return True

    def get_template(self, template_id: str) -> Optional[CodeTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def list_templates(
        self,
        language: Optional[TemplateLanguage] = None,
        category: Optional[TemplateCategory] = None,
        tags: Optional[List[str]] = None
    ) -> List[CodeTemplate]:
        """List templates with optional filters."""
        templates = list(self.templates.values())

        if language:
            templates = [t for t in templates if t.language == language]

        if category:
            templates = [t for t in templates if t.category == category]

        if tags:
            templates = [t for t in templates if any(tag in t.tags for tag in tags)]

        return sorted(templates, key=lambda t: t.name)

    def search_templates(self, query: str) -> List[CodeTemplate]:
        """Search templates by name, description, or tags."""
        query_lower = query.lower()
        results = []

        for template in self.templates.values():
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)

        return sorted(results, key=lambda t: t.usage_count, reverse=True)

    def instantiate_template(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> TemplateInstance:
        """Instantiate a template with variables."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Validate required variables
        for var in template.variables:
            if var.required and var.name not in variables:
                if var.default is not None:
                    variables[var.name] = var.default
                else:
                    raise ValueError(f"Required variable '{var.name}' not provided")

        # Render template
        content = self.engine.render(template.content, variables)

        # Update usage count
        template.usage_count += 1
        self._save_templates()

        return TemplateInstance(
            template_id=template_id,
            content=content,
            variables=variables
        )

    def preview_template(
        self,
        template_id: str,
        variables: Dict[str, Any]
    ) -> str:
        """Preview template rendering without saving."""
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        return self.engine.render(template.content, variables)

    def export_templates(self, output_file: Path) -> int:
        """Export all templates to a file."""
        data = [asdict(t) for t in self.templates.values()]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return len(data)

    def import_templates(self, input_file: Path, overwrite: bool = False) -> int:
        """Import templates from a file."""
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        count = 0
        for template_data in data:
            template = CodeTemplate(**template_data)
            if template.id not in self.templates or overwrite:
                self.templates[template.id] = template
                count += 1

        self._save_templates()
        return count


# Global instance
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager


def configure_template_manager(storage_dir: Path):
    """Configure global template manager."""
    global _template_manager
    _template_manager = TemplateManager(storage_dir=storage_dir)
