"""
Unit tests for DependencyResolver
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pr_agent.algo.dependency_resolver import (
    PythonDependencyResolver,
    JavaScriptDependencyResolver,
    TypeScriptDependencyResolver,
    JavaDependencyResolver,
    GoDependencyResolver,
    get_resolver
)


class TestPythonDependencyResolver(unittest.TestCase):
    """Test cases for PythonDependencyResolver"""

    def setUp(self):
        self.resolver = PythonDependencyResolver()

    def test_resolve_simple_import(self):
        """Test resolving simple import statement"""
        content = "import os\nimport sys"

        # Mock repo path
        with patch.object(self.resolver, '_resolve_python_import', return_value="module.py"):
            deps = self.resolver.resolve_dependencies(content, "test.py", Path("/repo"))

        self.assertEqual(len(deps), 2)

    def test_resolve_from_import(self):
        """Test resolving from...import statement"""
        content = "from package import module"

        with patch.object(self.resolver, '_resolve_python_import', return_value="package/__init__.py"):
            deps = self.resolver.resolve_dependencies(content, "test.py", Path("/repo"))

        self.assertEqual(len(deps), 1)
        self.assertEqual(deps[0][1], 10)  # High relevance score


class TestJavaScriptDependencyResolver(unittest.TestCase):
    """Test cases for JavaScriptDependencyResolver"""

    def setUp(self):
        self.resolver = JavaScriptDependencyResolver()

    def test_resolve_es6_import(self):
        """Test resolving ES6 import"""
        content = "import { func } from './utils';"

        with patch.object(self.resolver, '_resolve_js_import', return_value="utils.js"):
            deps = self.resolver.resolve_dependencies(content, "test.js", Path("/repo"))

        self.assertEqual(len(deps), 1)

    def test_resolve_require(self):
        """Test resolving require statement"""
        content = "const utils = require('./utils');"

        with patch.object(self.resolver, '_resolve_js_import', return_value="utils.js"):
            deps = self.resolver.resolve_dependencies(content, "test.js", Path("/repo"))

        self.assertEqual(len(deps), 1)

    def test_skip_external_packages(self):
        """Test that external packages are skipped"""
        content = "import React from 'react';"

        deps = self.resolver.resolve_dependencies(content, "test.js", Path("/repo"))

        self.assertEqual(len(deps), 0)


class TestTypeScriptDependencyResolver(unittest.TestCase):
    """Test cases for TypeScriptDependencyResolver"""

    def setUp(self):
        self.resolver = TypeScriptDependencyResolver()

    def test_resolve_type_import(self):
        """Test resolving type import"""
        content = "import type { User } from './types';"

        with patch.object(self.resolver, '_resolve_js_import', return_value="types.ts"):
            deps = self.resolver.resolve_dependencies(content, "test.ts", Path("/repo"))

        self.assertGreater(len(deps), 0)


class TestJavaDependencyResolver(unittest.TestCase):
    """Test cases for JavaDependencyResolver"""

    def setUp(self):
        self.resolver = JavaDependencyResolver()

    def test_resolve_import(self):
        """Test resolving Java import"""
        content = "import com.example.MyClass;"

        with patch.object(self.resolver, '_resolve_java_import', return_value="src/main/java/com/example/MyClass.java"):
            deps = self.resolver.resolve_dependencies(content, "Test.java", Path("/repo"))

        self.assertEqual(len(deps), 1)

    def test_skip_standard_library(self):
        """Test that standard library imports are skipped"""
        content = "import java.util.List;"

        deps = self.resolver.resolve_dependencies(content, "Test.java", Path("/repo"))

        self.assertEqual(len(deps), 0)


class TestGoDependencyResolver(unittest.TestCase):
    """Test cases for GoDependencyResolver"""

    def setUp(self):
        self.resolver = GoDependencyResolver()

    def test_resolve_single_import(self):
        """Test resolving single import"""
        content = 'import "github.com/user/repo/package"'

        with patch.object(self.resolver, '_resolve_go_import', return_value="package/file.go"):
            deps = self.resolver.resolve_dependencies(content, "main.go", Path("/repo"))

        self.assertEqual(len(deps), 1)

    def test_resolve_grouped_imports(self):
        """Test resolving grouped imports"""
        content = '''
import (
    "fmt"
    "github.com/user/repo/package1"
    "github.com/user/repo/package2"
)
'''

        with patch.object(self.resolver, '_resolve_go_import', side_effect=lambda p, r: f"{p}/file.go" if '.' in p else None):
            deps = self.resolver.resolve_dependencies(content, "main.go", Path("/repo"))

        self.assertGreater(len(deps), 0)


class TestGetResolver(unittest.TestCase):
    """Test cases for get_resolver function"""

    def test_get_python_resolver(self):
        """Test getting Python resolver"""
        resolver = get_resolver("test.py")
        self.assertIsInstance(resolver, PythonDependencyResolver)

    def test_get_javascript_resolver(self):
        """Test getting JavaScript resolver"""
        resolver = get_resolver("test.js")
        self.assertIsInstance(resolver, JavaScriptDependencyResolver)

    def test_get_typescript_resolver(self):
        """Test getting TypeScript resolver"""
        resolver = get_resolver("test.ts")
        self.assertIsInstance(resolver, TypeScriptDependencyResolver)

    def test_get_java_resolver(self):
        """Test getting Java resolver"""
        resolver = get_resolver("Test.java")
        self.assertIsInstance(resolver, JavaDependencyResolver)

    def test_get_go_resolver(self):
        """Test getting Go resolver"""
        resolver = get_resolver("main.go")
        self.assertIsInstance(resolver, GoDependencyResolver)

    def test_unsupported_extension(self):
        """Test unsupported file extension"""
        resolver = get_resolver("test.txt")
        self.assertIsNone(resolver)


if __name__ == "__main__":
    unittest.main()
