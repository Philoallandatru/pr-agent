"""
智能代码审查建议系统
"""

from pr_agent.suggestions.engine import (
    SuggestionEngine,
    CodeSuggestion,
    SuggestionType,
    SuggestionPriority,
    RefactoringAnalyzer,
    PerformanceAnalyzer,
    ReadabilityAnalyzer
)

__all__ = [
    'SuggestionEngine',
    'CodeSuggestion',
    'SuggestionType',
    'SuggestionPriority',
    'RefactoringAnalyzer',
    'PerformanceAnalyzer',
    'ReadabilityAnalyzer'
]


# 全局单例
_suggestion_engine = None


def get_suggestion_engine() -> SuggestionEngine:
    """获取建议引擎单例"""
    global _suggestion_engine
    if _suggestion_engine is None:
        _suggestion_engine = SuggestionEngine()
    return _suggestion_engine
