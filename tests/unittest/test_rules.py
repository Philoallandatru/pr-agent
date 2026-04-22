"""
Tests for the code review rules engine.
"""

import pytest
from pathlib import Path
import tempfile
import json

from pr_agent.rules import (
    RulesEngine,
    Rule,
    RuleSet,
    RuleViolation,
    RuleSeverity,
    RuleCategory,
    get_engine,
)


@pytest.fixture
def engine():
    """Create a fresh rules engine."""
    return RulesEngine()


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory."""
    return tmp_path


class TestRule:
    """Tests for Rule class."""

    def test_rule_creation(self):
        """Test creating a rule."""
        rule = Rule(
            rule_id="TEST001",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.MEDIUM,
            category=RuleCategory.STYLE
        )

        assert rule.rule_id == "TEST001"
        assert rule.name == "Test Rule"
        assert rule.severity == RuleSeverity.MEDIUM
        assert rule.category == RuleCategory.STYLE
        assert rule.enabled is True
        assert rule.priority == 0

    def test_rule_file_matching(self):
        """Test rule file pattern matching."""
        rule = Rule(
            rule_id="TEST001",
            name="Python Rule",
            description="Python files only",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE,
            file_patterns=["**/*.py"],
            exclude_patterns=["**/test_*.py"]
        )

        assert rule.matches_file("src/main.py") is True
        assert rule.matches_file("src/test_main.py") is False
        assert rule.matches_file("src/main.js") is False

    def test_rule_check_disabled(self):
        """Test that disabled rules don't run."""
        rule = Rule(
            rule_id="TEST001",
            name="Test Rule",
            description="Test",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE,
            enabled=False,
            checker=lambda *args: [RuleViolation(
                rule_id="TEST001",
                rule_name="Test",
                severity=RuleSeverity.LOW,
                category=RuleCategory.STYLE,
                message="Test",
                file_path="test.py"
            )]
        )

        violations = rule.check("test.py", "content", {})
        assert len(violations) == 0

    def test_rule_check_with_checker(self):
        """Test rule check with custom checker."""
        def custom_checker(file_path, content, context, rule):
            if "bad" in content:
                return [RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    message="Found 'bad' in content",
                    file_path=file_path
                )]
            return []

        rule = Rule(
            rule_id="TEST001",
            name="Bad Word Check",
            description="Check for bad words",
            severity=RuleSeverity.MEDIUM,
            category=RuleCategory.STYLE,
            file_patterns=["**/*.py"],  # Add file pattern
            checker=custom_checker
        )

        violations = rule.check("test.py", "this is bad code", {})
        assert len(violations) == 1
        assert violations[0].message == "Found 'bad' in content"

        violations = rule.check("test.py", "this is good code", {})
        assert len(violations) == 0


class TestRuleSet:
    """Tests for RuleSet class."""

    def test_ruleset_creation(self):
        """Test creating a rule set."""
        rule_set = RuleSet(
            name="test-set",
            description="Test rule set"
        )

        assert rule_set.name == "test-set"
        assert rule_set.description == "Test rule set"
        assert len(rule_set.rules) == 0
        assert rule_set.enabled is True

    def test_ruleset_add_rule(self):
        """Test adding rules to a set."""
        rule_set = RuleSet(name="test", description="Test")

        rule1 = Rule(
            rule_id="R1",
            name="Rule 1",
            description="First rule",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY
        )

        rule2 = Rule(
            rule_id="R2",
            name="Rule 2",
            description="Second rule",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE
        )

        rule_set.add_rule(rule1)
        rule_set.add_rule(rule2)

        assert len(rule_set.rules) == 2

    def test_ruleset_get_enabled_rules(self):
        """Test getting enabled rules in priority order."""
        rule_set = RuleSet(name="test", description="Test")

        rule1 = Rule(
            rule_id="R1",
            name="Rule 1",
            description="Low priority",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE,
            priority=1
        )

        rule2 = Rule(
            rule_id="R2",
            name="Rule 2",
            description="High priority",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            priority=10
        )

        rule3 = Rule(
            rule_id="R3",
            name="Rule 3",
            description="Disabled",
            severity=RuleSeverity.MEDIUM,
            category=RuleCategory.PERFORMANCE,
            enabled=False
        )

        rule_set.add_rule(rule1)
        rule_set.add_rule(rule2)
        rule_set.add_rule(rule3)

        enabled = rule_set.get_enabled_rules()
        assert len(enabled) == 2
        assert enabled[0].rule_id == "R2"  # Higher priority first
        assert enabled[1].rule_id == "R1"

    def test_ruleset_disabled(self):
        """Test that disabled rule sets return no rules."""
        rule_set = RuleSet(name="test", description="Test", enabled=False)

        rule_set.add_rule(Rule(
            rule_id="R1",
            name="Rule 1",
            description="Test",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE
        ))

        assert len(rule_set.get_enabled_rules()) == 0


class TestRulesEngine:
    """Tests for RulesEngine class."""

    def test_engine_creation(self, engine):
        """Test creating an engine."""
        assert engine is not None
        # Should have built-in rules
        assert len(engine.rules) > 0

    def test_register_rule(self, engine):
        """Test registering a rule."""
        rule = Rule(
            rule_id="CUSTOM001",
            name="Custom Rule",
            description="A custom rule",
            severity=RuleSeverity.MEDIUM,
            category=RuleCategory.STYLE
        )

        engine.register_rule(rule)
        assert "CUSTOM001" in engine.rules
        assert engine.get_rule("CUSTOM001") == rule

    def test_unregister_rule(self, engine):
        """Test unregistering a rule."""
        rule = Rule(
            rule_id="TEMP001",
            name="Temp Rule",
            description="Temporary",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE
        )

        engine.register_rule(rule)
        assert "TEMP001" in engine.rules

        result = engine.unregister_rule("TEMP001")
        assert result is True
        assert "TEMP001" not in engine.rules

        result = engine.unregister_rule("NONEXISTENT")
        assert result is False

    def test_list_rules(self, engine):
        """Test listing rules."""
        all_rules = engine.list_rules()
        assert len(all_rules) > 0

        # Filter by category
        security_rules = engine.list_rules(category=RuleCategory.SECURITY)
        assert all(r.category == RuleCategory.SECURITY for r in security_rules)

        # Filter by severity
        critical_rules = engine.list_rules(severity=RuleSeverity.CRITICAL)
        assert all(r.severity == RuleSeverity.CRITICAL for r in critical_rules)

    def test_register_rule_set(self, engine):
        """Test registering a rule set."""
        rule_set = RuleSet(name="custom", description="Custom rules")

        rule_set.add_rule(Rule(
            rule_id="CUSTOM001",
            name="Custom 1",
            description="First custom rule",
            severity=RuleSeverity.MEDIUM,
            category=RuleCategory.STYLE
        ))

        rule_set.add_rule(Rule(
            rule_id="CUSTOM002",
            name="Custom 2",
            description="Second custom rule",
            severity=RuleSeverity.LOW,
            category=RuleCategory.DOCUMENTATION
        ))

        engine.register_rule_set(rule_set)

        assert "custom" in engine.rule_sets
        assert "CUSTOM001" in engine.rules
        assert "CUSTOM002" in engine.rules

    def test_check_file(self, engine):
        """Test checking a single file."""
        # File with SQL injection risk
        content = """
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
"""

        violations = engine.check_file("test.py", content)
        assert len(violations) > 0
        assert any(v.rule_id == "SEC001" for v in violations)

    def test_check_file_with_specific_rules(self, engine):
        """Test checking with specific rules."""
        content = "password = 'secret123'\n"

        # Check only SEC002 (hardcoded secrets)
        violations = engine.check_file("test.py", content, rule_ids=["SEC002"])
        assert len(violations) > 0
        assert all(v.rule_id == "SEC002" for v in violations)

    def test_check_files(self, engine):
        """Test checking multiple files."""
        files = {
            "file1.py": "password = 'secret'\n",
            "file2.py": "x = 1\n",
            "file3.py": "api_key = 'abc123'\n"
        }

        results = engine.check_files(files)

        # file1 and file3 should have violations
        assert "file1.py" in results
        assert "file3.py" in results
        # file2 should be clean
        assert "file2.py" not in results

    def test_builtin_sql_injection_rule(self, engine):
        """Test built-in SQL injection rule."""
        content = """
cursor.execute("SELECT * FROM users WHERE name = '%s'" % user_input)
"""
        violations = engine.check_file("test.py", content)
        sql_violations = [v for v in violations if v.rule_id == "SEC001"]
        assert len(sql_violations) > 0

    def test_builtin_hardcoded_secrets_rule(self, engine):
        """Test built-in hardcoded secrets rule."""
        content = """
API_KEY = "sk-1234567890abcdef"
password = "mypassword123"
secret = "topsecret"
"""
        violations = engine.check_file("config.py", content)
        secret_violations = [v for v in violations if v.rule_id == "SEC002"]
        assert len(secret_violations) >= 2  # At least password and secret

    def test_builtin_line_length_rule(self, engine):
        """Test built-in line length rule."""
        content = "x = " + "a" * 150 + "\n"
        violations = engine.check_file("test.py", content)
        line_violations = [v for v in violations if v.rule_id == "STYLE001"]
        assert len(line_violations) > 0

    def test_builtin_trailing_whitespace_rule(self, engine):
        """Test built-in trailing whitespace rule."""
        content = "x = 1  \ny = 2\n"
        violations = engine.check_file("test.py", content)
        ws_violations = [v for v in violations if v.rule_id == "STYLE002"]
        assert len(ws_violations) > 0

    def test_builtin_complexity_rule(self, engine):
        """Test built-in complexity rule."""
        content = """
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            if x > 60:
                                if x > 70:
                                    if x > 80:
                                        if x > 90:
                                            return "very high"
    return "low"
"""
        violations = engine.check_file("test.py", content)
        complexity_violations = [v for v in violations if v.rule_id == "COMPLEX001"]
        assert len(complexity_violations) > 0

    def test_export_import_rules(self, engine, temp_dir):
        """Test exporting and importing rules."""
        # Add a custom rule
        custom_rule = Rule(
            rule_id="EXPORT001",
            name="Export Test",
            description="Test export/import",
            severity=RuleSeverity.HIGH,
            category=RuleCategory.SECURITY,
            priority=5,
            file_patterns=["**/*.py"],
            metadata={"test": "value"}
        )
        engine.register_rule(custom_rule)

        # Export
        export_path = temp_dir / "rules.json"
        engine.export_rules(export_path)

        assert export_path.exists()

        # Create new engine and import
        new_engine = RulesEngine()
        new_engine.import_rules(export_path)

        # Verify imported rule
        imported_rule = new_engine.get_rule("EXPORT001")
        assert imported_rule is not None
        assert imported_rule.name == "Export Test"
        assert imported_rule.severity == RuleSeverity.HIGH
        assert imported_rule.priority == 5
        assert imported_rule.metadata["test"] == "value"


class TestGlobalEngine:
    """Tests for global engine instance."""

    def test_get_engine(self):
        """Test getting global engine instance."""
        engine1 = get_engine()
        engine2 = get_engine()

        assert engine1 is engine2  # Should be same instance
        assert len(engine1.rules) > 0  # Should have built-in rules
