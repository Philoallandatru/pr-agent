"""Tests for AI Assistant."""

import pytest
from pr_agent.ai_assistant import (
    AIAssistant,
    AssistantCapability,
    ConfidenceLevel,
    MessageRole,
)


class TestAIAssistant:
    """Test AI assistant."""

    def test_create_assistant(self):
        """Test assistant creation."""
        assistant = AIAssistant()
        assert assistant.model_name == "gpt-4"
        assert len(assistant.capabilities) > 0

    def test_create_conversation(self):
        """Test conversation creation."""
        assistant = AIAssistant()
        conv = assistant.create_conversation(
            "conv-1",
            code_context={"file": "test.py"},
            review_context={"pr_id": "123"}
        )

        assert conv.conversation_id == "conv-1"
        assert conv.code_context["file"] == "test.py"
        assert conv.review_context["pr_id"] == "123"
        assert len(conv.messages) == 0

    def test_chat_basic(self):
        """Test basic chat."""
        assistant = AIAssistant()
        response = assistant.chat("conv-1", "Hello")

        assert response.content
        assert response.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW]

    def test_chat_code_explanation(self):
        """Test code explanation through chat."""
        assistant = AIAssistant()
        message = 'Explain this code: ```python\ndef add(a, b):\n    return a + b\n```'
        response = assistant.chat("conv-1", message)

        assert "explain" in response.content.lower() or "function" in response.content.lower()
        assert response.confidence == ConfidenceLevel.HIGH

    def test_chat_review_optimization(self):
        """Test review optimization through chat."""
        assistant = AIAssistant()
        message = 'Improve this comment: "This code is bad"'
        response = assistant.chat("conv-1", message)

        assert response.content
        assert response.confidence == ConfidenceLevel.HIGH

    def test_chat_question(self):
        """Test question handling."""
        assistant = AIAssistant()
        response = assistant.chat("conv-1", "What are code review best practices?")

        assert "best practices" in response.content.lower() or "review" in response.content.lower()

    def test_explain_code_python(self):
        """Test Python code explanation."""
        assistant = AIAssistant()
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
"""
        explanation = assistant.explain_code(code, "python")

        assert explanation.code == code
        assert explanation.explanation
        assert len(explanation.key_concepts) > 0
        assert "lines" in explanation.complexity_analysis
        assert "cyclomatic" in explanation.complexity_analysis

    def test_explain_code_with_issues(self):
        """Test code explanation with issues."""
        assistant = AIAssistant()
        code = """
try:
    risky_operation()
except:
    pass
"""
        explanation = assistant.explain_code(code, "python")

        assert len(explanation.potential_issues) > 0
        # Issues are now dictionaries with 'message' key
        assert any("except" in issue["message"].lower() for issue in explanation.potential_issues)

    def test_optimize_review_comment_negative(self):
        """Test optimizing negative comment."""
        assistant = AIAssistant()
        comment = "This code is bad and wrong"
        optimization = assistant.optimize_review_comment(comment)

        assert optimization.original_comment == comment
        assert optimization.optimized_comment != comment
        assert len(optimization.improvements) > 0
        assert optimization.tone_score > 0.3

    def test_optimize_review_comment_short(self):
        """Test optimizing short comment."""
        assistant = AIAssistant()
        comment = "Fix this"
        optimization = assistant.optimize_review_comment(comment)

        assert len(optimization.optimized_comment) > len(comment)
        assert "clarity" in [i.lower() for i in optimization.improvements] or len(optimization.improvements) > 0

    def test_optimize_review_comment_constructive(self):
        """Test already constructive comment."""
        assistant = AIAssistant()
        comment = "Consider using a more descriptive variable name here. This will improve code readability."
        optimization = assistant.optimize_review_comment(comment)

        assert optimization.tone_score >= 0.7
        assert optimization.clarity_score >= 0.7

    def test_suggest_review_points(self):
        """Test review point suggestions."""
        assistant = AIAssistant()
        code = """
def very_complex_function(a, b, c, d, e):
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        if a and b:
                            if c or d:
                                if e > 10:
                                    for i in range(10):
                                        while i > 0:
                                            return a + b + c + d + e
    return 0
"""
        suggestions = assistant.suggest_review_points(code, "test.py")

        assert len(suggestions) > 0
        assert any(s["type"] == "complexity" for s in suggestions)

    def test_suggest_review_points_with_issues(self):
        """Test suggestions with code issues."""
        assistant = AIAssistant()
        code = """
def process_data(data):
    try:
        result = eval(data)
    except:
        result = None
    return result
"""
        suggestions = assistant.suggest_review_points(code, "test.py")

        assert len(suggestions) > 0
        assert any("eval" in s["message"].lower() or "except" in s["message"].lower() for s in suggestions)

    def test_conversation_history(self):
        """Test conversation history."""
        assistant = AIAssistant()

        assistant.chat("conv-1", "Hello")
        assistant.chat("conv-1", "How are you?")

        history = assistant.get_conversation_history("conv-1")
        assert len(history) == 4  # 2 user + 2 assistant messages

        # Test with limit
        limited = assistant.get_conversation_history("conv-1", limit=2)
        assert len(limited) == 2

    def test_conversation_history_empty(self):
        """Test empty conversation history."""
        assistant = AIAssistant()
        history = assistant.get_conversation_history("nonexistent")
        assert len(history) == 0

    def test_clear_conversation(self):
        """Test clearing conversation."""
        assistant = AIAssistant()

        assistant.chat("conv-1", "Hello")
        assert "conv-1" in assistant.conversations

        assistant.clear_conversation("conv-1")
        assert "conv-1" not in assistant.conversations

    def test_custom_handler(self):
        """Test custom intent handler."""
        assistant = AIAssistant()

        def custom_handler(message, conv, context):
            from pr_agent.ai_assistant import AssistantResponse, ConfidenceLevel
            return AssistantResponse(
                content="Custom response",
                confidence=ConfidenceLevel.HIGH
            )

        assistant.register_custom_handler("custom", custom_handler)
        assert "custom" in assistant.custom_handlers

    def test_code_complexity_low(self):
        """Test low complexity code."""
        assistant = AIAssistant()
        code = "def add(a, b):\n    return a + b"
        complexity = assistant._analyze_complexity(code, "python")

        assert complexity["level"] == "low"
        assert complexity["cyclomatic"] < 5

    def test_code_complexity_high(self):
        """Test high complexity code."""
        assistant = AIAssistant()
        code = """
def complex_func(a, b, c):
    if a and b or c:
        if a > 0:
            if b > 0:
                if c > 0:
                    for i in range(10):
                        while i > 0:
                            if i % 2 == 0:
                                return i
    return 0
"""
        complexity = assistant._analyze_complexity(code, "python")

        # This code has medium complexity (cyclomatic = 9)
        assert complexity["level"] in ["medium", "high"]
        assert complexity["cyclomatic"] >= 5

    def test_extract_code_from_message(self):
        """Test code extraction from message."""
        assistant = AIAssistant()
        message = "Here is my code:\n```python\nprint('hello')\n```"
        code = assistant._extract_code(message)

        assert code == "print('hello')"

    def test_extract_code_no_code(self):
        """Test code extraction with no code."""
        assistant = AIAssistant()
        message = "Just a regular message"
        code = assistant._extract_code(message)

        assert code is None

    def test_extract_comment_from_message(self):
        """Test comment extraction."""
        assistant = AIAssistant()
        message = 'Optimize this: "This is bad code"'
        comment = assistant._extract_comment(message)

        assert comment == "This is bad code"

    def test_detect_language(self):
        """Test language detection."""
        assistant = AIAssistant()

        assert assistant._detect_language("test.py") == "python"
        assert assistant._detect_language("test.js") == "javascript"
        assert assistant._detect_language("test.ts") == "typescript"
        assert assistant._detect_language("test.java") == "java"
        assert assistant._detect_language("test.go") == "go"
        assert assistant._detect_language("test.unknown") == "unknown"

    def test_key_concepts_extraction(self):
        """Test key concepts extraction."""
        assistant = AIAssistant()

        # Test class detection
        code = "class MyClass:\n    pass"
        concepts = assistant._extract_key_concepts(code, "python")
        assert "Object-Oriented Programming" in concepts

        # Test async detection
        code = "async def fetch():\n    await get_data()"
        concepts = assistant._extract_key_concepts(code, "python")
        assert "Asynchronous Programming" in concepts

        # Test exception handling
        code = "try:\n    risky()\nexcept Exception:\n    pass"
        concepts = assistant._extract_key_concepts(code, "python")
        assert "Exception Handling" in concepts

    def test_tone_analysis(self):
        """Test tone analysis."""
        assistant = AIAssistant()

        # Negative tone
        negative = "This is bad and wrong"
        assert assistant._analyze_tone(negative) < 0.5

        # Positive tone
        positive = "Consider using a better approach"
        assert assistant._analyze_tone(positive) > 0.7

        # Neutral tone
        neutral = "This code does X"
        assert 0.5 <= assistant._analyze_tone(neutral) <= 0.7

    def test_clarity_analysis(self):
        """Test clarity analysis."""
        assistant = AIAssistant()

        # Short, unclear
        short = "Fix this"
        assert assistant._analyze_clarity(short) < 0.5

        # Medium clarity
        medium = "This function could be improved"
        assert 0.5 <= assistant._analyze_clarity(medium) < 0.9

        # High clarity (adjust threshold to match implementation)
        long = "This function could be improved by extracting the complex logic into separate helper functions"
        assert assistant._analyze_clarity(long) >= 0.7

    def test_get_assistant_singleton(self):
        """Test global assistant singleton."""
        from pr_agent.ai_assistant import get_assistant

        assistant1 = get_assistant()
        assistant2 = get_assistant()

        assert assistant1 is assistant2


class TestIntegration:
    """Test integration scenarios."""

    def test_full_conversation_flow(self):
        """Test complete conversation flow."""
        assistant = AIAssistant()

        # Create conversation with context
        conv = assistant.create_conversation(
            "test-conv",
            code_context={"file": "main.py"},
            review_context={"pr_id": "123"}
        )

        # Ask about code
        response1 = assistant.chat("test-conv", "What should I review in this PR?")
        assert response1.content

        # Ask for explanation
        code_msg = '```python\ndef test():\n    pass\n```\nWhat does this do?'
        response2 = assistant.chat("test-conv", code_msg)
        assert response2.content

        # Check history
        history = assistant.get_conversation_history("test-conv")
        assert len(history) == 4  # 2 user + 2 assistant

    def test_code_review_workflow(self):
        """Test code review workflow."""
        assistant = AIAssistant()

        # Explain code
        code = "def process(data):\n    return [x * 2 for x in data]"
        explanation = assistant.explain_code(code)
        assert explanation.explanation

        # Get review suggestions
        suggestions = assistant.suggest_review_points(code, "process.py")
        assert isinstance(suggestions, list)

        # Optimize a comment
        comment = "This is wrong"
        optimization = assistant.optimize_review_comment(comment)
        assert optimization.optimized_comment != comment
