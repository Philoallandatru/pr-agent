"""
Code navigation utilities.

Provides go-to-definition, find-references, and code outline features.
"""

from typing import List, Optional, Dict, Tuple
from pathlib import Path
from pr_agent.code_search.engine import (
    CodeSearchEngine,
    Symbol,
    SearchResult,
    SymbolType,
)


class CodeNavigator:
    """Provides code navigation features."""

    def __init__(self, search_engine: CodeSearchEngine):
        self.search_engine = search_engine

    def go_to_definition(
        self,
        symbol_name: str,
        file_path: str,
        line_number: int,
    ) -> Optional[Symbol]:
        """Navigate to symbol definition."""
        return self.search_engine.find_definition(symbol_name, file_path, line_number)

    def find_all_references(self, symbol_name: str) -> List[SearchResult]:
        """Find all references to a symbol."""
        return self.search_engine.find_references(symbol_name)

    def get_file_outline(self, file_path: str) -> Dict[str, List[Symbol]]:
        """Get outline of symbols in a file."""
        symbols = self.search_engine.get_symbols_in_file(file_path)

        outline = {
            "classes": [],
            "functions": [],
            "methods": [],
            "variables": [],
            "constants": [],
            "imports": [],
        }

        for symbol in symbols:
            if symbol.type == SymbolType.CLASS:
                outline["classes"].append(symbol)
            elif symbol.type == SymbolType.FUNCTION:
                outline["functions"].append(symbol)
            elif symbol.type == SymbolType.METHOD:
                outline["methods"].append(symbol)
            elif symbol.type == SymbolType.VARIABLE:
                outline["variables"].append(symbol)
            elif symbol.type == SymbolType.CONSTANT:
                outline["constants"].append(symbol)
            elif symbol.type == SymbolType.IMPORT:
                outline["imports"].append(symbol)

        return outline

    def get_symbol_hierarchy(self, file_path: str) -> List[Dict]:
        """Get hierarchical symbol structure."""
        symbols = self.search_engine.get_symbols_in_file(file_path)

        # Build hierarchy
        hierarchy = []
        scope_stack = {}

        for symbol in sorted(symbols, key=lambda s: s.line_number):
            node = {
                "symbol": symbol,
                "children": [],
            }

            if symbol.scope == "<module>":
                hierarchy.append(node)
                scope_stack[symbol.name] = node
            else:
                # Find parent
                parent_scope = symbol.scope.split(".")[-1]
                if parent_scope in scope_stack:
                    scope_stack[parent_scope]["children"].append(node)

                # Add to scope stack if it's a class or function
                if symbol.type in [SymbolType.CLASS, SymbolType.FUNCTION]:
                    scope_stack[symbol.name] = node

        return hierarchy

    def find_symbol_at_position(
        self,
        file_path: str,
        line_number: int,
        column: int,
    ) -> Optional[Symbol]:
        """Find symbol at a specific position."""
        symbols = self.search_engine.get_symbols_in_file(file_path)

        # Find symbol at or before the position
        for symbol in reversed(symbols):
            if symbol.line_number <= line_number:
                # Check if position is within symbol range
                # (simplified - would need more context for exact range)
                return symbol

        return None

    def get_call_hierarchy(self, symbol_name: str) -> Dict:
        """Get call hierarchy for a function/method."""
        # Find the symbol
        symbols = self.search_engine.search_symbol(symbol_name, fuzzy=False)
        if not symbols:
            return {"symbol": None, "callers": [], "callees": []}

        symbol = symbols[0]

        # Find references (callers)
        references = self.search_engine.find_references(symbol_name)

        # Filter out the definition itself
        callers = [
            ref for ref in references
            if ref.line_number != symbol.line_number or ref.file_path != symbol.file_path
        ]

        return {
            "symbol": symbol,
            "callers": callers,
            "callees": [],  # Would need more analysis to find callees
        }

    def get_type_hierarchy(self, class_name: str) -> Dict:
        """Get inheritance hierarchy for a class."""
        # Find the class
        symbols = self.search_engine.search_symbol(
            class_name,
            symbol_type=SymbolType.CLASS,
            fuzzy=False,
        )

        if not symbols:
            return {"class": None, "parents": [], "children": []}

        class_symbol = symbols[0]

        # This is simplified - would need dependency graph for full hierarchy
        return {
            "class": class_symbol,
            "parents": [],
            "children": [],
        }

    def search_workspace(
        self,
        query: str,
        search_type: str = "full_text",
        **kwargs,
    ) -> List:
        """Search entire workspace."""
        if search_type == "full_text":
            return self.search_engine.search_full_text(query, **kwargs)
        elif search_type == "regex":
            return self.search_engine.search_regex(query, **kwargs)
        elif search_type == "symbol":
            return self.search_engine.search_symbol(query, **kwargs)
        else:
            return []

    def get_workspace_symbols(self) -> Dict[str, List[Symbol]]:
        """Get all symbols in workspace grouped by type."""
        result = {
            "classes": self.search_engine.get_symbols_by_type(SymbolType.CLASS),
            "functions": self.search_engine.get_symbols_by_type(SymbolType.FUNCTION),
            "methods": self.search_engine.get_symbols_by_type(SymbolType.METHOD),
            "variables": self.search_engine.get_symbols_by_type(SymbolType.VARIABLE),
            "constants": self.search_engine.get_symbols_by_type(SymbolType.CONSTANT),
        }
        return result

    def find_similar_symbols(self, symbol_name: str, limit: int = 10) -> List[Symbol]:
        """Find symbols with similar names."""
        all_symbols = []
        for symbols in self.search_engine.symbol_index.values():
            all_symbols.extend(symbols)

        # Calculate similarity (simple substring matching)
        similar = []
        query_lower = symbol_name.lower()

        for symbol in all_symbols:
            name_lower = symbol.name.lower()
            if query_lower in name_lower or name_lower in query_lower:
                similar.append(symbol)

        # Sort by similarity (exact match first, then by length)
        similar.sort(key=lambda s: (
            s.name != symbol_name,
            abs(len(s.name) - len(symbol_name)),
            s.name,
        ))

        return similar[:limit]


# Global instance
_navigator: Optional[CodeNavigator] = None


def get_code_navigator(search_engine: Optional[CodeSearchEngine] = None) -> CodeNavigator:
    """Get or create the global code navigator."""
    global _navigator
    if _navigator is None or search_engine:
        from pr_agent.code_search.engine import get_search_engine
        engine = search_engine or get_search_engine()
        _navigator = CodeNavigator(engine)
    return _navigator
