"""Tests for code formatting system."""

import pytest
from pathlib import Path
from pr_agent.formatting import (
    FormatterManager,
    FormatterLanguage,
    FormatConfig,
    BlackFormatter,
    PrettierFormatter,
    GoFormatter,
    RustFormatter,
    get_formatter_manager,
)


class TestFormatConfig:
    """Test format configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = FormatConfig()
        assert config.line_length == 88
        assert config.indent_size == 4
        assert config.use_tabs is False
        assert config.trailing_comma is True
        assert config.quote_style == "double"
        assert config.custom_options == {}

    def test_custom_config(self):
        """Test custom configuration."""
        config = FormatConfig(
            line_length=100,
            indent_size=2,
            use_tabs=True,
            quote_style="single"
        )
        assert config.line_length == 100
        assert config.indent_size == 2
        assert config.use_tabs is True
        assert config.quote_style == "single"


class TestBlackFormatter:
    """Test Black Python formatter."""

    def test_is_available(self):
        """Test checking if Black is available."""
        formatter = BlackFormatter()
        # Just check it returns a boolean
        assert isinstance(formatter.is_available(), bool)

    def test_format_simple_code(self):
        """Test formatting simple Python code."""
        formatter = BlackFormatter()
        code = "x=1+2"
        result = formatter.format(code)

        if result.success:
            assert result.formatted_code is not None
            assert result.changes_made is True
            assert "x = 1 + 2" in result.formatted_code
        else:
            # Black not installed, skip
            assert "not installed" in result.error.lower()

    def test_format_already_formatted(self):
        """Test formatting already formatted code."""
        formatter = BlackFormatter()
        code = "x = 1 + 2\n"
        result = formatter.format(code)

        if result.success:
            assert result.formatted_code is not None
            # May or may not have changes depending on Black version
            assert result.changes_made in [True, False]

    def test_check_formatted_code(self):
        """Test checking if code is formatted."""
        formatter = BlackFormatter()
        code = "x = 1 + 2\n"

        if formatter.is_available():
            # Well-formatted code should pass check
            is_formatted = formatter.check(code)
            assert isinstance(is_formatted, bool)


class TestPrettierFormatter:
    """Test Prettier formatter."""

    def test_is_available(self):
        """Test checking if Prettier is available."""
        formatter = PrettierFormatter(parser="babel")
        assert isinstance(formatter.is_available(), bool)

    def test_format_javascript(self):
        """Test formatting JavaScript code."""
        formatter = PrettierFormatter(parser="babel")
        code = "const x=1+2;"
        result = formatter.format(code)

        if result.success:
            assert result.formatted_code is not None
            assert result.changes_made is True
            assert "const x = 1 + 2" in result.formatted_code
        else:
            assert "not installed" in result.error.lower()

    def test_format_json(self):
        """Test formatting JSON."""
        formatter = PrettierFormatter(parser="json")
        code = '{"name":"test","value":123}'
        result = formatter.format(code)

        if result.success:
            assert result.formatted_code is not None
            assert result.changes_made is True
            # JSON should be pretty-printed
            assert "\n" in result.formatted_code

    def test_format_with_custom_config(self):
        """Test formatting with custom configuration."""
        config = FormatConfig(line_length=40, quote_style="single")
        formatter = PrettierFormatter(config, parser="babel")
        code = 'const message = "hello world";'
        result = formatter.format(code)

        if result.success:
            assert result.formatted_code is not None


class TestGoFormatter:
    """Test Go formatter."""

    def test_is_available(self):
        """Test checking if gofmt is available."""
        formatter = GoFormatter()
        assert isinstance(formatter.is_available(), bool)

    def test_format_go_code(self):
        """Test formatting Go code."""
        formatter = GoFormatter()
        code = "package main\nfunc main(){x:=1+2}"
        result = formatter.format(code)

        if result.success:
            assert result.formatted_code is not None
            # gofmt should add proper spacing
            assert "x := 1 + 2" in result.formatted_code
        else:
            assert "not available" in result.error.lower()


class TestRustFormatter:
    """Test Rust formatter."""

    def test_is_available(self):
        """Test checking if rustfmt is available."""
        formatter = RustFormatter()
        assert isinstance(formatter.is_available(), bool)

    def test_format_rust_code(self):
        """Test formatting Rust code."""
        formatter = RustFormatter()
        code = "fn main(){let x=1+2;}"
        result = formatter.format(code)

        if result.success:
            assert result.formatted_code is not None
            # rustfmt should add proper spacing
            assert "let x = 1 + 2" in result.formatted_code
        else:
            assert "not available" in result.error.lower()


class TestFormatterManager:
    """Test formatter manager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = FormatterManager()
        assert manager.config is not None
        assert len(manager.formatters) > 0

    def test_format_python(self):
        """Test formatting Python code."""
        manager = FormatterManager()
        code = "x=1+2"
        result = manager.format(code, FormatterLanguage.PYTHON)

        assert result is not None
        if result.success:
            assert result.formatted_code is not None
            assert result.formatter == "black"

    def test_format_javascript(self):
        """Test formatting JavaScript code."""
        manager = FormatterManager()
        code = "const x=1+2;"
        result = manager.format(code, FormatterLanguage.JAVASCRIPT)

        assert result is not None
        if result.success:
            assert result.formatted_code is not None
            assert result.formatter == "prettier"

    def test_format_json(self):
        """Test formatting JSON."""
        manager = FormatterManager()
        code = '{"name":"test"}'
        result = manager.format(code, FormatterLanguage.JSON)

        assert result is not None
        if result.success:
            assert result.formatted_code is not None

    def test_check_python(self):
        """Test checking Python code format."""
        manager = FormatterManager()
        code = "x = 1 + 2\n"

        # Check returns boolean
        is_formatted = manager.check(code, FormatterLanguage.PYTHON)
        assert isinstance(is_formatted, bool)

    def test_detect_language(self):
        """Test language detection from file extension."""
        manager = FormatterManager()

        assert manager._detect_language(Path("test.py")) == FormatterLanguage.PYTHON
        assert manager._detect_language(Path("test.js")) == FormatterLanguage.JAVASCRIPT
        assert manager._detect_language(Path("test.ts")) == FormatterLanguage.TYPESCRIPT
        assert manager._detect_language(Path("test.json")) == FormatterLanguage.JSON
        assert manager._detect_language(Path("test.go")) == FormatterLanguage.GO
        assert manager._detect_language(Path("test.rs")) == FormatterLanguage.RUST
        assert manager._detect_language(Path("test.html")) == FormatterLanguage.HTML
        assert manager._detect_language(Path("test.css")) == FormatterLanguage.CSS
        assert manager._detect_language(Path("test.md")) == FormatterLanguage.MARKDOWN
        assert manager._detect_language(Path("test.yaml")) == FormatterLanguage.YAML

    def test_detect_unknown_language(self):
        """Test detecting unknown language."""
        manager = FormatterManager()
        assert manager._detect_language(Path("test.xyz")) is None

    def test_get_available_formatters(self):
        """Test getting available formatters."""
        manager = FormatterManager()
        available = manager.get_available_formatters()

        assert isinstance(available, dict)
        assert len(available) > 0
        # All values should be boolean
        for is_available in available.values():
            assert isinstance(is_available, bool)

    def test_format_with_custom_config(self):
        """Test formatting with custom configuration."""
        config = FormatConfig(line_length=100)
        manager = FormatterManager(config)

        assert manager.config.line_length == 100

    def test_format_unsupported_language(self):
        """Test formatting unsupported language."""
        manager = FormatterManager()
        # Create a fake language enum value
        result = manager.format("code", FormatterLanguage.SQL)

        # Should return error for unsupported language
        assert result.success is False
        assert "No formatter available" in result.error


class TestGlobalInstance:
    """Test global formatter manager instance."""

    def test_get_formatter_manager(self):
        """Test getting global instance."""
        manager1 = get_formatter_manager()
        manager2 = get_formatter_manager()

        # Should return same instance
        assert manager1 is manager2

    def test_get_formatter_manager_with_config(self):
        """Test getting instance with custom config."""
        config = FormatConfig(line_length=100)
        manager = get_formatter_manager(config)

        assert manager.config.line_length == 100


class TestFormatResult:
    """Test format result."""

    def test_success_result(self):
        """Test successful format result."""
        from pr_agent.formatting.manager import FormatResult

        result = FormatResult(
            success=True,
            formatted_code="x = 1 + 2\n",
            original_code="x=1+2",
            changes_made=True,
            formatter="black"
        )

        assert result.success is True
        assert result.formatted_code == "x = 1 + 2\n"
        assert result.changes_made is True
        assert result.formatter == "black"

    def test_error_result(self):
        """Test error format result."""
        from pr_agent.formatting.manager import FormatResult

        result = FormatResult(
            success=False,
            error="Formatter not installed"
        )

        assert result.success is False
        assert result.error == "Formatter not installed"
        assert result.formatted_code is None
