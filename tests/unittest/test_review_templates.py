"""
Unit tests for review templates system.
"""

import pytest
import json
from pathlib import Path
from pr_agent.review_templates import (
    TemplateCategory,
    CheckSeverity,
    CheckItem,
    ReviewTemplate,
    ReviewResult,
    TemplateManager,
    get_template_manager,
)


class TestCheckItem:
    """Test CheckItem class."""

    def test_create_check_item(self):
        """Test creating a check item."""
        item = CheckItem(
            check_id="TEST-001",
            title="Test Check",
            description="A test check item",
            severity=CheckSeverity.HIGH,
        )

        assert item.check_id == "TEST-001"
        assert item.title == "Test Check"
        assert item.severity == CheckSeverity.HIGH
        assert item.required is True

    def test_check_item_to_dict(self):
        """Test converting check item to dictionary."""
        item = CheckItem(
            check_id="TEST-001",
            title="Test Check",
            description="A test check",
            severity=CheckSeverity.MEDIUM,
            guidance="Test guidance",
            examples=["Example 1", "Example 2"],
        )

        data = item.to_dict()
        assert data["check_id"] == "TEST-001"
        assert data["severity"] == "medium"
        assert len(data["examples"]) == 2

    def test_check_item_from_dict(self):
        """Test creating check item from dictionary."""
        data = {
            "check_id": "TEST-001",
            "title": "Test Check",
            "description": "A test check",
            "severity": "high",
            "required": False,
            "guidance": "Test guidance",
            "examples": ["Example 1"],
            "metadata": {},
        }

        item = CheckItem.from_dict(data)
        assert item.check_id == "TEST-001"
        assert item.severity == CheckSeverity.HIGH
        assert item.required is False


class TestReviewTemplate:
    """Test ReviewTemplate class."""

    def test_create_template(self):
        """Test creating a review template."""
        template = ReviewTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.SECURITY,
        )

        assert template.template_id == "test-template"
        assert template.name == "Test Template"
        assert template.category == TemplateCategory.SECURITY
        assert len(template.check_items) == 0

    def test_add_check(self):
        """Test adding a check to template."""
        template = ReviewTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.SECURITY,
        )

        check = CheckItem(
            check_id="SEC-001",
            title="Security Check",
            description="Security check",
            severity=CheckSeverity.HIGH,
        )

        template.add_check(check)
        assert len(template.check_items) == 1
        assert template.check_items[0].check_id == "SEC-001"

    def test_get_checks_by_severity(self):
        """Test filtering checks by severity."""
        template = ReviewTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.SECURITY,
        )

        template.add_check(CheckItem(
            check_id="SEC-001",
            title="Critical Check",
            description="Critical check",
            severity=CheckSeverity.CRITICAL,
        ))

        template.add_check(CheckItem(
            check_id="SEC-002",
            title="High Check",
            description="High check",
            severity=CheckSeverity.HIGH,
        ))

        critical_checks = template.get_checks_by_severity(CheckSeverity.CRITICAL)
        assert len(critical_checks) == 1
        assert critical_checks[0].check_id == "SEC-001"

    def test_get_required_checks(self):
        """Test getting required checks."""
        template = ReviewTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.SECURITY,
        )

        template.add_check(CheckItem(
            check_id="SEC-001",
            title="Required Check",
            description="Required check",
            severity=CheckSeverity.HIGH,
            required=True,
        ))

        template.add_check(CheckItem(
            check_id="SEC-002",
            title="Optional Check",
            description="Optional check",
            severity=CheckSeverity.LOW,
            required=False,
        ))

        required_checks = template.get_required_checks()
        assert len(required_checks) == 1
        assert required_checks[0].check_id == "SEC-001"

    def test_template_to_dict(self):
        """Test converting template to dictionary."""
        template = ReviewTemplate(
            template_id="test-template",
            name="Test Template",
            description="A test template",
            category=TemplateCategory.SECURITY,
        )

        template.add_check(CheckItem(
            check_id="SEC-001",
            title="Test Check",
            description="Test check",
            severity=CheckSeverity.HIGH,
        ))

        data = template.to_dict()
        assert data["template_id"] == "test-template"
        assert data["name"] == "Test Template"
        assert data["category"] == "security"
        assert len(data["check_items"]) == 1

    def test_template_from_dict(self):
        """Test creating template from dictionary."""
        data = {
            "template_id": "test-template",
            "name": "Test Template",
            "description": "A test template",
            "category": "security",
            "check_items": [
                {
                    "check_id": "SEC-001",
                    "title": "Test Check",
                    "description": "Test check",
                    "severity": "high",
                    "required": True,
                    "guidance": "",
                    "examples": [],
                    "metadata": {},
                }
            ],
            "enabled": True,
            "metadata": {},
        }

        template = ReviewTemplate.from_dict(data)
        assert template.template_id == "test-template"
        assert len(template.check_items) == 1


class TestReviewResult:
    """Test ReviewResult class."""

    def test_create_review_result(self):
        """Test creating a review result."""
        result = ReviewResult(
            template_id="test-template",
            template_name="Test Template",
            file_path="test.py",
        )

        assert result.template_id == "test-template"
        assert result.file_path == "test.py"
        assert result.checks_passed == 0
        assert result.checks_failed == 0

    def test_add_finding(self):
        """Test adding a finding to result."""
        result = ReviewResult(
            template_id="test-template",
            template_name="Test Template",
            file_path="test.py",
        )

        result.add_finding(
            check_id="SEC-001",
            status="passed",
            message="Check passed",
            severity=CheckSeverity.HIGH,
        )

        assert result.checks_passed == 1
        assert len(result.findings) == 1
        assert result.findings[0]["check_id"] == "SEC-001"

    def test_add_failed_finding(self):
        """Test adding a failed finding."""
        result = ReviewResult(
            template_id="test-template",
            template_name="Test Template",
            file_path="test.py",
        )

        result.add_finding(
            check_id="SEC-001",
            status="failed",
            message="Check failed",
            severity=CheckSeverity.CRITICAL,
            line_number=42,
            suggestion="Fix this issue",
        )

        assert result.checks_failed == 1
        assert result.findings[0]["status"] == "failed"
        assert result.findings[0]["line_number"] == 42

    def test_get_summary(self):
        """Test getting result summary."""
        result = ReviewResult(
            template_id="test-template",
            template_name="Test Template",
            file_path="test.py",
        )

        result.add_finding("SEC-001", "passed", "OK", CheckSeverity.HIGH)
        result.add_finding("SEC-002", "failed", "Failed", CheckSeverity.CRITICAL)
        result.add_finding("SEC-003", "skipped", "Skipped", CheckSeverity.LOW)

        summary = result.get_summary()
        assert summary["total_checks"] == 3
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert summary["skipped"] == 1
        assert summary["critical_findings"] == 1


class TestTemplateManager:
    """Test TemplateManager class."""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        return tmp_path / "templates"

    @pytest.fixture
    def manager(self, temp_storage):
        """Create template manager with temporary storage."""
        return TemplateManager(storage_path=str(temp_storage))

    def test_builtin_templates_loaded(self, manager):
        """Test that built-in templates are loaded."""
        templates = manager.list_templates()
        assert len(templates) >= 4  # At least 4 built-in templates

        # Check specific templates exist
        assert manager.get_template("builtin_security") is not None
        assert manager.get_template("builtin_performance") is not None
        assert manager.get_template("builtin_style") is not None
        assert manager.get_template("builtin_general") is not None

    def test_get_template(self, manager):
        """Test getting a template."""
        template = manager.get_template("builtin_security")
        assert template is not None
        assert template.template_id == "builtin_security"
        assert template.name == "Security Review"

    def test_get_nonexistent_template(self, manager):
        """Test getting a non-existent template."""
        template = manager.get_template("nonexistent")
        assert template is None

    def test_list_templates(self, manager):
        """Test listing all templates."""
        templates = manager.list_templates()
        assert len(templates) > 0
        assert all(isinstance(t, ReviewTemplate) for t in templates)

    def test_register_template(self, manager):
        """Test registering a new template."""
        template = ReviewTemplate(
            template_id="custom-template",
            name="Custom Template",
            description="A custom template",
            category=TemplateCategory.SECURITY,
        )

        manager.register_template(template)

        # Verify it can be retrieved
        retrieved = manager.get_template("custom-template")
        assert retrieved is not None
        assert retrieved.template_id == "custom-template"

    def test_unregister_template(self, manager):
        """Test unregistering a template."""
        # Register a template first
        template = ReviewTemplate(
            template_id="temp-template",
            name="Temp Template",
            description="Temporary template",
            category=TemplateCategory.SECURITY,
        )
        manager.register_template(template)

        # Unregister it
        result = manager.unregister_template("temp-template")
        assert result is True

        # Verify it's gone
        assert manager.get_template("temp-template") is None

    def test_unregister_nonexistent_template(self, manager):
        """Test unregistering a non-existent template."""
        result = manager.unregister_template("nonexistent")
        assert result is False

    def test_list_templates_by_category(self, manager):
        """Test listing templates by category."""
        templates = manager.list_templates(category=TemplateCategory.SECURITY)
        assert len(templates) > 0
        assert all(t.category == TemplateCategory.SECURITY for t in templates)

    def test_list_enabled_templates(self, manager):
        """Test listing only enabled templates."""
        # Create a disabled template
        template = ReviewTemplate(
            template_id="disabled-template",
            name="Disabled Template",
            description="A disabled template",
            category=TemplateCategory.SECURITY,
            enabled=False,
        )
        manager.register_template(template)

        # List only enabled templates
        templates = manager.list_templates(enabled_only=True)
        assert all(t.enabled for t in templates)
        assert not any(t.template_id == "disabled-template" for t in templates)

    def test_apply_template(self, manager):
        """Test applying a template to a file."""
        result = manager.apply_template(
            template_id="builtin_security",
            file_path="test.py",
            content="print('hello')",
        )

        assert result.template_id == "builtin_security"
        assert result.file_path == "test.py"
        assert len(result.findings) > 0

    def test_apply_nonexistent_template(self, manager):
        """Test applying a non-existent template."""
        with pytest.raises(ValueError, match="not found"):
            manager.apply_template(
                template_id="nonexistent",
                file_path="test.py",
                content="print('hello')",
            )

    def test_export_templates(self, manager):
        """Test exporting templates."""
        data = manager.export_templates(template_ids=["builtin_security"])

        assert "version" in data
        assert "templates" in data
        assert len(data["templates"]) == 1
        assert data["templates"][0]["template_id"] == "builtin_security"

    def test_export_all_templates(self, manager):
        """Test exporting all templates."""
        data = manager.export_templates()

        assert len(data["templates"]) >= 4

    def test_import_templates(self, manager):
        """Test importing templates."""
        # Create export data
        export_data = {
            "version": "1.0",
            "templates": [
                {
                    "template_id": "imported-template",
                    "name": "Imported Template",
                    "description": "An imported template",
                    "category": "security",
                    "check_items": [],
                    "enabled": True,
                    "metadata": {},
                }
            ],
        }

        # Import it
        manager.import_templates(export_data)

        # Verify it's available
        template = manager.get_template("imported-template")
        assert template is not None
        assert template.template_id == "imported-template"

    def test_import_templates_no_overwrite(self, manager):
        """Test importing templates without overwriting existing ones."""
        # Get existing template
        original = manager.get_template("builtin_security")
        original_name = original.name

        # Try to import with same ID
        export_data = {
            "version": "1.0",
            "templates": [
                {
                    "template_id": "builtin_security",
                    "name": "Modified Name",
                    "description": "Modified",
                    "category": "security",
                    "check_items": [],
                    "enabled": True,
                    "metadata": {},
                }
            ],
        }

        manager.import_templates(export_data, overwrite=False)

        # Verify original is unchanged
        template = manager.get_template("builtin_security")
        assert template.name == original_name

    def test_import_templates_with_overwrite(self, manager):
        """Test importing templates with overwriting."""
        # Import with overwrite
        export_data = {
            "version": "1.0",
            "templates": [
                {
                    "template_id": "builtin_security",
                    "name": "Modified Name",
                    "description": "Modified",
                    "category": "security",
                    "check_items": [],
                    "enabled": True,
                    "metadata": {},
                }
            ],
        }

        manager.import_templates(export_data, overwrite=True)

        # Verify it was overwritten
        template = manager.get_template("builtin_security")
        assert template.name == "Modified Name"


def test_get_template_manager():
    """Test getting the global template manager."""
    manager1 = get_template_manager()
    manager2 = get_template_manager()

    # Should return the same instance
    assert manager1 is manager2
