"""
Tests for code search and navigation system.
"""

import os
import tempfile
import unittest
from pathlib import Path

from pr_agent.code_search import (
    CodeSearchEngine,
    CodeNavigator,
    SearchResult,
    Symbol,
    SymbolType,
    get_search_engine,
    get_code_navigator,
)


class TestCodeSearchEngine(unittest.TestCase):
    """Test CodeSearchEngine."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = CodeSearchEngine(self.temp_dir)

        # Create test files
        self.test_file1 = os.path.join(self.temp_dir, "module1.py")
        with open(self.test_file1, "w") as f:
            f.write("""
class TestClass:
    def test_method(self):
        pass

def test_function():
    return "hello world"

TEST_CONSTANT = 42
test_variable = "test"
""")

        self.test_file2 = os.path.join(self.temp_dir, "module2.py")
        with open(self.test_file2, "w") as f:
            f.write("""
from module1 import TestClass

class AnotherClass(TestClass):
    def another_method(self):
        return test_function()
""")

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_index_directory(self):
        """Test indexing directory."""
        self.engine.index_directory()

        self.assertEqual(len(self.engine.file_cache), 2)
        self.assertIn(self.test_file1, self.engine.symbol_index)
        self.assertIn(self.test_file2, self.engine.symbol_index)

    def test_search_full_text(self):
        """Test full-text search."""
        self.engine.index_directory()

        results = self.engine.search_full_text("hello")
        self.assertGreater(len(results), 0)
        self.assertIsInstance(results[0], SearchResult)

    def test_search_full_text_case_sensitive(self):
        """Test case-sensitive search."""
        self.engine.index_directory()

        results = self.engine.search_full_text("TEST", case_sensitive=True)
        self.assertGreater(len(results), 0)

    def test_search_full_text_whole_word(self):
        """Test whole word search."""
        self.engine.index_directory()

        results = self.engine.search_full_text("test", whole_word=True)
        self.assertGreater(len(results), 0)

    def test_search_regex(self):
        """Test regex search."""
        self.engine.index_directory()

        results = self.engine.search_regex(r"def \w+\(")
        self.assertGreater(len(results), 0)

    def test_search_symbol(self):
        """Test symbol search."""
        self.engine.index_directory()

        symbols = self.engine.search_symbol("TestClass")
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].name, "TestClass")
        self.assertEqual(symbols[0].type, SymbolType.CLASS)

    def test_search_symbol_fuzzy(self):
        """Test fuzzy symbol search."""
        self.engine.index_directory()

        symbols = self.engine.search_symbol("test", fuzzy=True)
        self.assertGreater(len(symbols), 0)

    def test_search_symbol_by_type(self):
        """Test symbol search by type."""
        self.engine.index_directory()

        symbols = self.engine.search_symbol(
            "test_function",
            symbol_type=SymbolType.FUNCTION
        )
        self.assertEqual(len(symbols), 1)
        self.assertEqual(symbols[0].type, SymbolType.FUNCTION)

    def test_find_definition(self):
        """Test finding definition."""
        self.engine.index_directory()

        symbol = self.engine.find_definition("TestClass", self.test_file1, 1)
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.name, "TestClass")

    def test_find_references(self):
        """Test finding references."""
        self.engine.index_directory()

        references = self.engine.find_references("TestClass")
        self.assertGreater(len(references), 0)

    def test_get_symbols_in_file(self):
        """Test getting symbols in file."""
        self.engine.index_directory()

        symbols = self.engine.get_symbols_in_file(self.test_file1)
        self.assertGreater(len(symbols), 0)

    def test_get_symbols_by_type(self):
        """Test getting symbols by type."""
        self.engine.index_directory()

        classes = self.engine.get_symbols_by_type(SymbolType.CLASS)
        self.assertGreater(len(classes), 0)


class TestSymbol(unittest.TestCase):
    """Test Symbol class."""

    def test_symbol_creation(self):
        """Test creating a symbol."""
        symbol = Symbol(
            name="test",
            type=SymbolType.FUNCTION,
            file_path="/test.py",
            line_number=1,
            column=0,
        )

        self.assertEqual(symbol.name, "test")
        self.assertEqual(symbol.type, SymbolType.FUNCTION)

    def test_symbol_to_dict(self):
        """Test converting symbol to dict."""
        symbol = Symbol(
            name="test",
            type=SymbolType.FUNCTION,
            file_path="/test.py",
            line_number=1,
            column=0,
            scope="module",
            signature="def test()",
            docstring="Test function",
        )

        data = symbol.to_dict()
        self.assertEqual(data["name"], "test")
        self.assertEqual(data["type"], "function")
        self.assertEqual(data["scope"], "module")


class TestSearchResult(unittest.TestCase):
    """Test SearchResult class."""

    def test_search_result_creation(self):
        """Test creating a search result."""
        result = SearchResult(
            file_path="/test.py",
            line_number=1,
            column=0,
            match_text="test",
        )

        self.assertEqual(result.file_path, "/test.py")
        self.assertEqual(result.match_text, "test")

    def test_search_result_to_dict(self):
        """Test converting search result to dict."""
        result = SearchResult(
            file_path="/test.py",
            line_number=1,
            column=0,
            match_text="test",
            context_before="before",
            context_after="after",
        )

        data = result.to_dict()
        self.assertEqual(data["file_path"], "/test.py")
        self.assertEqual(data["match_text"], "test")
        self.assertEqual(data["context_before"], "before")


class TestCodeNavigator(unittest.TestCase):
    """Test CodeNavigator."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.engine = CodeSearchEngine(self.temp_dir)
        self.navigator = CodeNavigator(self.engine)

        # Create test file
        self.test_file = os.path.join(self.temp_dir, "test.py")
        with open(self.test_file, "w") as f:
            f.write("""
class TestClass:
    def method1(self):
        pass

    def method2(self):
        pass

def function1():
    pass

CONSTANT = 42
""")

        self.engine.index_directory()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_go_to_definition(self):
        """Test go to definition."""
        symbol = self.navigator.go_to_definition("TestClass", self.test_file, 1)
        self.assertIsNotNone(symbol)
        self.assertEqual(symbol.name, "TestClass")

    def test_find_all_references(self):
        """Test finding all references."""
        references = self.navigator.find_all_references("TestClass")
        self.assertIsInstance(references, list)

    def test_get_file_outline(self):
        """Test getting file outline."""
        outline = self.navigator.get_file_outline(self.test_file)

        self.assertIn("classes", outline)
        self.assertIn("functions", outline)
        self.assertIn("methods", outline)
        self.assertGreater(len(outline["classes"]), 0)

    def test_get_symbol_hierarchy(self):
        """Test getting symbol hierarchy."""
        hierarchy = self.navigator.get_symbol_hierarchy(self.test_file)
        self.assertIsInstance(hierarchy, list)

    def test_get_workspace_symbols(self):
        """Test getting workspace symbols."""
        symbols = self.navigator.get_workspace_symbols()

        self.assertIn("classes", symbols)
        self.assertIn("functions", symbols)
        self.assertGreater(len(symbols["classes"]), 0)

    def test_find_similar_symbols(self):
        """Test finding similar symbols."""
        similar = self.navigator.find_similar_symbols("Test")
        self.assertIsInstance(similar, list)

    def test_search_workspace(self):
        """Test searching workspace."""
        results = self.navigator.search_workspace("TestClass", search_type="full_text")
        self.assertIsInstance(results, list)


class TestGlobalInstances(unittest.TestCase):
    """Test global instance functions."""

    def test_get_search_engine(self):
        """Test getting search engine."""
        engine = get_search_engine()
        self.assertIsInstance(engine, CodeSearchEngine)

    def test_get_code_navigator(self):
        """Test getting code navigator."""
        navigator = get_code_navigator()
        self.assertIsInstance(navigator, CodeNavigator)


if __name__ == "__main__":
    unittest.main()
