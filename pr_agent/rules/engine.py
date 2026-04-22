"""
Code Review Rules Engine

Configurable rules engine for code review with support for custom rules,
rule priorities, rule combinations, and rule templates.
"""

import re
import ast
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Set
from enum import Enum
from pathlib import Path
import json


class RuleSeverity(Enum):
    """Rule violation severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RuleCategory(Enum):
    """Rule categories."""
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"
    MAINTAINABILITY = "maintainability"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    COMPLEXITY = "complexity"
    BEST_PRACTICES = "best_practices"


@dataclass
class RuleViolation:
    """Represents a rule violation."""
    rule_id: str
    rule_name: str
    severity: RuleSeverity
    category: RuleCategory
    message: str
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    code_snippet: Optional[str] = None
    suggestion: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """Represents a code review rule."""
    rule_id: str
    name: str
    description: str
    severity: RuleSeverity
    category: RuleCategory
    enabled: bool = True
    priority: int = 0  # Higher priority rules run first
    file_patterns: List[str] = field(default_factory=lambda: ["**/*"])
    exclude_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Rule implementation (function that checks code)
    checker: Optional[Callable] = None

    def matches_file(self, file_path: str) -> bool:
        """Check if rule applies to given file."""
        from pathlib import PurePath

        # Convert to PurePath for pattern matching
        path = PurePath(file_path)

        # Check exclusions first
        for pattern in self.exclude_patterns:
            # Remove leading **/ for pathlib.match()
            clean_pattern = pattern.lstrip('*').lstrip('/')
            if path.match(clean_pattern):
                return False

        # Check inclusions
        for pattern in self.file_patterns:
            # Remove leading **/ for pathlib.match()
            clean_pattern = pattern.lstrip('*').lstrip('/')
            if path.match(clean_pattern):
                return True

        return False

    def check(self, file_path: str, content: str, context: Dict[str, Any]) -> List[RuleViolation]:
        """Execute rule check on file content."""
        if not self.enabled:
            return []

        if not self.matches_file(file_path):
            return []

        if self.checker is None:
            return []

        try:
            violations = self.checker(file_path, content, context, self)
            return violations if violations else []
        except Exception as e:
            # Log error but don't fail the entire check
            return [
                RuleViolation(
                    rule_id=self.rule_id,
                    rule_name=self.name,
                    severity=RuleSeverity.INFO,
                    category=self.category,
                    message=f"Rule check failed: {str(e)}",
                    file_path=file_path
                )
            ]


@dataclass
class RuleSet:
    """Collection of related rules."""
    name: str
    description: str
    rules: List[Rule] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_rule(self, rule: Rule):
        """Add a rule to the set."""
        self.rules.append(rule)

    def get_enabled_rules(self) -> List[Rule]:
        """Get all enabled rules in priority order."""
        if not self.enabled:
            return []

        return sorted(
            [r for r in self.rules if r.enabled],
            key=lambda r: r.priority,
            reverse=True
        )


class RulesEngine:
    """
    Code review rules engine.

    Manages rules, rule sets, and executes checks on code files.
    """

    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.rule_sets: Dict[str, RuleSet] = {}
        self._load_builtin_rules()

    def register_rule(self, rule: Rule):
        """Register a new rule."""
        self.rules[rule.rule_id] = rule

    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Get a rule by ID."""
        return self.rules.get(rule_id)

    def list_rules(
        self,
        category: Optional[RuleCategory] = None,
        severity: Optional[RuleSeverity] = None,
        enabled_only: bool = False
    ) -> List[Rule]:
        """List rules with optional filtering."""
        rules = list(self.rules.values())

        if category:
            rules = [r for r in rules if r.category == category]

        if severity:
            rules = [r for r in rules if r.severity == severity]

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return sorted(rules, key=lambda r: (r.priority, r.rule_id), reverse=True)

    def register_rule_set(self, rule_set: RuleSet):
        """Register a rule set."""
        self.rule_sets[rule_set.name] = rule_set

        # Also register individual rules
        for rule in rule_set.rules:
            self.register_rule(rule)

    def get_rule_set(self, name: str) -> Optional[RuleSet]:
        """Get a rule set by name."""
        return self.rule_sets.get(name)

    def check_file(
        self,
        file_path: str,
        content: str,
        context: Optional[Dict[str, Any]] = None,
        rule_ids: Optional[List[str]] = None
    ) -> List[RuleViolation]:
        """
        Check a file against rules.

        Args:
            file_path: Path to the file
            content: File content
            context: Additional context for rules
            rule_ids: Specific rules to check (all enabled if None)

        Returns:
            List of violations found
        """
        context = context or {}
        violations = []

        # Determine which rules to run
        if rule_ids:
            rules = [self.rules[rid] for rid in rule_ids if rid in self.rules]
        else:
            rules = self.list_rules(enabled_only=True)

        # Run each rule
        for rule in rules:
            rule_violations = rule.check(file_path, content, context)
            violations.extend(rule_violations)

        return violations

    def check_files(
        self,
        files: Dict[str, str],
        context: Optional[Dict[str, Any]] = None,
        rule_ids: Optional[List[str]] = None
    ) -> Dict[str, List[RuleViolation]]:
        """
        Check multiple files.

        Args:
            files: Dictionary mapping file paths to content
            context: Additional context for rules
            rule_ids: Specific rules to check

        Returns:
            Dictionary mapping file paths to violations
        """
        results = {}

        for file_path, content in files.items():
            violations = self.check_file(file_path, content, context, rule_ids)
            if violations:
                results[file_path] = violations

        return results

    def export_rules(self, output_path: Path):
        """Export rules configuration to JSON."""
        data = {
            "rules": [
                {
                    "rule_id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity.value,
                    "category": r.category.value,
                    "enabled": r.enabled,
                    "priority": r.priority,
                    "file_patterns": r.file_patterns,
                    "exclude_patterns": r.exclude_patterns,
                    "metadata": r.metadata
                }
                for r in self.rules.values()
            ],
            "rule_sets": [
                {
                    "name": rs.name,
                    "description": rs.description,
                    "enabled": rs.enabled,
                    "rules": [r.rule_id for r in rs.rules],
                    "metadata": rs.metadata
                }
                for rs in self.rule_sets.values()
            ]
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

    def import_rules(self, input_path: Path):
        """Import rules configuration from JSON."""
        with open(input_path, "r") as f:
            data = json.load(f)

        # Import rules (without checkers - those must be registered separately)
        for rule_data in data.get("rules", []):
            rule = Rule(
                rule_id=rule_data["rule_id"],
                name=rule_data["name"],
                description=rule_data["description"],
                severity=RuleSeverity(rule_data["severity"]),
                category=RuleCategory(rule_data["category"]),
                enabled=rule_data.get("enabled", True),
                priority=rule_data.get("priority", 0),
                file_patterns=rule_data.get("file_patterns", ["**/*"]),
                exclude_patterns=rule_data.get("exclude_patterns", []),
                metadata=rule_data.get("metadata", {})
            )
            self.register_rule(rule)

        # Import rule sets
        for rs_data in data.get("rule_sets", []):
            rule_set = RuleSet(
                name=rs_data["name"],
                description=rs_data["description"],
                enabled=rs_data.get("enabled", True),
                metadata=rs_data.get("metadata", {})
            )

            # Add rules to set
            for rule_id in rs_data.get("rules", []):
                if rule_id in self.rules:
                    rule_set.add_rule(self.rules[rule_id])

            self.register_rule_set(rule_set)

    def _load_builtin_rules(self):
        """Load built-in rules."""
        # Security rules
        security_rules = RuleSet(
            name="security",
            description="Security-related rules"
        )

        # SQL Injection check
        security_rules.add_rule(Rule(
            rule_id="SEC001",
            name="SQL Injection Risk",
            description="Detect potential SQL injection vulnerabilities",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.SECURITY,
            file_patterns=["**/*.py", "**/*.js", "**/*.java"],
            checker=self._check_sql_injection
        ))

        # Hardcoded secrets
        security_rules.add_rule(Rule(
            rule_id="SEC002",
            name="Hardcoded Secrets",
            description="Detect hardcoded passwords, API keys, tokens",
            severity=RuleSeverity.CRITICAL,
            category=RuleCategory.SECURITY,
            checker=self._check_hardcoded_secrets
        ))

        self.register_rule_set(security_rules)

        # Style rules
        style_rules = RuleSet(
            name="style",
            description="Code style rules"
        )

        # Line length
        style_rules.add_rule(Rule(
            rule_id="STYLE001",
            name="Line Too Long",
            description="Lines should not exceed 100 characters",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE,
            checker=self._check_line_length
        ))

        # Trailing whitespace
        style_rules.add_rule(Rule(
            rule_id="STYLE002",
            name="Trailing Whitespace",
            description="Lines should not have trailing whitespace",
            severity=RuleSeverity.LOW,
            category=RuleCategory.STYLE,
            checker=self._check_trailing_whitespace
        ))

        self.register_rule_set(style_rules)

        # Complexity rules
        complexity_rules = RuleSet(
            name="complexity",
            description="Code complexity rules"
        )

        # Function complexity
        complexity_rules.add_rule(Rule(
            rule_id="COMPLEX001",
            name="High Function Complexity",
            description="Functions should not be too complex",
            severity=RuleSeverity.MEDIUM,
            category=RuleCategory.COMPLEXITY,
            file_patterns=["**/*.py"],
            checker=self._check_function_complexity
        ))

        self.register_rule_set(complexity_rules)

    # Built-in rule checkers

    def _check_sql_injection(
        self,
        file_path: str,
        content: str,
        context: Dict[str, Any],
        rule: Rule
    ) -> List[RuleViolation]:
        """Check for SQL injection risks."""
        violations = []

        # Simple pattern matching for common SQL injection patterns
        patterns = [
            r'execute\s*\(\s*["\'].*%s.*["\']',  # execute("... %s ...")
            r'cursor\.execute\s*\(\s*f["\']',     # cursor.execute(f"...")
            r'["\'].*["\'].*\+',                  # "..." + variable (string concat)
            r'\+.*["\'].*["\']',                  # variable + "..."
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(RuleViolation(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        message="Potential SQL injection vulnerability detected",
                        file_path=file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="Use parameterized queries instead of string concatenation"
                    ))
                    break  # Only report once per line

        return violations

    def _check_hardcoded_secrets(
        self,
        file_path: str,
        content: str,
        context: Dict[str, Any],
        rule: Rule
    ) -> List[RuleViolation]:
        """Check for hardcoded secrets."""
        violations = []

        # Patterns for common secret indicators
        patterns = [
            (r'password\s*=\s*["\'][^"\']+["\']', "password"),
            (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "API key"),
            (r'secret\s*=\s*["\'][^"\']+["\']', "secret"),
            (r'token\s*=\s*["\'][^"\']+["\']', "token"),
        ]

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pattern, secret_type in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    violations.append(RuleViolation(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        message=f"Hardcoded {secret_type} detected",
                        file_path=file_path,
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion=f"Use environment variables or secure vaults for {secret_type}"
                    ))

        return violations

    def _check_line_length(
        self,
        file_path: str,
        content: str,
        context: Dict[str, Any],
        rule: Rule
    ) -> List[RuleViolation]:
        """Check line length."""
        violations = []
        max_length = rule.metadata.get("max_length", 100)

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > max_length:
                violations.append(RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    message=f"Line too long ({len(line)} > {max_length})",
                    file_path=file_path,
                    line_number=i,
                    suggestion="Break long lines into multiple lines"
                ))

        return violations

    def _check_trailing_whitespace(
        self,
        file_path: str,
        content: str,
        context: Dict[str, Any],
        rule: Rule
    ) -> List[RuleViolation]:
        """Check for trailing whitespace."""
        violations = []

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if line.rstrip() != line:
                violations.append(RuleViolation(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    message="Line has trailing whitespace",
                    file_path=file_path,
                    line_number=i,
                    suggestion="Remove trailing whitespace"
                ))

        return violations

    def _check_function_complexity(
        self,
        file_path: str,
        content: str,
        context: Dict[str, Any],
        rule: Rule
    ) -> List[RuleViolation]:
        """Check function complexity (Python only)."""
        violations = []
        max_complexity = rule.metadata.get("max_complexity", 10)

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Simple complexity calculation
                    complexity = self._calculate_complexity(node)

                    if complexity > max_complexity:
                        violations.append(RuleViolation(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            message=f"Function '{node.name}' has high complexity ({complexity} > {max_complexity})",
                            file_path=file_path,
                            line_number=node.lineno,
                            suggestion="Consider breaking down the function into smaller functions"
                        ))
        except SyntaxError:
            pass  # Skip files with syntax errors

        return violations

    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1  # Base complexity

        for child in ast.walk(node):
            # Count decision points
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        return complexity


# Global engine instance
_engine = None


def get_engine() -> RulesEngine:
    """Get or create the global rules engine instance."""
    global _engine
    if _engine is None:
        _engine = RulesEngine()
    return _engine
