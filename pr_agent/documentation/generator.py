"""
Code documentation generation system.

This module provides automatic documentation generation from source code,
supporting multiple languages and documentation formats.
"""

import ast
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class DocLanguage(str, Enum):
    """Supported documentation languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"


class DocFormat(str, Enum):
    """Documentation output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    RST = "rst"
    JSON = "json"


@dataclass
class FunctionDoc:
    """Function documentation."""
    name: str
    signature: str
    docstring: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ClassDoc:
    """Class documentation."""
    name: str
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)
    methods: List[FunctionDoc] = field(default_factory=list)
    attributes: List[Dict[str, Any]] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    line_number: int = 0


@dataclass
class ModuleDoc:
    """Module documentation."""
    name: str
    file_path: str
    docstring: Optional[str] = None
    classes: List[ClassDoc] = field(default_factory=list)
    functions: List[FunctionDoc] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    constants: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class DocumentationResult:
    """Documentation generation result."""
    success: bool
    output_path: Optional[str] = None
    format: Optional[DocFormat] = None
    modules: List[ModuleDoc] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PythonDocExtractor:
    """Extract documentation from Python code."""

    def extract_module(self, file_path: str) -> ModuleDoc:
        """Extract documentation from a Python module."""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return ModuleDoc(
                name=Path(file_path).stem,
                file_path=file_path,
                docstring=f"Error parsing file: {e}"
            )

        module_doc = ModuleDoc(
            name=Path(file_path).stem,
            file_path=file_path,
            docstring=ast.get_docstring(tree)
        )

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                module_doc.classes.append(self._extract_class(node))
            elif isinstance(node, ast.FunctionDef):
                if not self._is_method(node, tree):
                    module_doc.functions.append(self._extract_function(node))
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module_doc.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        module_doc.imports.append(f"{node.module}.{alias.name}")
            elif isinstance(node, ast.Assign):
                if isinstance(node.targets[0], ast.Name):
                    name = node.targets[0].id
                    if name.isupper():  # Likely a constant
                        module_doc.constants.append({
                            'name': name,
                            'line': node.lineno
                        })

        return module_doc

    def _extract_class(self, node: ast.ClassDef) -> ClassDoc:
        """Extract class documentation."""
        class_doc = ClassDoc(
            name=node.name,
            docstring=ast.get_docstring(node),
            bases=[self._get_name(base) for base in node.bases],
            decorators=[self._get_name(dec) for dec in node.decorator_list],
            line_number=node.lineno
        )

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                class_doc.methods.append(self._extract_function(item))
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_doc.attributes.append({
                            'name': target.id,
                            'line': item.lineno
                        })

        return class_doc

    def _extract_function(self, node: ast.FunctionDef) -> FunctionDoc:
        """Extract function documentation."""
        # Build signature
        args = []
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                arg_str += f": {self._get_name(arg.annotation)}"
            args.append(arg_str)

        signature = f"{node.name}({', '.join(args)})"
        if node.returns:
            signature += f" -> {self._get_name(node.returns)}"

        # Extract parameters
        parameters = []
        for arg in node.args.args:
            param = {'name': arg.arg}
            if arg.annotation:
                param['type'] = self._get_name(arg.annotation)
            parameters.append(param)

        return FunctionDoc(
            name=node.name,
            signature=signature,
            docstring=ast.get_docstring(node),
            parameters=parameters,
            return_type=self._get_name(node.returns) if node.returns else None,
            decorators=[self._get_name(dec) for dec in node.decorator_list],
            line_number=node.lineno
        )

    def _get_name(self, node: ast.AST) -> str:
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            return f"{self._get_name(node.value)}[{self._get_name(node.slice)}]"
        elif isinstance(node, ast.Constant):
            return str(node.value)
        return ast.unparse(node)

    def _is_method(self, node: ast.FunctionDef, tree: ast.AST) -> bool:
        """Check if function is a method."""
        for parent in ast.walk(tree):
            if isinstance(parent, ast.ClassDef):
                if node in parent.body:
                    return True
        return False


class DocumentationGenerator:
    """Generate documentation from source code."""

    def __init__(self):
        self.extractors = {
            DocLanguage.PYTHON: PythonDocExtractor()
        }

    def generate_docs(
        self,
        directory: str,
        output_dir: str,
        language: DocLanguage = DocLanguage.PYTHON,
        format: DocFormat = DocFormat.MARKDOWN,
        patterns: Optional[List[str]] = None
    ) -> DocumentationResult:
        """Generate documentation for a directory."""
        result = DocumentationResult(success=True, format=format)

        # Find files
        files = self._find_files(directory, language, patterns)
        if not files:
            result.success = False
            result.errors.append(f"No {language} files found in {directory}")
            return result

        # Extract documentation
        extractor = self.extractors.get(language)
        if not extractor:
            result.success = False
            result.errors.append(f"No extractor for language: {language}")
            return result

        for file_path in files:
            try:
                module_doc = extractor.extract_module(file_path)
                result.modules.append(module_doc)
            except Exception as e:
                result.warnings.append(f"Error extracting {file_path}: {e}")

        # Generate output
        try:
            os.makedirs(output_dir, exist_ok=True)

            if format == DocFormat.MARKDOWN:
                output_path = self._generate_markdown(result.modules, output_dir)
            elif format == DocFormat.HTML:
                output_path = self._generate_html(result.modules, output_dir)
            elif format == DocFormat.RST:
                output_path = self._generate_rst(result.modules, output_dir)
            elif format == DocFormat.JSON:
                output_path = self._generate_json(result.modules, output_dir)
            else:
                result.success = False
                result.errors.append(f"Unsupported format: {format}")
                return result

            result.output_path = output_path
        except Exception as e:
            result.success = False
            result.errors.append(f"Error generating documentation: {e}")

        return result

    def generate_api_docs(
        self,
        directory: str,
        output_dir: str,
        language: DocLanguage = DocLanguage.PYTHON
    ) -> DocumentationResult:
        """Generate API documentation."""
        result = DocumentationResult(success=True, format=DocFormat.HTML)

        try:
            os.makedirs(output_dir, exist_ok=True)

            if language == DocLanguage.PYTHON:
                # Use Sphinx
                self._generate_sphinx_docs(directory, output_dir)
                result.output_path = os.path.join(output_dir, "index.html")
            elif language in (DocLanguage.JAVASCRIPT, DocLanguage.TYPESCRIPT):
                # Use JSDoc
                self._generate_jsdoc_docs(directory, output_dir)
                result.output_path = os.path.join(output_dir, "index.html")
            elif language == DocLanguage.GO:
                # Use godoc
                self._generate_godoc_docs(directory, output_dir)
                result.output_path = os.path.join(output_dir, "index.html")
            else:
                result.success = False
                result.errors.append(f"API docs not supported for: {language}")
        except Exception as e:
            result.success = False
            result.errors.append(f"Error generating API docs: {e}")

        return result

    def _find_files(
        self,
        directory: str,
        language: DocLanguage,
        patterns: Optional[List[str]] = None
    ) -> List[str]:
        """Find source files."""
        extensions = {
            DocLanguage.PYTHON: ['.py'],
            DocLanguage.JAVASCRIPT: ['.js'],
            DocLanguage.TYPESCRIPT: ['.ts'],
            DocLanguage.GO: ['.go'],
            DocLanguage.RUST: ['.rs'],
            DocLanguage.JAVA: ['.java']
        }

        exts = extensions.get(language, [])
        files = []

        for root, _, filenames in os.walk(directory):
            for filename in filenames:
                if any(filename.endswith(ext) for ext in exts):
                    file_path = os.path.join(root, filename)
                    if patterns:
                        if any(re.search(pattern, file_path) for pattern in patterns):
                            files.append(file_path)
                    else:
                        files.append(file_path)

        return files

    def _generate_markdown(self, modules: List[ModuleDoc], output_dir: str) -> str:
        """Generate Markdown documentation."""
        output_path = os.path.join(output_dir, "API.md")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# API Documentation\n\n")
            f.write(f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n")

            for module in modules:
                f.write(f"## Module: {module.name}\n\n")
                if module.docstring:
                    f.write(f"{module.docstring}\n\n")

                # Classes
                if module.classes:
                    f.write("### Classes\n\n")
                    for cls in module.classes:
                        f.write(f"#### {cls.name}\n\n")
                        if cls.docstring:
                            f.write(f"{cls.docstring}\n\n")

                        if cls.bases:
                            f.write(f"**Bases:** {', '.join(cls.bases)}\n\n")

                        if cls.methods:
                            f.write("**Methods:**\n\n")
                            for method in cls.methods:
                                f.write(f"- `{method.signature}`\n")
                                if method.docstring:
                                    f.write(f"  {method.docstring.split(chr(10))[0]}\n")
                            f.write("\n")

                # Functions
                if module.functions:
                    f.write("### Functions\n\n")
                    for func in module.functions:
                        f.write(f"#### {func.signature}\n\n")
                        if func.docstring:
                            f.write(f"{func.docstring}\n\n")

        return output_path

    def _generate_html(self, modules: List[ModuleDoc], output_dir: str) -> str:
        """Generate HTML documentation."""
        output_path = os.path.join(output_dir, "index.html")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("<!DOCTYPE html>\n<html>\n<head>\n")
            f.write("<title>API Documentation</title>\n")
            f.write("<style>body{font-family:sans-serif;margin:40px;}</style>\n")
            f.write("</head>\n<body>\n")
            f.write("<h1>API Documentation</h1>\n")

            for module in modules:
                f.write(f"<h2>Module: {module.name}</h2>\n")
                if module.docstring:
                    f.write(f"<p>{module.docstring}</p>\n")

                if module.classes:
                    f.write("<h3>Classes</h3>\n")
                    for cls in module.classes:
                        f.write(f"<h4>{cls.name}</h4>\n")
                        if cls.docstring:
                            f.write(f"<p>{cls.docstring}</p>\n")

            f.write("</body>\n</html>")

        return output_path

    def _generate_rst(self, modules: List[ModuleDoc], output_dir: str) -> str:
        """Generate reStructuredText documentation."""
        output_path = os.path.join(output_dir, "index.rst")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("API Documentation\n")
            f.write("=================\n\n")

            for module in modules:
                f.write(f"{module.name}\n")
                f.write("-" * len(module.name) + "\n\n")
                if module.docstring:
                    f.write(f"{module.docstring}\n\n")

        return output_path

    def _generate_json(self, modules: List[ModuleDoc], output_dir: str) -> str:
        """Generate JSON documentation."""
        import json

        output_path = os.path.join(output_dir, "api.json")

        data = []
        for module in modules:
            module_data = {
                'name': module.name,
                'file_path': module.file_path,
                'docstring': module.docstring,
                'classes': [
                    {
                        'name': cls.name,
                        'docstring': cls.docstring,
                        'bases': cls.bases,
                        'methods': [
                            {
                                'name': m.name,
                                'signature': m.signature,
                                'docstring': m.docstring
                            }
                            for m in cls.methods
                        ]
                    }
                    for cls in module.classes
                ],
                'functions': [
                    {
                        'name': f.name,
                        'signature': f.signature,
                        'docstring': f.docstring
                    }
                    for f in module.functions
                ]
            }
            data.append(module_data)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        return output_path

    def _generate_sphinx_docs(self, directory: str, output_dir: str):
        """Generate Sphinx documentation."""
        # Create conf.py
        conf_path = os.path.join(output_dir, "conf.py")
        with open(conf_path, 'w') as f:
            f.write("project = 'API Documentation'\n")
            f.write("extensions = ['sphinx.ext.autodoc']\n")

        # Run sphinx-build
        subprocess.run(
            ['sphinx-build', '-b', 'html', directory, output_dir],
            check=False,
            capture_output=True
        )

    def _generate_jsdoc_docs(self, directory: str, output_dir: str):
        """Generate JSDoc documentation."""
        subprocess.run(
            ['jsdoc', '-d', output_dir, '-r', directory],
            check=False,
            capture_output=True
        )

    def _generate_godoc_docs(self, directory: str, output_dir: str):
        """Generate godoc documentation."""
        subprocess.run(
            ['godoc', '-html', directory],
            check=False,
            capture_output=True
        )


# Global instance
_doc_generator = None


def get_doc_generator() -> DocumentationGenerator:
    """Get global documentation generator instance."""
    global _doc_generator
    if _doc_generator is None:
        _doc_generator = DocumentationGenerator()
    return _doc_generator
