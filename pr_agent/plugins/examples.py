"""
Example plugins demonstrating the plugin system.

These plugins can be used as templates for creating custom plugins.
"""

import re
from typing import Any, Dict, List

from pr_agent.plugins import AnalyzerPlugin, NotificationPlugin, ReviewRulePlugin


class SecurityReviewRule(ReviewRulePlugin):
    """Check for common security issues in code."""

    version = "1.0.0"
    description = "Detects common security vulnerabilities"
    author = "PR Agent Team"

    def initialize(self) -> bool:
        self.patterns = {
            "hardcoded_password": r'password\s*=\s*["\'][^"\']+["\']',
            "sql_injection": r"execute\s*\(\s*[\"'].*%s.*[\"']",
            "eval_usage": r"\beval\s*\(",
            "exec_usage": r"\bexec\s*\(",
            "pickle_usage": r"pickle\.loads?\s*\(",
        }
        return True

    def cleanup(self):
        pass

    def evaluate(self, pr_data: Dict[str, Any], diff: str) -> Dict[str, Any]:
        issues = []
        severity = "info"

        for issue_type, pattern in self.patterns.items():
            matches = re.finditer(pattern, diff, re.IGNORECASE)
            for match in matches:
                issues.append(
                    {
                        "type": issue_type,
                        "line": diff[: match.start()].count("\n") + 1,
                        "code": match.group(0),
                    }
                )

        if issues:
            severity = "error" if len(issues) > 3 else "warning"

        return {
            "passed": len(issues) == 0,
            "severity": severity,
            "message": f"Found {len(issues)} potential security issues"
            if issues
            else "No security issues detected",
            "suggestions": [
                f"Review {issue['type']} at line {issue['line']}" for issue in issues
            ],
        }


class CodeComplexityAnalyzer(AnalyzerPlugin):
    """Analyze code complexity metrics."""

    version = "1.0.0"
    description = "Calculates code complexity metrics"
    author = "PR Agent Team"

    def initialize(self) -> bool:
        return True

    def cleanup(self):
        pass

    def analyze(
        self, file_path: str, content: str, language: str
    ) -> Dict[str, Any]:
        lines = content.split("\n")
        code_lines = [
            line for line in lines if line.strip() and not line.strip().startswith("#")
        ]

        # Simple complexity metrics
        metrics = {
            "total_lines": len(lines),
            "code_lines": len(code_lines),
            "blank_lines": len(lines) - len(code_lines),
            "comment_lines": len(
                [line for line in lines if line.strip().startswith("#")]
            ),
        }

        # Calculate cyclomatic complexity (simplified)
        complexity_keywords = ["if", "elif", "else", "for", "while", "try", "except"]
        complexity = 1  # Base complexity
        for line in code_lines:
            for keyword in complexity_keywords:
                if re.search(rf"\b{keyword}\b", line):
                    complexity += 1

        metrics["cyclomatic_complexity"] = complexity

        # Generate suggestions
        suggestions = []
        if complexity > 10:
            suggestions.append(
                f"High complexity ({complexity}). Consider refactoring."
            )
        if len(code_lines) > 300:
            suggestions.append(
                f"Large file ({len(code_lines)} lines). Consider splitting."
            )

        # Identify issues
        issues = []
        if complexity > 15:
            issues.append(
                {
                    "severity": "warning",
                    "message": f"Very high cyclomatic complexity: {complexity}",
                    "suggestion": "Break down complex functions into smaller ones",
                }
            )

        return {"issues": issues, "metrics": metrics, "suggestions": suggestions}


class CustomWebhookNotification(NotificationPlugin):
    """Send notifications to custom webhook endpoint."""

    version = "1.0.0"
    description = "Sends notifications to custom webhook"
    author = "PR Agent Team"

    def initialize(self) -> bool:
        self.webhook_url = self.config.get("webhook_url")
        if not self.webhook_url:
            return False
        return True

    def cleanup(self):
        pass

    async def send_notification(
        self, event_type: str, data: Dict[str, Any]
    ) -> bool:
        import aiohttp

        try:
            payload = {
                "event": event_type,
                "timestamp": data.get("timestamp"),
                "repository": data.get("repository"),
                "pr_number": data.get("pr_number"),
                "author": data.get("author"),
                "title": data.get("title"),
                "url": data.get("url"),
                "status": data.get("status"),
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url, json=payload, timeout=10
                ) as response:
                    return response.status == 200

        except Exception as e:
            return False


class LargeFileReviewRule(ReviewRulePlugin):
    """Check for large files in PR."""

    version = "1.0.0"
    description = "Detects large files that may need review"
    author = "PR Agent Team"

    def initialize(self) -> bool:
        self.max_lines = self.config.get("max_lines", 500)
        return True

    def cleanup(self):
        pass

    def evaluate(self, pr_data: Dict[str, Any], diff: str) -> Dict[str, Any]:
        # Parse diff to find file sizes
        large_files = []
        current_file = None
        line_count = 0

        for line in diff.split("\n"):
            if line.startswith("diff --git"):
                if current_file and line_count > self.max_lines:
                    large_files.append({"file": current_file, "lines": line_count})
                # Extract filename
                match = re.search(r"b/(.+)$", line)
                current_file = match.group(1) if match else None
                line_count = 0
            elif line.startswith("+") and not line.startswith("+++"):
                line_count += 1

        # Check last file
        if current_file and line_count > self.max_lines:
            large_files.append({"file": current_file, "lines": line_count})

        return {
            "passed": len(large_files) == 0,
            "severity": "warning" if large_files else "info",
            "message": f"Found {len(large_files)} large files"
            if large_files
            else "No large files detected",
            "suggestions": [
                f"Consider splitting {f['file']} ({f['lines']} lines)"
                for f in large_files
            ],
        }


class TestCoverageAnalyzer(AnalyzerPlugin):
    """Analyze test coverage in code."""

    version = "1.0.0"
    description = "Checks for test coverage"
    author = "PR Agent Team"

    def initialize(self) -> bool:
        return True

    def cleanup(self):
        pass

    def analyze(
        self, file_path: str, content: str, language: str
    ) -> Dict[str, Any]:
        # Check if this is a test file
        is_test_file = any(
            pattern in file_path.lower()
            for pattern in ["test_", "_test.", "tests/", "/test/"]
        )

        # Count functions/methods
        function_pattern = r"^\s*def\s+(\w+)\s*\("
        functions = re.findall(function_pattern, content, re.MULTILINE)

        # Count test functions
        test_functions = [f for f in functions if f.startswith("test_")]

        metrics = {
            "is_test_file": is_test_file,
            "total_functions": len(functions),
            "test_functions": len(test_functions),
        }

        issues = []
        suggestions = []

        if not is_test_file and len(functions) > 5:
            suggestions.append(
                f"Consider adding tests for {len(functions)} functions in this file"
            )
            issues.append(
                {
                    "severity": "info",
                    "message": "No corresponding test file found",
                    "suggestion": f"Create test file: test_{file_path.split('/')[-1]}",
                }
            )

        return {"issues": issues, "metrics": metrics, "suggestions": suggestions}
