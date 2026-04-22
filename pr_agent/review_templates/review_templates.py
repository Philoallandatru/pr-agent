"""
Code Review Template System.

Provides customizable templates for different review scenarios.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


class TemplateCategory(str, Enum):
    """Template categories."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    STYLE = "style"
    GENERAL = "general"


class CheckSeverity(str, Enum):
    """Check item severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class CheckItem:
    """Individual check item in a template."""
    check_id: str
    title: str
    description: str
    severity: CheckSeverity
    required: bool = True
    guidance: str = ""
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check_id": self.check_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "required": self.required,
            "guidance": self.guidance,
            "examples": self.examples,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CheckItem":
        """Create from dictionary."""
        return cls(
            check_id=data["check_id"],
            title=data["title"],
            description=data["description"],
            severity=CheckSeverity(data["severity"]),
            required=data.get("required", True),
            guidance=data.get("guidance", ""),
            examples=data.get("examples", []),
            metadata=data.get("metadata", {})
        )


@dataclass
class ReviewTemplate:
    """Code review template."""
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    check_items: List[CheckItem] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_check(self, check: CheckItem):
        """Add a check item."""
        self.check_items.append(check)

    def get_required_checks(self) -> List[CheckItem]:
        """Get all required checks."""
        return [c for c in self.check_items if c.required]

    def get_checks_by_severity(self, severity: CheckSeverity) -> List[CheckItem]:
        """Get checks by severity level."""
        return [c for c in self.check_items if c.severity == severity]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "check_items": [c.to_dict() for c in self.check_items],
            "enabled": self.enabled,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReviewTemplate":
        """Create from dictionary."""
        return cls(
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            category=TemplateCategory(data["category"]),
            check_items=[CheckItem.from_dict(c) for c in data.get("check_items", [])],
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {})
        )


@dataclass
class ReviewResult:
    """Result of applying a template."""
    template_id: str
    template_name: str
    file_path: str
    checks_passed: int = 0
    checks_failed: int = 0
    checks_skipped: int = 0
    findings: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_finding(
        self,
        check_id: str,
        status: str,
        message: str,
        severity: CheckSeverity,
        line_number: Optional[int] = None,
        suggestion: Optional[str] = None
    ):
        """Add a finding."""
        self.findings.append({
            "check_id": check_id,
            "status": status,
            "message": message,
            "severity": severity.value,
            "line_number": line_number,
            "suggestion": suggestion
        })

        if status == "passed":
            self.checks_passed += 1
        elif status == "failed":
            self.checks_failed += 1
        else:
            self.checks_skipped += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get result summary."""
        total = self.checks_passed + self.checks_failed + self.checks_skipped
        return {
            "template_id": self.template_id,
            "template_name": self.template_name,
            "file_path": self.file_path,
            "total_checks": total,
            "passed": self.checks_passed,
            "failed": self.checks_failed,
            "skipped": self.checks_skipped,
            "pass_rate": self.checks_passed / total if total > 0 else 0,
            "critical_findings": len([
                f for f in self.findings
                if f["severity"] == CheckSeverity.CRITICAL.value and f["status"] == "failed"
            ])
        }


class TemplateManager:
    """
    Manages review templates.

    Provides template CRUD operations, built-in templates, and import/export.
    """

    def __init__(self, storage_path: str = ".pr_agent/templates"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.templates: Dict[str, ReviewTemplate] = {}
        self._load_builtin_templates()

    def register_template(self, template: ReviewTemplate):
        """Register a template."""
        self.templates[template.template_id] = template
        self._save_template(template)

    def unregister_template(self, template_id: str) -> bool:
        """Unregister a template."""
        if template_id in self.templates:
            del self.templates[template_id]
            template_file = self.storage_path / f"{template_id}.json"
            if template_file.exists():
                template_file.unlink()
            return True
        return False

    def get_template(self, template_id: str) -> Optional[ReviewTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        enabled_only: bool = False
    ) -> List[ReviewTemplate]:
        """List all templates."""
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        if enabled_only:
            templates = [t for t in templates if t.enabled]

        return templates

    def apply_template(
        self,
        template_id: str,
        file_path: str,
        content: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ReviewResult:
        """
        Apply a template to a file.

        This is a basic implementation that creates a result structure.
        Actual checking logic should be implemented by integrating with
        the rules engine or other analysis tools.
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        result = ReviewResult(
            template_id=template.template_id,
            template_name=template.name,
            file_path=file_path
        )

        # Basic implementation - in practice, integrate with rules engine
        for check in template.check_items:
            # Placeholder logic - should be replaced with actual checks
            result.add_finding(
                check_id=check.check_id,
                status="passed",  # Would be determined by actual check
                message=f"Check '{check.title}' completed",
                severity=check.severity
            )

        return result

    def export_templates(self, template_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Export templates to JSON."""
        if template_ids:
            templates = [self.templates[tid] for tid in template_ids if tid in self.templates]
        else:
            templates = list(self.templates.values())

        return {
            "version": "1.0",
            "templates": [t.to_dict() for t in templates]
        }

    def import_templates(self, data: Dict[str, Any], overwrite: bool = False):
        """Import templates from JSON."""
        for template_data in data.get("templates", []):
            template = ReviewTemplate.from_dict(template_data)
            if template.template_id in self.templates and not overwrite:
                continue
            self.register_template(template)

    def _save_template(self, template: ReviewTemplate):
        """Save template to disk."""
        template_file = self.storage_path / f"{template.template_id}.json"
        with open(template_file, "w") as f:
            json.dump(template.to_dict(), f, indent=2)

    def _load_template(self, template_file: Path) -> Optional[ReviewTemplate]:
        """Load template from disk."""
        try:
            with open(template_file) as f:
                data = json.load(f)
            return ReviewTemplate.from_dict(data)
        except Exception:
            return None

    def _load_builtin_templates(self):
        """Load built-in templates."""
        # Security Review Template
        security_template = ReviewTemplate(
            template_id="builtin_security",
            name="Security Review",
            description="Comprehensive security review checklist",
            category=TemplateCategory.SECURITY
        )

        security_template.add_check(CheckItem(
            check_id="SEC_AUTH",
            title="Authentication & Authorization",
            description="Verify proper authentication and authorization checks",
            severity=CheckSeverity.CRITICAL,
            required=True,
            guidance="Ensure all endpoints require authentication and check user permissions",
            examples=[
                "Check for @require_auth decorators",
                "Verify role-based access control",
                "Look for missing permission checks"
            ]
        ))

        security_template.add_check(CheckItem(
            check_id="SEC_INPUT",
            title="Input Validation",
            description="Check for proper input validation and sanitization",
            severity=CheckSeverity.HIGH,
            required=True,
            guidance="All user input should be validated and sanitized",
            examples=[
                "SQL injection prevention",
                "XSS prevention",
                "Command injection prevention"
            ]
        ))

        security_template.add_check(CheckItem(
            check_id="SEC_CRYPTO",
            title="Cryptography",
            description="Verify secure cryptographic practices",
            severity=CheckSeverity.HIGH,
            required=True,
            guidance="Use strong algorithms, proper key management, secure random generation",
            examples=[
                "No hardcoded secrets",
                "Use bcrypt/argon2 for passwords",
                "Proper TLS configuration"
            ]
        ))

        security_template.add_check(CheckItem(
            check_id="SEC_LOGGING",
            title="Security Logging",
            description="Ensure security events are logged",
            severity=CheckSeverity.MEDIUM,
            required=False,
            guidance="Log authentication failures, authorization failures, suspicious activities",
            examples=[
                "Failed login attempts",
                "Access denied events",
                "Unusual patterns"
            ]
        ))

        self.register_template(security_template)

        # Performance Review Template
        perf_template = ReviewTemplate(
            template_id="builtin_performance",
            name="Performance Review",
            description="Performance optimization checklist",
            category=TemplateCategory.PERFORMANCE
        )

        perf_template.add_check(CheckItem(
            check_id="PERF_QUERY",
            title="Database Query Optimization",
            description="Check for N+1 queries and missing indexes",
            severity=CheckSeverity.HIGH,
            required=True,
            guidance="Use eager loading, add indexes, avoid SELECT *",
            examples=[
                "Use .select_related() in Django",
                "Add database indexes",
                "Batch queries where possible"
            ]
        ))

        perf_template.add_check(CheckItem(
            check_id="PERF_CACHE",
            title="Caching Strategy",
            description="Verify appropriate caching is used",
            severity=CheckSeverity.MEDIUM,
            required=False,
            guidance="Cache expensive operations, use appropriate TTLs",
            examples=[
                "Redis/Memcached for session data",
                "HTTP caching headers",
                "Query result caching"
            ]
        ))

        perf_template.add_check(CheckItem(
            check_id="PERF_ASYNC",
            title="Asynchronous Processing",
            description="Check for blocking operations that should be async",
            severity=CheckSeverity.MEDIUM,
            required=False,
            guidance="Use background jobs for long-running tasks",
            examples=[
                "Email sending",
                "File processing",
                "External API calls"
            ]
        ))

        self.register_template(perf_template)

        # Architecture Review Template
        arch_template = ReviewTemplate(
            template_id="builtin_architecture",
            name="Architecture Review",
            description="Software architecture and design review",
            category=TemplateCategory.ARCHITECTURE
        )

        arch_template.add_check(CheckItem(
            check_id="ARCH_SOLID",
            title="SOLID Principles",
            description="Verify adherence to SOLID principles",
            severity=CheckSeverity.MEDIUM,
            required=True,
            guidance="Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion",
            examples=[
                "Classes have single responsibility",
                "Open for extension, closed for modification",
                "Depend on abstractions, not concretions"
            ]
        ))

        arch_template.add_check(CheckItem(
            check_id="ARCH_COUPLING",
            title="Coupling & Cohesion",
            description="Check for tight coupling and low cohesion",
            severity=CheckSeverity.MEDIUM,
            required=True,
            guidance="Minimize dependencies between modules, maximize cohesion within modules",
            examples=[
                "Use dependency injection",
                "Avoid circular dependencies",
                "Group related functionality"
            ]
        ))

        arch_template.add_check(CheckItem(
            check_id="ARCH_PATTERNS",
            title="Design Patterns",
            description="Verify appropriate use of design patterns",
            severity=CheckSeverity.LOW,
            required=False,
            guidance="Use patterns where they add value, avoid over-engineering",
            examples=[
                "Factory for object creation",
                "Strategy for algorithms",
                "Observer for event handling"
            ]
        ))

        self.register_template(arch_template)

        # Style Review Template
        style_template = ReviewTemplate(
            template_id="builtin_style",
            name="Code Style Review",
            description="Code style and readability checklist",
            category=TemplateCategory.STYLE
        )

        style_template.add_check(CheckItem(
            check_id="STYLE_NAMING",
            title="Naming Conventions",
            description="Check for clear, consistent naming",
            severity=CheckSeverity.LOW,
            required=True,
            guidance="Use descriptive names, follow language conventions",
            examples=[
                "snake_case for Python functions",
                "PascalCase for classes",
                "UPPER_CASE for constants"
            ]
        ))

        style_template.add_check(CheckItem(
            check_id="STYLE_COMMENTS",
            title="Comments & Documentation",
            description="Verify appropriate comments and docstrings",
            severity=CheckSeverity.LOW,
            required=False,
            guidance="Comment why, not what. Document public APIs",
            examples=[
                "Docstrings for public functions",
                "Explain complex algorithms",
                "Document assumptions"
            ]
        ))

        style_template.add_check(CheckItem(
            check_id="STYLE_FORMAT",
            title="Code Formatting",
            description="Check code formatting consistency",
            severity=CheckSeverity.INFO,
            required=False,
            guidance="Use automated formatters (Black, Prettier, etc.)",
            examples=[
                "Consistent indentation",
                "Line length limits",
                "Import organization"
            ]
        ))

        self.register_template(style_template)

        # General Review Template
        general_template = ReviewTemplate(
            template_id="builtin_general",
            name="General Code Review",
            description="General purpose code review checklist",
            category=TemplateCategory.GENERAL
        )

        general_template.add_check(CheckItem(
            check_id="GEN_CORRECTNESS",
            title="Correctness",
            description="Verify code does what it's supposed to do",
            severity=CheckSeverity.CRITICAL,
            required=True,
            guidance="Test edge cases, verify business logic",
            examples=[
                "Handles null/empty inputs",
                "Correct error handling",
                "Business rules implemented correctly"
            ]
        ))

        general_template.add_check(CheckItem(
            check_id="GEN_TESTS",
            title="Test Coverage",
            description="Check for adequate test coverage",
            severity=CheckSeverity.HIGH,
            required=True,
            guidance="Unit tests for business logic, integration tests for workflows",
            examples=[
                "Test happy path",
                "Test error cases",
                "Test edge cases"
            ]
        ))

        general_template.add_check(CheckItem(
            check_id="GEN_ERROR",
            title="Error Handling",
            description="Verify proper error handling",
            severity=CheckSeverity.HIGH,
            required=True,
            guidance="Catch specific exceptions, provide meaningful error messages",
            examples=[
                "Don't catch generic Exception",
                "Log errors appropriately",
                "Return user-friendly messages"
            ]
        ))

        general_template.add_check(CheckItem(
            check_id="GEN_DOCS",
            title="Documentation",
            description="Check for adequate documentation",
            severity=CheckSeverity.MEDIUM,
            required=False,
            guidance="README, API docs, inline comments where needed",
            examples=[
                "Update README if needed",
                "Document API changes",
                "Add migration notes"
            ]
        ))

        self.register_template(general_template)


# Global template manager instance
_template_manager: Optional[TemplateManager] = None


def get_template_manager() -> TemplateManager:
    """Get the global template manager instance."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
