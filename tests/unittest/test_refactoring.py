"""
Tests for code refactoring engine.
"""

import os
import tempfile
import unittest
from pathlib import Path

from pr_agent.refactoring import (
    RefactoringEngine,
    RefactoringType,
    RefactoringSeverity,
    get_refactoring_engine,
)


class TestSymbolRenamer(unittest.TestCase):
    """Test symbol renaming refactoring."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = RefactoringEngine()

        # Create test file
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
class OldClass:
    def method(self):
        pass

def use_old_class():
    obj = OldClass()
    return obj
""")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_rename_class(self):
        """Test renaming a class."""
        result = self.engine.rename_symbol(
            self.temp_dir,
            "OldClass",
            "NewClass"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.refactoring_type, RefactoringType.RENAME_SYMBOL)
        self.assertGreater(len(result.edits), 0)
        self.assertIn(self.test_file, result.affected_files)

    def test_rename_with_scope(self):
        """Test renaming with scope restriction."""
        result = self.engine.rename_symbol(
            self.temp_dir,
            "OldClass",
            "NewClass",
            scope=self.test_file
        )

        self.assertTrue(result.success)
        self.assertEqual(len(result.affected_files), 1)

    def test_rename_validation(self):
        """Test rename validation."""
        # Try to rename to a keyword
        result = self.engine.rename_symbol(
            self.temp_dir,
            "OldClass",
            "class"
        )

        self.assertTrue(result.success)  # Still returns result
        self.assertEqual(result.severity, RefactoringSeverity.UNSAFE)

    def test_rename_preview(self):
        """Test rename preview generation."""
        result = self.engine.rename_symbol(
            self.temp_dir,
            "OldClass",
            "NewClass"
        )

        self.assertIsNotNone(result.preview)
        self.assertIn("OldClass", result.preview)


class TestMethodExtractor(unittest.TestCase):
    """Test method extraction refactoring."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = RefactoringEngine()

        # Create test file
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
def complex_function():
    x = 10
    y = 20
    result = x + y
    print(result)
    return result
""")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_extract_method(self):
        """Test extracting a method."""
        result = self.engine.extract_method(
            self.test_file,
            4,  # Start line
            5,  # End line
            "calculate_sum"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.refactoring_type, RefactoringType.EXTRACT_METHOD)
        self.assertGreater(len(result.edits), 0)

    def test_extract_method_preview(self):
        """Test extract method preview."""
        result = self.engine.extract_method(
            self.test_file,
            4,
            5,
            "calculate_sum"
        )

        self.assertIsNotNone(result.preview)
        self.assertIn("calculate_sum", result.preview)


class TestVariableInliner(unittest.TestCase):
    """Test variable inlining refactoring."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = RefactoringEngine()

        # Create test file
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
def test_function():
    temp = 42
    result = temp * 2
    return result
""")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_inline_variable(self):
        """Test inlining a variable."""
        result = self.engine.inline_variable(
            self.test_file,
            "temp",
            3  # Line where temp is defined
        )

        self.assertTrue(result.success)
        self.assertEqual(result.refactoring_type, RefactoringType.INLINE_VARIABLE)
        self.assertGreater(len(result.edits), 0)

    def test_inline_variable_preview(self):
        """Test inline variable preview."""
        result = self.engine.inline_variable(
            self.test_file,
            "temp",
            3
        )

        self.assertIsNotNone(result.preview)
        self.assertIn("temp", result.preview)


class TestRefactoringEngine(unittest.TestCase):
    """Test RefactoringEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = RefactoringEngine()

        # Create test file
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
class TestClass:
    def method(self):
        x = 10
        return x
""")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_engine_creation(self):
        """Test creating refactoring engine."""
        self.assertIsNotNone(self.engine.renamer)
        self.assertIsNotNone(self.engine.extractor)
        self.assertIsNotNone(self.engine.inliner)

    def test_apply_refactoring(self):
        """Test applying refactoring to filesystem."""
        # Get refactoring result
        result = self.engine.rename_symbol(
            self.temp_dir,
            "TestClass",
            "RenamedClass"
        )

        # Apply refactoring
        success = self.engine.apply_refactoring(result)
        self.assertTrue(success)

        # Verify file was modified
        with open(self.test_file, "r") as f:
            content = f.read()
            self.assertIn("RenamedClass", content)
            self.assertNotIn("TestClass", content)

    def test_apply_failed_refactoring(self):
        """Test applying failed refactoring."""
        # Create a failed result
        result = self.engine.inline_variable(
            self.test_file,
            "nonexistent",
            999
        )

        success = self.engine.apply_refactoring(result)
        self.assertFalse(success)


class TestRefactoringResult(unittest.TestCase):
    """Test RefactoringResult."""

    def test_result_creation(self):
        """Test creating a refactoring result."""
        from pr_agent.refactoring.engine import RefactoringResult

        result = RefactoringResult(
            success=True,
            refactoring_type=RefactoringType.RENAME_SYMBOL,
            edits=[],
            affected_files=[],
            warnings=[],
            severity=RefactoringSeverity.SAFE,
            preview="Test preview"
        )

        self.assertTrue(result.success)
        self.assertEqual(result.refactoring_type, RefactoringType.RENAME_SYMBOL)
        self.assertEqual(result.severity, RefactoringSeverity.SAFE)


class TestRefactoringEdit(unittest.TestCase):
    """Test RefactoringEdit."""

    def test_edit_creation(self):
        """Test creating a refactoring edit."""
        from pr_agent.refactoring.engine import RefactoringEdit

        edit = RefactoringEdit(
            file_path="/test.py",
            start_line=1,
            start_col=0,
            end_line=1,
            end_col=10,
            old_text="old_name",
            new_text="new_name"
        )

        self.assertEqual(edit.file_path, "/test.py")
        self.assertEqual(edit.old_text, "old_name")
        self.assertEqual(edit.new_text, "new_name")


class TestGlobalInstance(unittest.TestCase):
    """Test global instance function."""

    def test_get_refactoring_engine(self):
        """Test getting refactoring engine."""
        engine = get_refactoring_engine()
        self.assertIsInstance(engine, RefactoringEngine)

        # Should return same instance
        engine2 = get_refactoring_engine()
        self.assertIs(engine, engine2)


class TestRefactoringTypes(unittest.TestCase):
    """Test refactoring type enums."""

    def test_refactoring_type_enum(self):
        """Test RefactoringType enum."""
        self.assertEqual(RefactoringType.RENAME_SYMBOL.value, "rename_symbol")
        self.assertEqual(RefactoringType.EXTRACT_METHOD.value, "extract_method")
        self.assertEqual(RefactoringType.INLINE_VARIABLE.value, "inline_variable")

    def test_refactoring_severity_enum(self):
        """Test RefactoringSeverity enum."""
        self.assertEqual(RefactoringSeverity.SAFE.value, "safe")
        self.assertEqual(RefactoringSeverity.WARNING.value, "warning")
        self.assertEqual(RefactoringSeverity.UNSAFE.value, "unsafe")


if __name__ == "__main__":
    unittest.main()
