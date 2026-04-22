"""Tests for code template system."""

import json
import pytest
from pathlib import Path
from pr_agent.templates import (
    TemplateManager,
    TemplateEngine,
    CodeTemplate,
    TemplateVariable,
    TemplateLanguage,
    TemplateCategory,
)


class TestTemplateEngine:
    """Test template rendering engine."""

    def test_simple_variable_substitution(self):
        """Test basic variable substitution."""
        engine = TemplateEngine()
        template = "Hello {{name}}!"
        result = engine.render(template, {"name": "World"})
        assert result == "Hello World!"

    def test_multiple_variables(self):
        """Test multiple variable substitution."""
        engine = TemplateEngine()
        template = "{{greeting}} {{name}}, you are {{age}} years old."
        result = engine.render(template, {
            "greeting": "Hello",
            "name": "Alice",
            "age": 30
        })
        assert result == "Hello Alice, you are 30 years old."

    def test_missing_variable(self):
        """Test missing variable handling."""
        engine = TemplateEngine()
        template = "Hello {{name}}!"
        result = engine.render(template, {})
        assert "MISSING:name" in result

    def test_conditional_true(self):
        """Test conditional block when true."""
        engine = TemplateEngine()
        template = "{% if show %}Visible{% endif %}"
        result = engine.render(template, {"show": True})
        assert result == "Visible"

    def test_conditional_false(self):
        """Test conditional block when false."""
        engine = TemplateEngine()
        template = "{% if show %}Visible{% endif %}"
        result = engine.render(template, {"show": False})
        assert result == ""

    def test_loop(self):
        """Test loop rendering."""
        engine = TemplateEngine()
        template = "{% for item in items %}{{item}}, {% endfor %}"
        result = engine.render(template, {"items": ["a", "b", "c"]})
        assert result == "a, b, c, "

    def test_extract_variables(self):
        """Test variable extraction."""
        engine = TemplateEngine()
        template = "{{name}} {{age}} {% if active %}yes{% endif %}"
        variables = engine.extract_variables(template)
        assert set(variables) == {"name", "age", "active"}


class TestTemplateVariable:
    """Test template variable definition."""

    def test_variable_creation(self):
        """Test creating a template variable."""
        var = TemplateVariable(
            name="test_var",
            description="Test variable",
            default="default_value",
            required=False
        )
        assert var.name == "test_var"
        assert var.default == "default_value"
        assert not var.required

    def test_required_variable(self):
        """Test required variable."""
        var = TemplateVariable(
            name="required_var",
            description="Required variable",
            required=True
        )
        assert var.required
        assert var.default is None


class TestCodeTemplate:
    """Test code template data structure."""

    def test_template_creation(self):
        """Test creating a code template."""
        template = CodeTemplate(
            id="test-template",
            name="Test Template",
            description="A test template",
            language=TemplateLanguage.PYTHON,
            category=TemplateCategory.FUNCTION,
            content="def {{name}}(): pass",
            variables=[
                TemplateVariable("name", "Function name", required=True)
            ],
            tags=["test", "python"]
        )
        assert template.id == "test-template"
        assert template.language == TemplateLanguage.PYTHON
        assert len(template.variables) == 1
        assert len(template.tags) == 2

    def test_template_defaults(self):
        """Test template default values."""
        template = CodeTemplate(
            id="test",
            name="Test",
            description="Test",
            language=TemplateLanguage.PYTHON,
            category=TemplateCategory.FUNCTION,
            content="test"
        )
        assert template.usage_count == 0
        assert template.variables == []
        assert template.tags == []


class TestTemplateManager:
    """Test template manager."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        return tmp_path / "templates"

    @pytest.fixture
    def manager(self, temp_storage):
        """Create template manager with temp storage."""
        return TemplateManager(storage_dir=temp_storage)

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert manager.storage_dir.exists()
        assert len(manager.templates) > 0  # Built-in templates

    def test_create_template(self, manager):
        """Test creating a new template."""
        template = CodeTemplate(
            id="custom-test",
            name="Custom Test",
            description="Custom template",
            language=TemplateLanguage.PYTHON,
            category=TemplateCategory.FUNCTION,
            content="# {{comment}}"
        )
        result = manager.create_template(template)
        assert result.id == "custom-test"
        assert "custom-test" in manager.templates

    def test_create_duplicate_template(self, manager):
        """Test creating duplicate template fails."""
        template = CodeTemplate(
            id="duplicate",
            name="Duplicate",
            description="Test",
            language=TemplateLanguage.PYTHON,
            category=TemplateCategory.FUNCTION,
            content="test"
        )
        manager.create_template(template)

        with pytest.raises(ValueError, match="already exists"):
            manager.create_template(template)

    def test_get_template(self, manager):
        """Test getting a template."""
        template = manager.get_template("python-class")
        assert template is not None
        assert template.id == "python-class"

    def test_get_nonexistent_template(self, manager):
        """Test getting nonexistent template."""
        template = manager.get_template("nonexistent")
        assert template is None

    def test_update_template(self, manager):
        """Test updating a template."""
        template = CodeTemplate(
            id="update-test",
            name="Update Test",
            description="Original",
            language=TemplateLanguage.PYTHON,
            category=TemplateCategory.FUNCTION,
            content="original"
        )
        manager.create_template(template)

        updated = manager.update_template("update-test", {
            "description": "Updated",
            "content": "updated"
        })
        assert updated.description == "Updated"
        assert updated.content == "updated"

    def test_delete_template(self, manager):
        """Test deleting a template."""
        template = CodeTemplate(
            id="delete-test",
            name="Delete Test",
            description="Test",
            language=TemplateLanguage.PYTHON,
            category=TemplateCategory.FUNCTION,
            content="test"
        )
        manager.create_template(template)
        assert "delete-test" in manager.templates

        result = manager.delete_template("delete-test")
        assert result is True
        assert "delete-test" not in manager.templates

    def test_delete_nonexistent_template(self, manager):
        """Test deleting nonexistent template."""
        result = manager.delete_template("nonexistent")
        assert result is False

    def test_list_templates(self, manager):
        """Test listing all templates."""
        templates = manager.list_templates()
        assert len(templates) > 0
        assert all(isinstance(t, CodeTemplate) for t in templates)

    def test_list_templates_by_language(self, manager):
        """Test filtering templates by language."""
        templates = manager.list_templates(language=TemplateLanguage.PYTHON)
        assert len(templates) > 0
        assert all(t.language == TemplateLanguage.PYTHON for t in templates)

    def test_list_templates_by_category(self, manager):
        """Test filtering templates by category."""
        templates = manager.list_templates(category=TemplateCategory.FUNCTION)
        assert len(templates) > 0
        assert all(t.category == TemplateCategory.FUNCTION for t in templates)

    def test_list_templates_by_tags(self, manager):
        """Test filtering templates by tags."""
        templates = manager.list_templates(tags=["python"])
        assert len(templates) > 0
        assert all("python" in t.tags for t in templates)

    def test_search_templates(self, manager):
        """Test searching templates."""
        results = manager.search_templates("python")
        assert len(results) > 0
        assert all("python" in t.name.lower() or
                  "python" in t.description.lower() or
                  "python" in t.tags for t in results)

    def test_instantiate_template(self, manager):
        """Test instantiating a template."""
        instance = manager.instantiate_template(
            "python-function",
            {
                "function_name": "test_func",
                "description": "Test function",
                "params": "",
                "param_list": [],
                "return_type": "None",
                "return_description": "Nothing"
            }
        )
        assert instance.template_id == "python-function"
        assert "test_func" in instance.content
        assert "Test function" in instance.content

    def test_instantiate_missing_required_variable(self, manager):
        """Test instantiating with missing required variable."""
        with pytest.raises(ValueError, match="Required variable"):
            manager.instantiate_template("python-function", {})

    def test_preview_template(self, manager):
        """Test previewing template."""
        preview = manager.preview_template(
            "python-class",
            {
                "class_name": "TestClass",
                "description": "Test class",
                "has_params": False,
                "param_list": []
            }
        )
        assert "TestClass" in preview
        assert "Test class" in preview

    def test_export_templates(self, manager, tmp_path):
        """Test exporting templates."""
        output_file = tmp_path / "export.json"
        count = manager.export_templates(output_file)
        assert count > 0
        assert output_file.exists()

        with open(output_file, 'r') as f:
            data = json.load(f)
            assert len(data) == count

    def test_import_templates(self, manager, tmp_path):
        """Test importing templates."""
        # Create export file
        templates_data = [
            {
                "id": "import-test",
                "name": "Import Test",
                "description": "Test",
                "language": "python",
                "category": "function",
                "content": "test",
                "variables": [],
                "tags": [],
                "author": None,
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-01-01T00:00:00",
                "usage_count": 0
            }
        ]
        import_file = tmp_path / "import.json"
        with open(import_file, 'w') as f:
            json.dump(templates_data, f)

        count = manager.import_templates(import_file)
        assert count == 1
        assert "import-test" in manager.templates

    def test_usage_count_increment(self, manager):
        """Test usage count increments on instantiation."""
        template = manager.get_template("python-class")
        initial_count = template.usage_count

        manager.instantiate_template(
            "python-class",
            {
                "class_name": "Test",
                "description": "Test",
                "has_params": False,
                "param_list": []
            }
        )

        updated_template = manager.get_template("python-class")
        assert updated_template.usage_count == initial_count + 1


class TestBuiltinTemplates:
    """Test built-in templates."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create manager with temp storage."""
        return TemplateManager(storage_dir=tmp_path / "templates")

    def test_python_class_template(self, manager):
        """Test Python class template."""
        template = manager.get_template("python-class")
        assert template is not None
        assert template.language == TemplateLanguage.PYTHON
        assert template.category == TemplateCategory.CLASS

    def test_python_function_template(self, manager):
        """Test Python function template."""
        template = manager.get_template("python-function")
        assert template is not None
        assert template.language == TemplateLanguage.PYTHON
        assert template.category == TemplateCategory.FUNCTION

    def test_python_test_template(self, manager):
        """Test Python test template."""
        template = manager.get_template("python-test")
        assert template is not None
        assert template.category == TemplateCategory.TEST

    def test_fastapi_endpoint_template(self, manager):
        """Test FastAPI endpoint template."""
        template = manager.get_template("fastapi-endpoint")
        assert template is not None
        assert template.category == TemplateCategory.API
