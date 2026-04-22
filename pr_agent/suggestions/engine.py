"""
智能代码审查建议引擎

基于 AI 的代码改进建议系统，提供上下文感知的重构、性能优化和可读性改进建议。
"""

import ast
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class SuggestionType(Enum):
    """建议类型"""
    REFACTORING = "refactoring"  # 重构建议
    PERFORMANCE = "performance"  # 性能优化
    READABILITY = "readability"  # 可读性改进
    BEST_PRACTICE = "best_practice"  # 最佳实践
    SECURITY = "security"  # 安全改进


class SuggestionPriority(Enum):
    """建议优先级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CodeSuggestion:
    """代码建议"""
    type: SuggestionType
    priority: SuggestionPriority
    title: str
    description: str
    file_path: str
    line_number: int
    original_code: str
    suggested_code: str
    reasoning: str
    tags: List[str] = field(default_factory=list)


class RefactoringAnalyzer:
    """重构分析器"""

    def analyze(self, file_path: str) -> List[CodeSuggestion]:
        """分析代码并生成重构建议"""
        suggestions = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return suggestions

        # 检测重复代码
        suggestions.extend(self._detect_duplicate_code(file_path, tree, content))

        # 检测长函数
        suggestions.extend(self._detect_long_functions(file_path, tree, content))

        # 检测深层嵌套
        suggestions.extend(self._detect_deep_nesting(file_path, tree, content))

        return suggestions

    def _detect_duplicate_code(self, file_path: str, tree: ast.AST, content: str) -> List[CodeSuggestion]:
        """检测重复代码"""
        suggestions = []
        # 简化实现：检测相似的函数体
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        for i, func1 in enumerate(functions):
            for func2 in functions[i+1:]:
                similarity = self._calculate_similarity(func1, func2)
                if similarity > 0.8:  # 80% 相似度
                    suggestions.append(CodeSuggestion(
                        type=SuggestionType.REFACTORING,
                        priority=SuggestionPriority.MEDIUM,
                        title="检测到重复代码",
                        description=f"函数 {func1.name} 和 {func2.name} 有高度相似的代码",
                        file_path=file_path,
                        line_number=func1.lineno,
                        original_code=ast.unparse(func1),
                        suggested_code="考虑提取公共逻辑到单独的函数",
                        reasoning="重复代码增加维护成本，应该提取为可复用的函数",
                        tags=["duplicate", "refactoring"]
                    ))

        return suggestions

    def _calculate_similarity(self, node1: ast.AST, node2: ast.AST) -> float:
        """计算两个 AST 节点的相似度"""
        code1 = ast.unparse(node1)
        code2 = ast.unparse(node2)

        # 简单的相似度计算
        common = len(set(code1.split()) & set(code2.split()))
        total = len(set(code1.split()) | set(code2.split()))

        return common / total if total > 0 else 0.0

    def _detect_long_functions(self, file_path: str, tree: ast.AST, content: str) -> List[CodeSuggestion]:
        """检测过长的函数"""
        suggestions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                lines = content.split('\n')[node.lineno-1:node.end_lineno]
                line_count = len([l for l in lines if l.strip() and not l.strip().startswith('#')])

                if line_count > 50:
                    suggestions.append(CodeSuggestion(
                        type=SuggestionType.REFACTORING,
                        priority=SuggestionPriority.HIGH,
                        title="函数过长",
                        description=f"函数 {node.name} 有 {line_count} 行代码",
                        file_path=file_path,
                        line_number=node.lineno,
                        original_code=f"def {node.name}(...): # {line_count} lines",
                        suggested_code="将函数拆分为多个小函数，每个函数专注于单一职责",
                        reasoning="长函数难以理解和维护，建议拆分为多个小函数",
                        tags=["long-function", "refactoring"]
                    ))

        return suggestions

    def _detect_deep_nesting(self, file_path: str, tree: ast.AST, content: str) -> List[CodeSuggestion]:
        """检测深层嵌套"""
        suggestions = []

        def get_nesting_level(node: ast.AST, level: int = 0) -> int:
            max_level = level
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.If, ast.For, ast.While, ast.With)):
                    child_level = get_nesting_level(child, level + 1)
                    max_level = max(max_level, child_level)
            return max_level

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                nesting = get_nesting_level(node)
                if nesting > 4:
                    suggestions.append(CodeSuggestion(
                        type=SuggestionType.REFACTORING,
                        priority=SuggestionPriority.MEDIUM,
                        title="嵌套层级过深",
                        description=f"函数 {node.name} 的嵌套层级为 {nesting}",
                        file_path=file_path,
                        line_number=node.lineno,
                        original_code=f"def {node.name}(...): # nesting level {nesting}",
                        suggested_code="使用提前返回或提取子函数来减少嵌套",
                        reasoning="深层嵌套降低代码可读性，建议重构",
                        tags=["nesting", "refactoring"]
                    ))

        return suggestions


class PerformanceAnalyzer:
    """性能分析器"""

    def analyze(self, file_path: str) -> List[CodeSuggestion]:
        """分析代码并生成性能优化建议"""
        suggestions = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return suggestions

        # 检测低效的循环
        suggestions.extend(self._detect_inefficient_loops(file_path, tree, content))

        # 检测重复计算
        suggestions.extend(self._detect_repeated_computation(file_path, tree, content))

        return suggestions

    def _detect_inefficient_loops(self, file_path: str, tree: ast.AST, content: str) -> List[CodeSuggestion]:
        """检测低效的循环"""
        suggestions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                # 检测循环中的列表追加
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Attribute) and child.func.attr == 'append':
                            suggestions.append(CodeSuggestion(
                                type=SuggestionType.PERFORMANCE,
                                priority=SuggestionPriority.LOW,
                                title="考虑使用列表推导式",
                                description="循环中使用 append 可以改为列表推导式",
                                file_path=file_path,
                                line_number=node.lineno,
                                original_code=ast.unparse(node),
                                suggested_code="使用列表推导式: [item for item in iterable]",
                                reasoning="列表推导式通常比循环 append 更快",
                                tags=["performance", "list-comprehension"]
                            ))
                            break

        return suggestions

    def _detect_repeated_computation(self, file_path: str, tree: ast.AST, content: str) -> List[CodeSuggestion]:
        """检测重复计算"""
        suggestions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.For, ast.While)):
                # 检测循环中的不变计算
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        # 简化检测：如果调用没有参数依赖循环变量
                        suggestions.append(CodeSuggestion(
                            type=SuggestionType.PERFORMANCE,
                            priority=SuggestionPriority.MEDIUM,
                            title="循环不变量提升",
                            description="将循环中的不变计算移到循环外",
                            file_path=file_path,
                            line_number=node.lineno,
                            original_code="# 循环中的重复计算",
                            suggested_code="# 将不变计算移到循环外",
                            reasoning="避免在循环中重复执行相同的计算",
                            tags=["performance", "loop-invariant"]
                        ))
                        break

        return suggestions


class ReadabilityAnalyzer:
    """可读性分析器"""

    def analyze(self, file_path: str) -> List[CodeSuggestion]:
        """分析代码并生成可读性改进建议"""
        suggestions = []

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return suggestions

        # 检测魔法数字
        suggestions.extend(self._detect_magic_numbers(file_path, tree, content))

        # 检测不清晰的变量名
        suggestions.extend(self._detect_unclear_names(file_path, tree, content))

        return suggestions

    def _detect_magic_numbers(self, file_path: str, tree: ast.AST, content: str) -> List[CodeSuggestion]:
        """检测魔法数字"""
        suggestions = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)) and node.value not in [0, 1, -1]:
                    suggestions.append(CodeSuggestion(
                        type=SuggestionType.READABILITY,
                        priority=SuggestionPriority.LOW,
                        title="使用命名常量替代魔法数字",
                        description=f"发现魔法数字: {node.value}",
                        file_path=file_path,
                        line_number=node.lineno,
                        original_code=str(node.value),
                        suggested_code=f"MEANINGFUL_NAME = {node.value}",
                        reasoning="命名常量提高代码可读性和可维护性",
                        tags=["readability", "magic-number"]
                    ))

        return suggestions

    def _detect_unclear_names(self, file_path: str, tree: ast.AST, content: str) -> List[CodeSuggestion]:
        """检测不清晰的变量名"""
        suggestions = []
        unclear_patterns = ['x', 'y', 'tmp', 'temp', 'data', 'info', 'obj']

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id in unclear_patterns:
                    suggestions.append(CodeSuggestion(
                        type=SuggestionType.READABILITY,
                        priority=SuggestionPriority.LOW,
                        title="使用更具描述性的变量名",
                        description=f"变量名 '{node.id}' 不够清晰",
                        file_path=file_path,
                        line_number=node.lineno,
                        original_code=node.id,
                        suggested_code="使用描述变量用途的名称",
                        reasoning="清晰的变量名提高代码可读性",
                        tags=["readability", "naming"]
                    ))

        return suggestions


class SuggestionEngine:
    """建议引擎主控制器"""

    def __init__(self):
        self.refactoring_analyzer = RefactoringAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()
        self.readability_analyzer = ReadabilityAnalyzer()

    def analyze_file(self, file_path: str,
                    suggestion_types: Optional[List[SuggestionType]] = None) -> List[CodeSuggestion]:
        """分析单个文件"""
        if suggestion_types is None:
            suggestion_types = list(SuggestionType)

        suggestions = []

        if SuggestionType.REFACTORING in suggestion_types:
            suggestions.extend(self.refactoring_analyzer.analyze(file_path))

        if SuggestionType.PERFORMANCE in suggestion_types:
            suggestions.extend(self.performance_analyzer.analyze(file_path))

        if SuggestionType.READABILITY in suggestion_types:
            suggestions.extend(self.readability_analyzer.analyze(file_path))

        return suggestions

    def analyze_directory(self, directory: str,
                         suggestion_types: Optional[List[SuggestionType]] = None) -> Dict[str, List[CodeSuggestion]]:
        """分析整个目录"""
        results = {}

        for file_path in Path(directory).rglob("*.py"):
            suggestions = self.analyze_file(str(file_path), suggestion_types)
            if suggestions:
                results[str(file_path)] = suggestions

        return results

    def generate_report(self, suggestions: Dict[str, List[CodeSuggestion]]) -> Dict[str, Any]:
        """生成建议报告"""
        total_suggestions = sum(len(s) for s in suggestions.values())

        by_type = {}
        by_priority = {}

        for file_suggestions in suggestions.values():
            for suggestion in file_suggestions:
                by_type[suggestion.type.value] = by_type.get(suggestion.type.value, 0) + 1
                by_priority[suggestion.priority.value] = by_priority.get(suggestion.priority.value, 0) + 1

        return {
            "total_suggestions": total_suggestions,
            "files_analyzed": len(suggestions),
            "by_type": by_type,
            "by_priority": by_priority,
            "suggestions": {
                file_path: [
                    {
                        "type": s.type.value,
                        "priority": s.priority.value,
                        "title": s.title,
                        "description": s.description,
                        "line_number": s.line_number,
                        "reasoning": s.reasoning,
                        "tags": s.tags
                    }
                    for s in file_suggestions
                ]
                for file_path, file_suggestions in suggestions.items()
            }
        }
