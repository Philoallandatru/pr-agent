"""
Code formatting and beautification system.

Integrates multiple formatters for different languages and provides
unified interface for code formatting, checking, and auto-fixing.
"""

import logging
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
import json


logger = logging.getLogger(__name__)


class FormatterLanguage(str, Enum):
    """Supported languages for formatting."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    CPP = "cpp"
    HTML = "html"
    CSS = "css"
    SQL = "sql"


class FormatterTool(str, Enum):
    """Available formatter tools."""
    BLACK = "black"
    AUTOPEP8 = "autopep8"
    YAPF = "yapf"
    PRETTIER = "prettier"
    GOFMT = "gofmt"
    RUSTFMT = "rustfmt"
    CLANG_FORMAT = "clang-format"
    GOOGLE_JAVA_FORMAT = "google-java-format"
    SQLFORMAT = "sqlformat"


@dataclass
class FormatResult:
    """Result of formatting operation."""
    success: bool
    formatted_code: Optional[str] = None
    original_code: Optional[str] = None
    changes_made: bool = False
    error: Optional[str] = None
    formatter: Optional[str] = None
    diff: Optional[str] = None


@dataclass
class FormatConfig:
    """Formatter configuration."""
    line_length: int = 88
    indent_size: int = 4
    use_tabs: bool = False
    trailing_comma: bool = True
    quote_style: str = "double"  # single, double
    custom_options: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_options is None:
            self.custom_options = {}


class BaseFormatter:
    """Base class for code formatters."""

    def __init__(self, config: Optional[FormatConfig] = None):
        self.config = config or FormatConfig()

    def format(self, code: str, file_path: Optional[Path] = None) -> FormatResult:
        """Format code and return result."""
        raise NotImplementedError

    def check(self, code: str, file_path: Optional[Path] = None) -> bool:
        """Check if code is properly formatted."""
        result = self.format(code, file_path)
        return result.success and not result.changes_made

    def is_available(self) -> bool:
        """Check if formatter tool is available."""
        raise NotImplementedError


class BlackFormatter(BaseFormatter):
    """Python formatter using Black."""

    def is_available(self) -> bool:
        """Check if black is installed."""
        try:
            subprocess.run(
                ["black", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def format(self, code: str, file_path: Optional[Path] = None) -> FormatResult:
        """Format Python code with Black."""
        if not self.is_available():
            return FormatResult(
                success=False,
                error="Black is not installed. Install with: pip install black"
            )

        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = Path(f.name)

            try:
                # Run black
                result = subprocess.run(
                    [
                        "black",
                        "--line-length", str(self.config.line_length),
                        "--quiet",
                        str(temp_path)
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Read formatted code
                formatted_code = temp_path.read_text()

                # Check if changes were made
                changes_made = formatted_code != code

                return FormatResult(
                    success=True,
                    formatted_code=formatted_code,
                    original_code=code,
                    changes_made=changes_made,
                    formatter="black"
                )
            finally:
                # Clean up temp file
                temp_path.unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            return FormatResult(
                success=False,
                error="Black formatting timed out"
            )
        except Exception as e:
            logger.error(f"Black formatting failed: {e}")
            return FormatResult(
                success=False,
                error=str(e)
            )


class PrettierFormatter(BaseFormatter):
    """JavaScript/TypeScript/JSON/Markdown formatter using Prettier."""

    def __init__(self, config: Optional[FormatConfig] = None, parser: str = "babel"):
        super().__init__(config)
        self.parser = parser  # babel, typescript, json, markdown, yaml, html, css

    def is_available(self) -> bool:
        """Check if prettier is installed."""
        try:
            subprocess.run(
                ["prettier", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def format(self, code: str, file_path: Optional[Path] = None) -> FormatResult:
        """Format code with Prettier."""
        if not self.is_available():
            return FormatResult(
                success=False,
                error="Prettier is not installed. Install with: npm install -g prettier"
            )

        try:
            # Build prettier options
            options = [
                "prettier",
                "--parser", self.parser,
                "--print-width", str(self.config.line_length),
                "--tab-width", str(self.config.indent_size),
                "--use-tabs", str(self.config.use_tabs).lower(),
                "--trailing-comma", "all" if self.config.trailing_comma else "none",
                "--quote-props", "as-needed",
            ]

            if self.config.quote_style == "single":
                options.append("--single-quote")

            # Run prettier
            result = subprocess.run(
                options,
                input=code,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return FormatResult(
                    success=False,
                    error=result.stderr
                )

            formatted_code = result.stdout
            changes_made = formatted_code != code

            return FormatResult(
                success=True,
                formatted_code=formatted_code,
                original_code=code,
                changes_made=changes_made,
                formatter="prettier"
            )

        except subprocess.TimeoutExpired:
            return FormatResult(
                success=False,
                error="Prettier formatting timed out"
            )
        except Exception as e:
            logger.error(f"Prettier formatting failed: {e}")
            return FormatResult(
                success=False,
                error=str(e)
            )


class GoFormatter(BaseFormatter):
    """Go formatter using gofmt."""

    def is_available(self) -> bool:
        """Check if gofmt is available."""
        try:
            subprocess.run(
                ["gofmt", "-h"],
                capture_output=True,
                timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def format(self, code: str, file_path: Optional[Path] = None) -> FormatResult:
        """Format Go code with gofmt."""
        if not self.is_available():
            return FormatResult(
                success=False,
                error="gofmt is not available. Install Go toolchain."
            )

        try:
            result = subprocess.run(
                ["gofmt"],
                input=code,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return FormatResult(
                    success=False,
                    error=result.stderr
                )

            formatted_code = result.stdout
            changes_made = formatted_code != code

            return FormatResult(
                success=True,
                formatted_code=formatted_code,
                original_code=code,
                changes_made=changes_made,
                formatter="gofmt"
            )

        except subprocess.TimeoutExpired:
            return FormatResult(
                success=False,
                error="gofmt formatting timed out"
            )
        except Exception as e:
            logger.error(f"gofmt formatting failed: {e}")
            return FormatResult(
                success=False,
                error=str(e)
            )


class RustFormatter(BaseFormatter):
    """Rust formatter using rustfmt."""

    def is_available(self) -> bool:
        """Check if rustfmt is available."""
        try:
            subprocess.run(
                ["rustfmt", "--version"],
                capture_output=True,
                check=True,
                timeout=5
            )
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def format(self, code: str, file_path: Optional[Path] = None) -> FormatResult:
        """Format Rust code with rustfmt."""
        if not self.is_available():
            return FormatResult(
                success=False,
                error="rustfmt is not available. Install with: rustup component add rustfmt"
            )

        try:
            result = subprocess.run(
                ["rustfmt", "--emit=stdout"],
                input=code,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return FormatResult(
                    success=False,
                    error=result.stderr
                )

            formatted_code = result.stdout
            changes_made = formatted_code != code

            return FormatResult(
                success=True,
                formatted_code=formatted_code,
                original_code=code,
                changes_made=changes_made,
                formatter="rustfmt"
            )

        except subprocess.TimeoutExpired:
            return FormatResult(
                success=False,
                error="rustfmt formatting timed out"
            )
        except Exception as e:
            logger.error(f"rustfmt formatting failed: {e}")
            return FormatResult(
                success=False,
                error=str(e)
            )


class FormatterManager:
    """Manage code formatters for multiple languages."""

    def __init__(self, config: Optional[FormatConfig] = None):
        self.config = config or FormatConfig()
        self.formatters: Dict[FormatterLanguage, BaseFormatter] = {}
        self._register_formatters()

    def _register_formatters(self):
        """Register available formatters."""
        # Python
        self.formatters[FormatterLanguage.PYTHON] = BlackFormatter(self.config)

        # JavaScript/TypeScript
        self.formatters[FormatterLanguage.JAVASCRIPT] = PrettierFormatter(
            self.config, parser="babel"
        )
        self.formatters[FormatterLanguage.TYPESCRIPT] = PrettierFormatter(
            self.config, parser="typescript"
        )

        # JSON/YAML/Markdown
        self.formatters[FormatterLanguage.JSON] = PrettierFormatter(
            self.config, parser="json"
        )
        self.formatters[FormatterLanguage.YAML] = PrettierFormatter(
            self.config, parser="yaml"
        )
        self.formatters[FormatterLanguage.MARKDOWN] = PrettierFormatter(
            self.config, parser="markdown"
        )

        # HTML/CSS
        self.formatters[FormatterLanguage.HTML] = PrettierFormatter(
            self.config, parser="html"
        )
        self.formatters[FormatterLanguage.CSS] = PrettierFormatter(
            self.config, parser="css"
        )

        # Go
        self.formatters[FormatterLanguage.GO] = GoFormatter(self.config)

        # Rust
        self.formatters[FormatterLanguage.RUST] = RustFormatter(self.config)

    def format(
        self,
        code: str,
        language: FormatterLanguage,
        file_path: Optional[Path] = None
    ) -> FormatResult:
        """Format code for specified language."""
        formatter = self.formatters.get(language)
        if not formatter:
            return FormatResult(
                success=False,
                error=f"No formatter available for {language}"
            )

        return formatter.format(code, file_path)

    def format_file(self, file_path: Path) -> FormatResult:
        """Format a file based on its extension."""
        language = self._detect_language(file_path)
        if not language:
            return FormatResult(
                success=False,
                error=f"Cannot detect language for {file_path}"
            )

        code = file_path.read_text()
        return self.format(code, language, file_path)

    def check(
        self,
        code: str,
        language: FormatterLanguage,
        file_path: Optional[Path] = None
    ) -> bool:
        """Check if code is properly formatted."""
        formatter = self.formatters.get(language)
        if not formatter:
            return False

        return formatter.check(code, file_path)

    def check_file(self, file_path: Path) -> bool:
        """Check if a file is properly formatted."""
        language = self._detect_language(file_path)
        if not language:
            return False

        code = file_path.read_text()
        return self.check(code, language, file_path)

    def _detect_language(self, file_path: Path) -> Optional[FormatterLanguage]:
        """Detect language from file extension."""
        ext = file_path.suffix.lower()
        mapping = {
            ".py": FormatterLanguage.PYTHON,
            ".js": FormatterLanguage.JAVASCRIPT,
            ".jsx": FormatterLanguage.JAVASCRIPT,
            ".ts": FormatterLanguage.TYPESCRIPT,
            ".tsx": FormatterLanguage.TYPESCRIPT,
            ".json": FormatterLanguage.JSON,
            ".yaml": FormatterLanguage.YAML,
            ".yml": FormatterLanguage.YAML,
            ".md": FormatterLanguage.MARKDOWN,
            ".go": FormatterLanguage.GO,
            ".rs": FormatterLanguage.RUST,
            ".html": FormatterLanguage.HTML,
            ".css": FormatterLanguage.CSS,
            ".sql": FormatterLanguage.SQL,
        }
        return mapping.get(ext)

    def get_available_formatters(self) -> Dict[FormatterLanguage, bool]:
        """Get list of available formatters."""
        return {
            lang: formatter.is_available()
            for lang, formatter in self.formatters.items()
        }

    def format_multiple(
        self,
        files: List[Path]
    ) -> Dict[Path, FormatResult]:
        """Format multiple files."""
        results = {}
        for file_path in files:
            results[file_path] = self.format_file(file_path)
        return results


# Global instance
_formatter_manager: Optional[FormatterManager] = None


def get_formatter_manager(config: Optional[FormatConfig] = None) -> FormatterManager:
    """Get global formatter manager instance."""
    global _formatter_manager
    if _formatter_manager is None or config is not None:
        _formatter_manager = FormatterManager(config)
    return _formatter_manager
