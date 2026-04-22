"""
Code refactoring engine for automated code transformations.

This module provides tools for safe, automated code refactoring operations
including renaming, extraction, inlining, and structural transformations.
"""

import ast
import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RefactoringType(str, Enum):
    """Types of refactoring operations."""
    RENAME_SYMBOL = "rename_symbol"
    EXTRACT_METHOD = "extract_method"
    INLINE_VARIABLE = "inline_variable"
    EXTRACT_VARIABLE = "extract_variable"
    MOVE_METHOD = "move_method"
    CHANGE_SIGNATURE = "change_signature"


class RefactoringSeverity(str, Enum):
    """Severity levels for refactoring validation."""
    SAFE = "safe"
    WARNING = "warning"
    UNSAFE = "unsafe"


@dataclass
class RefactoringEdit:
    """Represents a single edit in a refactoring operation."""
    file_path: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int
    old_text: str
    new_text: str


@dataclass
class RefactoringResult:
    """Result of a refactoring operation."""
    success: bool
    refactoring_type: RefactoringType
    edits: List[RefactoringEdit]
    affected_files: List[str]
    warnings: List[str]
    severity: RefactoringSeverity
    preview: str


class SymbolRenamer:
    """Handles symbol renaming refactoring."""

    def __init__(self):
        self.symbol_table: Dict[str, List[Tuple[str, int, int]]] = {}

    def rename_symbol(
        self,
        workspace: str,
        old_name: str,
        new_name: str,
        scope: Optional[str] = None
    ) -> RefactoringResult:
        """
        Rename a symbol across the workspace.

        Args:
            workspace: Root directory to search
            old_name: Current symbol name
            new_name: New symbol name
            scope: Optional scope restriction (file path)

        Returns:
            RefactoringResult with all necessary edits
        """
        edits = []
        affected_files = set()
        warnings = []

        # Find all occurrences
        occurrences = self._find_symbol_occurrences(workspace, old_name, scope)

        # Validate rename
        severity = self._validate_rename(old_name, new_name, occurrences)
        if severity == RefactoringSeverity.UNSAFE:
            warnings.append(f"Renaming '{old_name}' to '{new_name}' may cause conflicts")

        # Create edits
        for file_path, line, col in occurrences:
            edit = RefactoringEdit(
                file_path=file_path,
                start_line=line,
                start_col=col,
                end_line=line,
                end_col=col + len(old_name),
                old_text=old_name,
                new_text=new_name
            )
            edits.append(edit)
            affected_files.add(file_path)

        preview = self._generate_preview(edits)

        return RefactoringResult(
            success=True,
            refactoring_type=RefactoringType.RENAME_SYMBOL,
            edits=edits,
            affected_files=list(affected_files),
            warnings=warnings,
            severity=severity,
            preview=preview
        )

    def _find_symbol_occurrences(
        self,
        workspace: str,
        symbol: str,
        scope: Optional[str] = None
    ) -> List[Tuple[str, int, int]]:
        """Find all occurrences of a symbol."""
        occurrences = []

        search_paths = [scope] if scope else self._get_python_files(workspace)

        for file_path in search_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                tree = ast.parse(content, filename=file_path)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Name) and node.id == symbol:
                        occurrences.append((file_path, node.lineno, node.col_offset))
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if node.name == symbol:
                            occurrences.append((file_path, node.lineno, node.col_offset))
            except Exception as e:
                logger.warning(f"Error parsing {file_path}: {e}")

        return occurrences

    def _validate_rename(
        self,
        old_name: str,
        new_name: str,
        occurrences: List[Tuple[str, int, int]]
    ) -> RefactoringSeverity:
        """Validate if rename is safe."""
        # Check if new name is a Python keyword
        import keyword
        if keyword.iskeyword(new_name):
            return RefactoringSeverity.UNSAFE

        # Check if new name follows naming conventions
        if not new_name.isidentifier():
            return RefactoringSeverity.UNSAFE

        # Check for potential conflicts
        if len(occurrences) > 100:
            return RefactoringSeverity.WARNING

        return RefactoringSeverity.SAFE

    def _get_python_files(self, workspace: str) -> List[str]:
        """Get all Python files in workspace."""
        python_files = []
        for root, _, files in os.walk(workspace):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        return python_files

    def _generate_preview(self, edits: List[RefactoringEdit]) -> str:
        """Generate a preview of the refactoring."""
        preview_lines = []
        preview_lines.append(f"Total edits: {len(edits)}")

        # Group by file
        files = {}
        for edit in edits:
            if edit.file_path not in files:
                files[edit.file_path] = []
            files[edit.file_path].append(edit)

        for file_path, file_edits in list(files.items())[:5]:  # Show first 5 files
            preview_lines.append(f"\n{file_path}:")
            for edit in file_edits[:3]:  # Show first 3 edits per file
                preview_lines.append(f"  Line {edit.start_line}: {edit.old_text} → {edit.new_text}")

        if len(files) > 5:
            preview_lines.append(f"\n... and {len(files) - 5} more files")

        return "\n".join(preview_lines)


class MethodExtractor:
    """Handles extract method refactoring."""

    def extract_method(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        method_name: str
    ) -> RefactoringResult:
        """
        Extract a block of code into a new method.

        Args:
            file_path: File containing the code
            start_line: Start line of code block
            end_line: End line of code block
            method_name: Name for the new method

        Returns:
            RefactoringResult with extraction edits
        """
        edits = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Extract the code block
            code_block = ''.join(lines[start_line-1:end_line])

            # Analyze variables
            used_vars, defined_vars = self._analyze_variables(code_block)
            params = used_vars - defined_vars
            returns = defined_vars

            # Generate method signature
            param_str = ', '.join(sorted(params))
            method_def = f"def {method_name}({param_str}):\n"

            # Indent code block
            indented_block = self._indent_code(code_block, 4)

            # Add return statement if needed
            if returns:
                return_str = ', '.join(sorted(returns))
                indented_block += f"    return {return_str}\n"

            new_method = method_def + indented_block

            # Create edit for method definition
            insertion_line = self._find_insertion_point(file_path, start_line)
            edits.append(RefactoringEdit(
                file_path=file_path,
                start_line=insertion_line,
                start_col=0,
                end_line=insertion_line,
                end_col=0,
                old_text="",
                new_text=new_method + "\n"
            ))

            # Create edit for method call
            call_args = ', '.join(sorted(params))
            method_call = f"{method_name}({call_args})"
            if returns:
                return_vars = ', '.join(sorted(returns))
                method_call = f"{return_vars} = {method_call}"

            edits.append(RefactoringEdit(
                file_path=file_path,
                start_line=start_line,
                start_col=0,
                end_line=end_line,
                end_col=len(lines[end_line-1]),
                old_text=code_block,
                new_text=self._get_indentation(lines[start_line-1]) + method_call + "\n"
            ))

            preview = f"Extract {end_line - start_line + 1} lines into method '{method_name}'"

            return RefactoringResult(
                success=True,
                refactoring_type=RefactoringType.EXTRACT_METHOD,
                edits=edits,
                affected_files=[file_path],
                warnings=warnings,
                severity=RefactoringSeverity.SAFE,
                preview=preview
            )

        except Exception as e:
            logger.error(f"Error extracting method: {e}")
            return RefactoringResult(
                success=False,
                refactoring_type=RefactoringType.EXTRACT_METHOD,
                edits=[],
                affected_files=[],
                warnings=[str(e)],
                severity=RefactoringSeverity.UNSAFE,
                preview=""
            )

    def _analyze_variables(self, code: str) -> Tuple[Set[str], Set[str]]:
        """Analyze variables used and defined in code block."""
        used_vars = set()
        defined_vars = set()

        try:
            tree = ast.parse(code)

            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    if isinstance(node.ctx, ast.Store):
                        defined_vars.add(node.id)
                    elif isinstance(node.ctx, ast.Load):
                        used_vars.add(node.id)
        except:
            pass

        return used_vars, defined_vars

    def _indent_code(self, code: str, spaces: int) -> str:
        """Add indentation to code."""
        indent = ' ' * spaces
        return '\n'.join(indent + line if line.strip() else line
                        for line in code.split('\n'))

    def _get_indentation(self, line: str) -> str:
        """Get the indentation of a line."""
        return line[:len(line) - len(line.lstrip())]

    def _find_insertion_point(self, file_path: str, current_line: int) -> int:
        """Find appropriate line to insert new method."""
        # Simple heuristic: insert before the current function
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for i in range(current_line - 1, -1, -1):
            if lines[i].strip().startswith('def ') or lines[i].strip().startswith('class '):
                return i

        return 0


class VariableInliner:
    """Handles inline variable refactoring."""

    def inline_variable(
        self,
        file_path: str,
        variable_name: str,
        line: int
    ) -> RefactoringResult:
        """
        Inline a variable by replacing all uses with its value.

        Args:
            file_path: File containing the variable
            variable_name: Name of variable to inline
            line: Line where variable is defined

        Returns:
            RefactoringResult with inlining edits
        """
        edits = []
        warnings = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            tree = ast.parse(content, filename=file_path)

            # Find variable definition
            var_value = None
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    if (hasattr(node, 'lineno') and node.lineno == line and
                        len(node.targets) == 1 and
                        isinstance(node.targets[0], ast.Name) and
                        node.targets[0].id == variable_name):
                        var_value = ast.unparse(node.value)
                        break

            if not var_value:
                warnings.append(f"Could not find definition of '{variable_name}' at line {line}")
                return RefactoringResult(
                    success=False,
                    refactoring_type=RefactoringType.INLINE_VARIABLE,
                    edits=[],
                    affected_files=[],
                    warnings=warnings,
                    severity=RefactoringSeverity.UNSAFE,
                    preview=""
                )

            # Find all uses of the variable
            uses = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id == variable_name:
                    if isinstance(node.ctx, ast.Load) and hasattr(node, 'lineno'):
                        uses.append((node.lineno, node.col_offset))

            # Create edits for each use
            lines = content.split('\n')
            for use_line, use_col in uses:
                if use_line != line:  # Don't replace the definition
                    edits.append(RefactoringEdit(
                        file_path=file_path,
                        start_line=use_line,
                        start_col=use_col,
                        end_line=use_line,
                        end_col=use_col + len(variable_name),
                        old_text=variable_name,
                        new_text=f"({var_value})"
                    ))

            # Remove the variable definition
            edits.append(RefactoringEdit(
                file_path=file_path,
                start_line=line,
                start_col=0,
                end_line=line,
                end_col=len(lines[line-1]) + 1,
                old_text=lines[line-1] + '\n',
                new_text=""
            ))

            preview = f"Inline variable '{variable_name}' ({len(uses)} uses)"

            return RefactoringResult(
                success=True,
                refactoring_type=RefactoringType.INLINE_VARIABLE,
                edits=edits,
                affected_files=[file_path],
                warnings=warnings,
                severity=RefactoringSeverity.SAFE,
                preview=preview
            )

        except Exception as e:
            logger.error(f"Error inlining variable: {e}")
            return RefactoringResult(
                success=False,
                refactoring_type=RefactoringType.INLINE_VARIABLE,
                edits=[],
                affected_files=[],
                warnings=[str(e)],
                severity=RefactoringSeverity.UNSAFE,
                preview=""
            )


class RefactoringEngine:
    """Main refactoring engine coordinating all refactoring operations."""

    def __init__(self):
        self.renamer = SymbolRenamer()
        self.extractor = MethodExtractor()
        self.inliner = VariableInliner()

    def rename_symbol(
        self,
        workspace: str,
        old_name: str,
        new_name: str,
        scope: Optional[str] = None
    ) -> RefactoringResult:
        """Rename a symbol across the workspace."""
        return self.renamer.rename_symbol(workspace, old_name, new_name, scope)

    def extract_method(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        method_name: str
    ) -> RefactoringResult:
        """Extract code block into a new method."""
        return self.extractor.extract_method(file_path, start_line, end_line, method_name)

    def inline_variable(
        self,
        file_path: str,
        variable_name: str,
        line: int
    ) -> RefactoringResult:
        """Inline a variable."""
        return self.inliner.inline_variable(file_path, variable_name, line)

    def apply_refactoring(self, result: RefactoringResult) -> bool:
        """
        Apply a refactoring result to the filesystem.

        Args:
            result: RefactoringResult to apply

        Returns:
            True if successful, False otherwise
        """
        if not result.success:
            logger.error("Cannot apply failed refactoring")
            return False

        try:
            # Group edits by file
            files_edits = {}
            for edit in result.edits:
                if edit.file_path not in files_edits:
                    files_edits[edit.file_path] = []
                files_edits[edit.file_path].append(edit)

            # Apply edits to each file
            for file_path, edits in files_edits.items():
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Sort edits by position (reverse order to maintain line numbers)
                edits.sort(key=lambda e: (e.start_line, e.start_col), reverse=True)

                # Apply each edit
                for edit in edits:
                    if edit.start_line == edit.end_line:
                        line = lines[edit.start_line - 1]
                        new_line = (line[:edit.start_col] +
                                   edit.new_text +
                                   line[edit.end_col:])
                        lines[edit.start_line - 1] = new_line
                    else:
                        # Multi-line edit
                        new_lines = [edit.new_text]
                        lines[edit.start_line - 1:edit.end_line] = new_lines

                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)

            logger.info(f"Applied refactoring to {len(files_edits)} files")
            return True

        except Exception as e:
            logger.error(f"Error applying refactoring: {e}")
            return False


# Global instance
_global_engine: Optional[RefactoringEngine] = None


def get_refactoring_engine() -> RefactoringEngine:
    """Get or create the global refactoring engine instance."""
    global _global_engine
    if _global_engine is None:
        _global_engine = RefactoringEngine()
    return _global_engine
