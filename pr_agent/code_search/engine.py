"""
Code search and navigation system.

Provides full-text search, symbol search, reference finding, and definition jumping.
"""

import ast
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import json


class SearchType(Enum):
    """Type of search."""
    FULL_TEXT = "full_text"
    SYMBOL = "symbol"
    REFERENCE = "reference"
    DEFINITION = "definition"
    REGEX = "regex"


class SymbolType(Enum):
    """Type of symbol."""
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"


@dataclass
class SearchResult:
    """Represents a search result."""
    file_path: str
    line_number: int
    column: int
    match_text: str
    context_before: str = ""
    context_after: str = ""
    symbol_type: Optional[SymbolType] = None
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "match_text": self.match_text,
            "context_before": self.context_before,
            "context_after": self.context_after,
            "symbol_type": self.symbol_type.value if self.symbol_type else None,
            "metadata": self.metadata,
        }


@dataclass
class Symbol:
    """Represents a code symbol."""
    name: str
    type: SymbolType
    file_path: str
    line_number: int
    column: int
    scope: str = ""
    signature: str = ""
    docstring: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "scope": self.scope,
            "signature": self.signature,
            "docstring": self.docstring,
        }


class SymbolIndexer(ast.NodeVisitor):
    """Indexes symbols in Python code."""

    def __init__(self, file_path: str, source_code: str):
        self.file_path = file_path
        self.source_code = source_code
        self.lines = source_code.split('\n')
        self.symbols: List[Symbol] = []
        self.current_scope: List[str] = []

    def index(self) -> List[Symbol]:
        """Index all symbols in the source code."""
        try:
            tree = ast.parse(self.source_code)
            self.visit(tree)
        except SyntaxError:
            pass
        return self.symbols

    def _get_scope(self) -> str:
        """Get current scope string."""
        return ".".join(self.current_scope) if self.current_scope else "<module>"

    def _get_docstring(self, node) -> str:
        """Extract docstring from node."""
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            docstring = ast.get_docstring(node)
            return docstring or ""
        return ""

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition."""
        symbol = Symbol(
            name=node.name,
            type=SymbolType.CLASS,
            file_path=self.file_path,
            line_number=node.lineno,
            column=node.col_offset,
            scope=self._get_scope(),
            signature=f"class {node.name}",
            docstring=self._get_docstring(node),
        )
        self.symbols.append(symbol)

        # Visit class body
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        # Determine if it's a method or function
        symbol_type = SymbolType.METHOD if self.current_scope else SymbolType.FUNCTION

        # Build signature
        args = [arg.arg for arg in node.args.args]
        signature = f"def {node.name}({', '.join(args)})"

        symbol = Symbol(
            name=node.name,
            type=symbol_type,
            file_path=self.file_path,
            line_number=node.lineno,
            column=node.col_offset,
            scope=self._get_scope(),
            signature=signature,
            docstring=self._get_docstring(node),
        )
        self.symbols.append(symbol)

        # Visit function body
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment (variables/constants)."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                # Determine if constant (uppercase name)
                is_constant = target.id.isupper()
                symbol_type = SymbolType.CONSTANT if is_constant else SymbolType.VARIABLE

                symbol = Symbol(
                    name=target.id,
                    type=symbol_type,
                    file_path=self.file_path,
                    line_number=node.lineno,
                    column=node.col_offset,
                    scope=self._get_scope(),
                )
                self.symbols.append(symbol)

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            symbol = Symbol(
                name=alias.name,
                type=SymbolType.IMPORT,
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                scope=self._get_scope(),
            )
            self.symbols.append(symbol)

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statement."""
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            symbol = Symbol(
                name=full_name,
                type=SymbolType.IMPORT,
                file_path=self.file_path,
                line_number=node.lineno,
                column=node.col_offset,
                scope=self._get_scope(),
            )
            self.symbols.append(symbol)

        self.generic_visit(node)


class CodeSearchEngine:
    """Main code search engine."""

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.symbol_index: Dict[str, List[Symbol]] = {}
        self.file_cache: Dict[str, List[str]] = {}

    def index_directory(
        self,
        extensions: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
    ) -> None:
        """Index all files in directory."""
        if extensions is None:
            extensions = [".py"]
        if exclude_patterns is None:
            exclude_patterns = ["__pycache__", ".git", "venv", "node_modules"]

        self.symbol_index.clear()

        for file_path in self._find_files(extensions, exclude_patterns):
            self._index_file(file_path)

    def search_full_text(
        self,
        query: str,
        case_sensitive: bool = False,
        whole_word: bool = False,
        max_results: int = 100,
    ) -> List[SearchResult]:
        """Search for text in all indexed files."""
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE

        # Build regex pattern
        if whole_word:
            pattern = rf"\b{re.escape(query)}\b"
        else:
            pattern = re.escape(query)

        regex = re.compile(pattern, flags)

        for file_path, lines in self.file_cache.items():
            for line_num, line in enumerate(lines, 1):
                matches = regex.finditer(line)
                for match in matches:
                    result = SearchResult(
                        file_path=file_path,
                        line_number=line_num,
                        column=match.start(),
                        match_text=match.group(),
                        context_before=lines[line_num - 2] if line_num > 1 else "",
                        context_after=lines[line_num] if line_num < len(lines) else "",
                    )
                    results.append(result)

                    if len(results) >= max_results:
                        return results

        return results

    def search_regex(
        self,
        pattern: str,
        case_sensitive: bool = False,
        max_results: int = 100,
    ) -> List[SearchResult]:
        """Search using regular expression."""
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            regex = re.compile(pattern, flags)
        except re.error:
            return results

        for file_path, lines in self.file_cache.items():
            for line_num, line in enumerate(lines, 1):
                matches = regex.finditer(line)
                for match in matches:
                    result = SearchResult(
                        file_path=file_path,
                        line_number=line_num,
                        column=match.start(),
                        match_text=match.group(),
                        context_before=lines[line_num - 2] if line_num > 1 else "",
                        context_after=lines[line_num] if line_num < len(lines) else "",
                    )
                    results.append(result)

                    if len(results) >= max_results:
                        return results

        return results

    def search_symbol(
        self,
        symbol_name: str,
        symbol_type: Optional[SymbolType] = None,
        fuzzy: bool = False,
    ) -> List[Symbol]:
        """Search for symbols by name."""
        results = []

        for symbols in self.symbol_index.values():
            for symbol in symbols:
                # Filter by type if specified
                if symbol_type and symbol.type != symbol_type:
                    continue

                # Match name
                if fuzzy:
                    if symbol_name.lower() in symbol.name.lower():
                        results.append(symbol)
                else:
                    if symbol.name == symbol_name:
                        results.append(symbol)

        return results

    def find_definition(self, symbol_name: str, file_path: str, line_number: int) -> Optional[Symbol]:
        """Find definition of a symbol."""
        # First, try to find in current file
        if file_path in self.symbol_index:
            for symbol in self.symbol_index[file_path]:
                if symbol.name == symbol_name:
                    return symbol

        # Then search in all files
        symbols = self.search_symbol(symbol_name, fuzzy=False)
        if symbols:
            return symbols[0]

        return None

    def find_references(self, symbol_name: str) -> List[SearchResult]:
        """Find all references to a symbol."""
        return self.search_full_text(symbol_name, whole_word=True)

    def get_symbols_in_file(self, file_path: str) -> List[Symbol]:
        """Get all symbols in a file."""
        return self.symbol_index.get(file_path, [])

    def get_symbols_by_type(self, symbol_type: SymbolType) -> List[Symbol]:
        """Get all symbols of a specific type."""
        results = []
        for symbols in self.symbol_index.values():
            for symbol in symbols:
                if symbol.type == symbol_type:
                    results.append(symbol)
        return results

    def _find_files(
        self,
        extensions: List[str],
        exclude_patterns: List[str],
    ) -> List[str]:
        """Find all files matching criteria."""
        files = []

        for ext in extensions:
            for file_path in self.root_path.rglob(f"*{ext}"):
                # Check exclusions
                if any(pattern in str(file_path) for pattern in exclude_patterns):
                    continue
                files.append(str(file_path))

        return files

    def _index_file(self, file_path: str) -> None:
        """Index a single file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

            # Cache file lines
            self.file_cache[file_path] = source_code.split('\n')

            # Index symbols for Python files
            if file_path.endswith(".py"):
                indexer = SymbolIndexer(file_path, source_code)
                symbols = indexer.index()
                self.symbol_index[file_path] = symbols

        except Exception:
            pass


# Global instance
_search_engine: Optional[CodeSearchEngine] = None


def get_search_engine(root_path: Optional[str] = None) -> CodeSearchEngine:
    """Get or create the global search engine."""
    global _search_engine
    if _search_engine is None or (root_path and str(_search_engine.root_path) != root_path):
        _search_engine = CodeSearchEngine(root_path or ".")
    return _search_engine
