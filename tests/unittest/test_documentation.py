"""Tests for documentation generation system."""

import json
import os
import tempfile
from pathlib import Path

import pytest

from pr_agent.documentation import (
    ClassDoc,
    DocFormat,
    DocLanguage,
    DocumentationGenerator,
    FunctionDoc,
    ModuleDoc,
    PythonDocExtractor,
    get_doc_generator,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_python_file(temp_dir):
    """Create sample Python file."""
    file_path = os.path.join(temp_dir, "sample.py")
    with open(file_path, 'w') as f:
        f.write('''"""Sample module for testing."""

import os
from typing import List

MAX_SIZE = 100

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        """Initialize calculator."""
        self.result = 0

    def add(self, a: int, b: int) -> int:
        """Add two numbers.

        Args:
            a: First number
            b: Second number

        Returns:
            Sum of a and b
        """
        return a + b

    def subtract(self, a: int, b: int) -> int:
        """Subtract b from a."""
        return a - b

def greet(name: str) -> str:
    """Greet a person.

    Args:
        name: Person's name

    Returns:
        Greeting message
    """
    return f"Hello, {name}!"
''')
    return file_path


class TestPythonDocExtractor:
    """Test Python documentation extractor."""

    def test_extract_module(self, sample_python_file):
        """Test module extraction."""
        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(sample_python_file)

        assert module_doc.name == "sample"
        assert module_doc.docstring == "Sample module for testing."
        assert len(module_doc.classes) == 1
        assert len(module_doc.functions) == 1
        assert len(module_doc.imports) >= 2
        assert len(module_doc.constants) == 1

    def test_extract_class(self, sample_python_file):
        """Test class extraction."""
        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(sample_python_file)

        cls = module_doc.classes[0]
        assert cls.name == "Calculator"
        assert cls.docstring == "A simple calculator class."
        assert len(cls.methods) == 3  # __init__, add, subtract

    def test_extract_function(self, sample_python_file):
        """Test function extraction."""
        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(sample_python_file)

        func = module_doc.functions[0]
        assert func.name == "greet"
        assert "name: str" in func.signature
        assert func.return_type == "str"
        assert func.docstring.startswith("Greet a person")

    def test_extract_method_signature(self, sample_python_file):
        """Test method signature extraction."""
        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(sample_python_file)

        cls = module_doc.classes[0]
        add_method = next(m for m in cls.methods if m.name == "add")

        assert "a: int" in add_method.signature
        assert "b: int" in add_method.signature
        assert add_method.return_type == "int"

    def test_extract_imports(self, sample_python_file):
        """Test import extraction."""
        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(sample_python_file)

        assert "os" in module_doc.imports
        assert any("typing" in imp for imp in module_doc.imports)

    def test_extract_constants(self, sample_python_file):
        """Test constant extraction."""
        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(sample_python_file)

        assert len(module_doc.constants) == 1
        assert module_doc.constants[0]['name'] == "MAX_SIZE"

    def test_syntax_error_handling(self, temp_dir):
        """Test handling of syntax errors."""
        file_path = os.path.join(temp_dir, "invalid.py")
        with open(file_path, 'w') as f:
            f.write("def invalid(\n")  # Syntax error

        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(file_path)

        assert "Error parsing file" in module_doc.docstring


class TestDocumentationGenerator:
    """Test documentation generator."""

    def test_generate_markdown_docs(self, temp_dir, sample_python_file):
        """Test Markdown documentation generation."""
        generator = DocumentationGenerator()
        output_dir = os.path.join(temp_dir, "docs")

        result = generator.generate_docs(
            temp_dir,
            output_dir,
            language=DocLanguage.PYTHON,
            format=DocFormat.MARKDOWN
        )

        assert result.success
        assert result.output_path
        assert os.path.exists(result.output_path)
        assert len(result.modules) == 1

        # Check content
        with open(result.output_path, 'r') as f:
            content = f.read()
            assert "# API Documentation" in content
            assert "Calculator" in content
            assert "greet" in content

    def test_generate_html_docs(self, temp_dir, sample_python_file):
        """Test HTML documentation generation."""
        generator = DocumentationGenerator()
        output_dir = os.path.join(temp_dir, "docs")

        result = generator.generate_docs(
            temp_dir,
            output_dir,
            language=DocLanguage.PYTHON,
            format=DocFormat.HTML
        )

        assert result.success
        assert result.output_path
        assert os.path.exists(result.output_path)

        # Check content
        with open(result.output_path, 'r') as f:
            content = f.read()
            assert "<!DOCTYPE html>" in content
            assert "Calculator" in content

    def test_generate_rst_docs(self, temp_dir, sample_python_file):
        """Test reStructuredText documentation generation."""
        generator = DocumentationGenerator()
        output_dir = os.path.join(temp_dir, "docs")

        result = generator.generate_docs(
            temp_dir,
            output_dir,
            language=DocLanguage.PYTHON,
            format=DocFormat.RST
        )

        assert result.success
        assert result.output_path
        assert os.path.exists(result.output_path)

    def test_generate_json_docs(self, temp_dir, sample_python_file):
        """Test JSON documentation generation."""
        generator = DocumentationGenerator()
        output_dir = os.path.join(temp_dir, "docs")

        result = generator.generate_docs(
            temp_dir,
            output_dir,
            language=DocLanguage.PYTHON,
            format=DocFormat.JSON
        )

        assert result.success
        assert result.output_path
        assert os.path.exists(result.output_path)

        # Check content
        with open(result.output_path, 'r') as f:
            data = json.load(f)
            assert len(data) == 1
            assert data[0]['name'] == "sample"
            assert len(data[0]['classes']) == 1
            assert len(data[0]['functions']) == 1

    def test_no_files_found(self, temp_dir):
        """Test handling when no files are found."""
        generator = DocumentationGenerator()
        output_dir = os.path.join(temp_dir, "docs")

        result = generator.generate_docs(
            temp_dir,
            output_dir,
            language=DocLanguage.PYTHON
        )

        assert not result.success
        assert len(result.errors) > 0

    def test_unsupported_language(self, temp_dir, sample_python_file):
        """Test unsupported language handling."""
        generator = DocumentationGenerator()
        output_dir = os.path.join(temp_dir, "docs")

        # Manually set unsupported language
        result = generator.generate_docs(
            temp_dir,
            output_dir,
            language=DocLanguage.JAVA  # No extractor for Java yet
        )

        assert not result.success
        assert len(result.errors) > 0
        # Should fail because no Java files found or no extractor
        assert any("files found" in err.lower() or "extractor" in err.lower() for err in result.errors)

    def test_file_patterns(self, temp_dir):
        """Test file pattern filtering."""
        # Create multiple files
        for i in range(3):
            file_path = os.path.join(temp_dir, f"file{i}.py")
            with open(file_path, 'w') as f:
                f.write(f'"""Module {i}."""\n')

        generator = DocumentationGenerator()
        output_dir = os.path.join(temp_dir, "docs")

        result = generator.generate_docs(
            temp_dir,
            output_dir,
            language=DocLanguage.PYTHON,
            patterns=[r"file[01]\.py"]  # Only file0 and file1
        )

        assert result.success
        assert len(result.modules) == 2

    def test_get_doc_generator(self):
        """Test global instance getter."""
        gen1 = get_doc_generator()
        gen2 = get_doc_generator()

        assert gen1 is gen2  # Same instance


class TestDataClasses:
    """Test data classes."""

    def test_function_doc(self):
        """Test FunctionDoc creation."""
        func = FunctionDoc(
            name="test_func",
            signature="test_func(a: int) -> str",
            docstring="Test function",
            parameters=[{'name': 'a', 'type': 'int'}],
            return_type="str",
            line_number=10
        )

        assert func.name == "test_func"
        assert func.return_type == "str"
        assert len(func.parameters) == 1

    def test_class_doc(self):
        """Test ClassDoc creation."""
        cls = ClassDoc(
            name="TestClass",
            docstring="Test class",
            bases=["BaseClass"],
            line_number=5
        )

        assert cls.name == "TestClass"
        assert len(cls.bases) == 1
        assert len(cls.methods) == 0

    def test_module_doc(self):
        """Test ModuleDoc creation."""
        module = ModuleDoc(
            name="test_module",
            file_path="/path/to/module.py",
            docstring="Test module"
        )

        assert module.name == "test_module"
        assert len(module.classes) == 0
        assert len(module.functions) == 0

    def test_documentation_result(self):
        """Test DocumentationResult creation."""
        from pr_agent.documentation.generator import DocumentationResult

        result = DocumentationResult(
            success=True,
            output_path="/path/to/output",
            format=DocFormat.MARKDOWN
        )

        assert result.success
        assert result.format == DocFormat.MARKDOWN
        assert result.generated_at  # Should have timestamp


class TestComplexCode:
    """Test with more complex code structures."""

    def test_nested_classes(self, temp_dir):
        """Test nested class handling."""
        file_path = os.path.join(temp_dir, "nested.py")
        with open(file_path, 'w') as f:
            f.write('''
class Outer:
    """Outer class."""

    class Inner:
        """Inner class."""
        pass
''')

        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(file_path)

        # Should extract both classes
        assert len(module_doc.classes) >= 1

    def test_decorators(self, temp_dir):
        """Test decorator extraction."""
        file_path = os.path.join(temp_dir, "decorated.py")
        with open(file_path, 'w') as f:
            f.write('''
@dataclass
class MyClass:
    """Decorated class."""

    @property
    def value(self):
        """Property method."""
        return 42
''')

        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(file_path)

        cls = module_doc.classes[0]
        assert len(cls.decorators) > 0

    def test_multiple_inheritance(self, temp_dir):
        """Test multiple inheritance."""
        file_path = os.path.join(temp_dir, "multi.py")
        with open(file_path, 'w') as f:
            f.write('''
class MyClass(Base1, Base2):
    """Class with multiple bases."""
    pass
''')

        extractor = PythonDocExtractor()
        module_doc = extractor.extract_module(file_path)

        cls = module_doc.classes[0]
        assert len(cls.bases) == 2
