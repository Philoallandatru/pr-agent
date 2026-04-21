"""
Dependency Resolver - Language-specific import and dependency resolution

Analyzes source files to find related files through imports, function calls,
and other dependencies.
"""

import ast
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional


class DependencyResolver(ABC):
    """Base class for language-specific dependency resolvers"""

    @abstractmethod
    def resolve_dependencies(
        self,
        content: str,
        file_path: str,
        repo_path: Path
    ) -> List[Tuple[str, int]]:
        """
        Resolve dependencies for a file

        Args:
            content: File content
            file_path: Relative path to file
            repo_path: Path to repository root

        Returns:
            List of (file_path, relevance_score) tuples
        """
        pass


class PythonDependencyResolver(DependencyResolver):
    """Resolves Python imports and dependencies"""

    def resolve_dependencies(
        self,
        content: str,
        file_path: str,
        repo_path: Path
    ) -> List[Tuple[str, int]]:
        """Resolve Python imports"""
        dependencies = []

        try:
            tree = ast.parse(content)

            for node in ast.walk(tree):
                # Handle "import module"
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dep_path = self._resolve_python_import(alias.name, file_path, repo_path)
                        if dep_path:
                            dependencies.append((dep_path, 10))  # Direct import = high relevance

                # Handle "from module import ..."
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dep_path = self._resolve_python_import(node.module, file_path, repo_path)
                        if dep_path:
                            dependencies.append((dep_path, 10))

        except SyntaxError as e:
            pass  # Syntax errors are expected for some files
        except Exception as e:
            pass  # Silently handle errors during dependency resolution

        return dependencies

    def _resolve_python_import(
        self,
        module_name: str,
        current_file: str,
        repo_path: Path
    ) -> Optional[str]:
        """
        Resolve Python module name to file path

        Args:
            module_name: Module name (e.g., "package.module")
            current_file: Current file path
            repo_path: Repository root path

        Returns:
            Relative file path or None
        """
        # Convert module name to path
        module_path = module_name.replace('.', '/')

        # Try as .py file
        py_file = repo_path / f"{module_path}.py"
        if py_file.exists():
            return str(Path(module_path + ".py"))

        # Try as package __init__.py
        init_file = repo_path / module_path / "__init__.py"
        if init_file.exists():
            return str(Path(module_path) / "__init__.py")

        # Try relative import from current directory
        current_dir = Path(current_file).parent
        relative_py = repo_path / current_dir / f"{module_path}.py"
        if relative_py.exists():
            return str(current_dir / f"{module_path}.py")

        return None


class JavaScriptDependencyResolver(DependencyResolver):
    """Resolves JavaScript/TypeScript imports"""

    # Regex patterns for import statements
    IMPORT_PATTERNS = [
        r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]',  # import ... from 'module'
        r'import\s+[\'"]([^\'"]+)[\'"]',  # import 'module'
        r'require\([\'"]([^\'"]+)[\'"]\)',  # require('module')
        r'import\([\'"]([^\'"]+)[\'"]\)',  # dynamic import('module')
    ]

    def resolve_dependencies(
        self,
        content: str,
        file_path: str,
        repo_path: Path
    ) -> List[Tuple[str, int]]:
        """Resolve JavaScript/TypeScript imports"""
        dependencies = []

        try:
            for pattern in self.IMPORT_PATTERNS:
                matches = re.finditer(pattern, content)
                for match in matches:
                    module_name = match.group(1)

                    # Skip node_modules and external packages
                    if not module_name.startswith('.'):
                        continue

                    dep_path = self._resolve_js_import(module_name, file_path, repo_path)
                    if dep_path:
                        dependencies.append((dep_path, 10))

        except Exception as e:
            pass  # Silently handle errors

        return dependencies

    def _resolve_js_import(
        self,
        module_name: str,
        current_file: str,
        repo_path: Path
    ) -> Optional[str]:
        """
        Resolve JavaScript module to file path

        Args:
            module_name: Module name (e.g., "./utils", "../components/Button")
            current_file: Current file path
            repo_path: Repository root path

        Returns:
            Relative file path or None
        """
        current_dir = Path(current_file).parent

        # Resolve relative path
        if module_name.startswith('./') or module_name.startswith('../'):
            module_path = (current_dir / module_name).resolve()
            relative_path = module_path.relative_to(repo_path.resolve())

            # Try various extensions
            for ext in ['.js', '.jsx', '.ts', '.tsx', '.mjs']:
                file_with_ext = repo_path / f"{relative_path}{ext}"
                if file_with_ext.exists():
                    return str(Path(f"{relative_path}{ext}"))

            # Try as directory with index file
            for ext in ['.js', '.jsx', '.ts', '.tsx']:
                index_file = repo_path / relative_path / f"index{ext}"
                if index_file.exists():
                    return str(relative_path / f"index{ext}")

        return None


class TypeScriptDependencyResolver(JavaScriptDependencyResolver):
    """Resolves TypeScript imports (extends JavaScript resolver)"""

    def resolve_dependencies(
        self,
        content: str,
        file_path: str,
        repo_path: Path
    ) -> List[Tuple[str, int]]:
        """Resolve TypeScript imports including type imports"""
        dependencies = super().resolve_dependencies(content, file_path, repo_path)

        try:
            # Also match type imports: import type { ... } from '...'
            type_import_pattern = r'import\s+type\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]'
            matches = re.finditer(type_import_pattern, content)

            for match in matches:
                module_name = match.group(1)
                if module_name.startswith('.'):
                    dep_path = self._resolve_js_import(module_name, file_path, repo_path)
                    if dep_path:
                        dependencies.append((dep_path, 8))  # Type imports slightly lower relevance

        except Exception as e:
            pass  # Silently handle errors

        return dependencies


class JavaDependencyResolver(DependencyResolver):
    """Resolves Java imports"""

    def resolve_dependencies(
        self,
        content: str,
        file_path: str,
        repo_path: Path
    ) -> List[Tuple[str, int]]:
        """Resolve Java imports"""
        dependencies = []

        try:
            # Match import statements
            import_pattern = r'import\s+(static\s+)?([a-zA-Z0-9_.]+);'
            matches = re.finditer(import_pattern, content)

            for match in matches:
                class_name = match.group(2)

                # Skip java.* and javax.* (standard library)
                if class_name.startswith('java.') or class_name.startswith('javax.'):
                    continue

                dep_path = self._resolve_java_import(class_name, repo_path)
                if dep_path:
                    dependencies.append((dep_path, 10))

        except Exception as e:
            pass  # Silently handle errors

        return dependencies

    def _resolve_java_import(
        self,
        class_name: str,
        repo_path: Path
    ) -> Optional[str]:
        """
        Resolve Java class name to file path

        Args:
            class_name: Fully qualified class name (e.g., "com.example.MyClass")
            repo_path: Repository root path

        Returns:
            Relative file path or None
        """
        # Convert package.Class to path
        file_path = class_name.replace('.', '/') + '.java'

        # Try in src/main/java (Maven structure)
        maven_path = repo_path / 'src' / 'main' / 'java' / file_path
        if maven_path.exists():
            return str(Path('src/main/java') / file_path)

        # Try in src (simple structure)
        simple_path = repo_path / 'src' / file_path
        if simple_path.exists():
            return str(Path('src') / file_path)

        # Try direct path
        direct_path = repo_path / file_path
        if direct_path.exists():
            return file_path

        return None


class GoDependencyResolver(DependencyResolver):
    """Resolves Go imports"""

    def resolve_dependencies(
        self,
        content: str,
        file_path: str,
        repo_path: Path
    ) -> List[Tuple[str, int]]:
        """Resolve Go imports"""
        dependencies = []

        try:
            # Match import statements (single and grouped)
            # Single: import "package"
            single_pattern = r'import\s+"([^"]+)"'
            # Grouped: import ( ... "package" ... )
            group_pattern = r'import\s*\(\s*((?:[^)]*"[^"]+"\s*)+)\)'

            # Single imports
            for match in re.finditer(single_pattern, content):
                package = match.group(1)
                dep_path = self._resolve_go_import(package, repo_path)
                if dep_path:
                    dependencies.append((dep_path, 10))

            # Grouped imports
            for match in re.finditer(group_pattern, content, re.MULTILINE):
                imports_block = match.group(1)
                for package_match in re.finditer(r'"([^"]+)"', imports_block):
                    package = package_match.group(1)
                    dep_path = self._resolve_go_import(package, repo_path)
                    if dep_path:
                        dependencies.append((dep_path, 10))

        except Exception as e:
            pass  # Silently handle errors

        return dependencies

    def _resolve_go_import(
        self,
        package: str,
        repo_path: Path
    ) -> Optional[str]:
        """
        Resolve Go package to file path

        Args:
            package: Package import path
            repo_path: Repository root path

        Returns:
            Relative file path or None
        """
        # Skip standard library and external packages
        if '.' not in package or package.startswith('golang.org'):
            return None

        # Try to find package directory
        package_dir = repo_path / package
        if package_dir.exists() and package_dir.is_dir():
            # Return first .go file in package
            for go_file in package_dir.glob('*.go'):
                if not go_file.name.endswith('_test.go'):
                    return str(Path(package) / go_file.name)

        return None


# Resolver registry
RESOLVERS = {
    '.py': PythonDependencyResolver(),
    '.js': JavaScriptDependencyResolver(),
    '.jsx': JavaScriptDependencyResolver(),
    '.ts': TypeScriptDependencyResolver(),
    '.tsx': TypeScriptDependencyResolver(),
    '.mjs': JavaScriptDependencyResolver(),
    '.java': JavaDependencyResolver(),
    '.go': GoDependencyResolver(),
}


def get_resolver(file_path: str) -> Optional[DependencyResolver]:
    """
    Get appropriate dependency resolver for a file

    Args:
        file_path: File path

    Returns:
        DependencyResolver instance or None
    """
    ext = Path(file_path).suffix.lower()
    return RESOLVERS.get(ext)
