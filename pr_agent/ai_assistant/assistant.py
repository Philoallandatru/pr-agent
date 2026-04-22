"""
AI Assistant for Code Review

Provides intelligent assistance for code review tasks including:
- Natural language interaction
- Code explanation and analysis
- Review suggestion optimization
- Context-aware recommendations
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import json
import re


class AssistantCapability(Enum):
    """AI assistant capabilities."""
    CODE_EXPLANATION = "code_explanation"
    REVIEW_OPTIMIZATION = "review_optimization"
    QUESTION_ANSWERING = "question_answering"
    PATTERN_DETECTION = "pattern_detection"
    SUGGESTION_GENERATION = "suggestion_generation"
    CONTEXT_ANALYSIS = "context_analysis"


class MessageRole(Enum):
    """Message roles in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConfidenceLevel(Enum):
    """Confidence level for AI responses."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Message:
    """Conversation message."""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AssistantResponse:
    """AI assistant response."""
    content: str
    confidence: ConfidenceLevel
    suggestions: List[str] = field(default_factory=list)
    code_snippets: List[Dict[str, str]] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeExplanation:
    """Code explanation result."""
    code: str
    explanation: str
    key_concepts: List[str]
    complexity_analysis: Dict[str, Any]
    potential_issues: List[Dict[str, Any]]
    improvement_suggestions: List[str]


@dataclass
class ReviewOptimization:
    """Review optimization result."""
    original_comment: str
    optimized_comment: str
    improvements: List[str]
    tone_score: float  # 0-1, higher is more constructive
    clarity_score: float  # 0-1, higher is clearer


@dataclass
class ConversationContext:
    """Conversation context."""
    conversation_id: str
    messages: List[Message] = field(default_factory=list)
    code_context: Dict[str, Any] = field(default_factory=dict)
    review_context: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AIAssistant:
    """
    AI Assistant for code review tasks.

    Provides intelligent assistance through natural language interaction,
    code analysis, and review optimization.
    """

    def __init__(
        self,
        model_name: str = "gpt-4",
        capabilities: Optional[List[AssistantCapability]] = None,
        max_context_length: int = 4000
    ):
        """
        Initialize AI assistant.

        Args:
            model_name: Name of the AI model to use
            capabilities: List of enabled capabilities
            max_context_length: Maximum context length in tokens
        """
        self.model_name = model_name
        self.capabilities = capabilities or list(AssistantCapability)
        self.max_context_length = max_context_length
        self.conversations: Dict[str, ConversationContext] = {}
        self.custom_handlers: Dict[str, Callable] = {}

    def create_conversation(
        self,
        conversation_id: str,
        code_context: Optional[Dict[str, Any]] = None,
        review_context: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> ConversationContext:
        """
        Create a new conversation context.

        Args:
            conversation_id: Unique conversation identifier
            code_context: Code-related context
            review_context: Review-related context
            user_preferences: User preferences

        Returns:
            ConversationContext: Created conversation context
        """
        context = ConversationContext(
            conversation_id=conversation_id,
            code_context=code_context or {},
            review_context=review_context or {},
            user_preferences=user_preferences or {}
        )
        self.conversations[conversation_id] = context
        return context

    def chat(
        self,
        conversation_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AssistantResponse:
        """
        Chat with the AI assistant.

        Args:
            conversation_id: Conversation identifier
            message: User message
            context: Additional context

        Returns:
            AssistantResponse: Assistant's response
        """
        # Get or create conversation
        if conversation_id not in self.conversations:
            self.create_conversation(conversation_id)

        conv = self.conversations[conversation_id]

        # Add user message
        user_msg = Message(role=MessageRole.USER, content=message)
        conv.messages.append(user_msg)

        # Analyze intent
        intent = self._analyze_intent(message)

        # Generate response based on intent
        if intent == "code_explanation":
            response = self._handle_code_explanation(message, conv, context)
        elif intent == "review_optimization":
            response = self._handle_review_optimization(message, conv, context)
        elif intent == "question":
            response = self._handle_question(message, conv, context)
        else:
            response = self._handle_general(message, conv, context)

        # Add assistant message
        assistant_msg = Message(
            role=MessageRole.ASSISTANT,
            content=response.content,
            metadata={"confidence": response.confidence.value}
        )
        conv.messages.append(assistant_msg)
        conv.updated_at = datetime.now(timezone.utc)

        return response

    def explain_code(
        self,
        code: str,
        language: str = "python",
        context: Optional[Dict[str, Any]] = None
    ) -> CodeExplanation:
        """
        Explain code snippet.

        Args:
            code: Code to explain
            language: Programming language
            context: Additional context

        Returns:
            CodeExplanation: Code explanation
        """
        # Analyze code structure
        key_concepts = self._extract_key_concepts(code, language)
        complexity = self._analyze_complexity(code, language)
        issues = self._detect_issues(code, language)
        suggestions = self._generate_improvements(code, language)

        # Generate explanation
        explanation = self._generate_explanation(
            code, language, key_concepts, complexity, issues
        )

        return CodeExplanation(
            code=code,
            explanation=explanation,
            key_concepts=key_concepts,
            complexity_analysis=complexity,
            potential_issues=issues,
            improvement_suggestions=suggestions
        )

    def optimize_review_comment(
        self,
        comment: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ReviewOptimization:
        """
        Optimize a review comment for clarity and constructiveness.

        Args:
            comment: Original review comment
            context: Additional context

        Returns:
            ReviewOptimization: Optimized comment
        """
        # Analyze tone and clarity
        tone_score = self._analyze_tone(comment)
        clarity_score = self._analyze_clarity(comment)

        # Generate improvements
        improvements = []
        optimized = comment

        # Make more constructive
        if tone_score < 0.7:
            optimized = self._make_constructive(optimized)
            improvements.append("Made tone more constructive")

        # Improve clarity
        if clarity_score < 0.7:
            optimized = self._improve_clarity(optimized)
            improvements.append("Improved clarity")

        # Add specific suggestions
        if not self._has_actionable_suggestion(optimized):
            optimized = self._add_suggestion(optimized)
            improvements.append("Added actionable suggestion")

        return ReviewOptimization(
            original_comment=comment,
            optimized_comment=optimized,
            improvements=improvements,
            tone_score=min(tone_score + 0.2, 1.0),
            clarity_score=min(clarity_score + 0.2, 1.0)
        )

    def suggest_review_points(
        self,
        code: str,
        file_path: str,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest review points for code.

        Args:
            code: Code to review
            file_path: File path
            context: Additional context

        Returns:
            List of review point suggestions
        """
        suggestions = []

        # Check for common patterns
        patterns = self._detect_patterns(code)
        for pattern in patterns:
            suggestions.append({
                "type": "pattern",
                "severity": "info",
                "message": f"Consider reviewing: {pattern['description']}",
                "line": pattern.get("line"),
                "suggestion": pattern.get("suggestion")
            })

        # Check complexity
        complexity = self._analyze_complexity(code, self._detect_language(file_path))
        if complexity.get("cyclomatic", 0) > 10:
            suggestions.append({
                "type": "complexity",
                "severity": "warning",
                "message": "High complexity detected",
                "suggestion": "Consider breaking down into smaller functions"
            })

        # Check for potential issues
        issues = self._detect_issues(code, self._detect_language(file_path))
        for issue in issues:
            suggestions.append({
                "type": "issue",
                "severity": issue.get("severity", "warning"),
                "message": issue["message"],
                "line": issue.get("line"),
                "suggestion": issue.get("fix")
            })

        return suggestions

    def register_custom_handler(
        self,
        intent: str,
        handler: Callable[[str, ConversationContext, Optional[Dict[str, Any]]], AssistantResponse]
    ):
        """
        Register a custom intent handler.

        Args:
            intent: Intent name
            handler: Handler function
        """
        self.custom_handlers[intent] = handler

    def get_conversation_history(
        self,
        conversation_id: str,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Get conversation history.

        Args:
            conversation_id: Conversation identifier
            limit: Maximum number of messages

        Returns:
            List of messages
        """
        if conversation_id not in self.conversations:
            return []

        messages = self.conversations[conversation_id].messages
        if limit:
            return messages[-limit:]
        return messages

    def clear_conversation(self, conversation_id: str):
        """Clear conversation history."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]

    # Private helper methods

    def _analyze_intent(self, message: str) -> str:
        """Analyze user intent from message."""
        message_lower = message.lower()

        if any(word in message_lower for word in ["explain", "what does", "how does"]):
            return "code_explanation"
        elif any(word in message_lower for word in ["improve", "optimize", "better"]):
            return "review_optimization"
        elif message_lower.endswith("?"):
            return "question"
        else:
            return "general"

    def _handle_code_explanation(
        self,
        message: str,
        conv: ConversationContext,
        context: Optional[Dict[str, Any]]
    ) -> AssistantResponse:
        """Handle code explanation request."""
        # Extract code from message or context
        code = self._extract_code(message) or conv.code_context.get("current_code", "")

        if not code:
            return AssistantResponse(
                content="I'd be happy to explain code. Please provide the code snippet you'd like me to explain.",
                confidence=ConfidenceLevel.HIGH
            )

        explanation = self.explain_code(code)

        content = f"**Code Explanation:**\n\n{explanation.explanation}\n\n"
        content += f"**Key Concepts:** {', '.join(explanation.key_concepts)}\n\n"

        if explanation.potential_issues:
            content += f"**Potential Issues:**\n"
            for issue in explanation.potential_issues:
                content += f"- {issue}\n"

        return AssistantResponse(
            content=content,
            confidence=ConfidenceLevel.HIGH,
            suggestions=explanation.improvement_suggestions,
            code_snippets=[{"language": "python", "code": code}]
        )

    def _handle_review_optimization(
        self,
        message: str,
        conv: ConversationContext,
        context: Optional[Dict[str, Any]]
    ) -> AssistantResponse:
        """Handle review optimization request."""
        # Extract comment from message
        comment = self._extract_comment(message)

        if not comment:
            return AssistantResponse(
                content="Please provide the review comment you'd like me to optimize.",
                confidence=ConfidenceLevel.HIGH
            )

        optimization = self.optimize_review_comment(comment)

        content = f"**Optimized Comment:**\n\n{optimization.optimized_comment}\n\n"
        content += f"**Improvements Made:**\n"
        for improvement in optimization.improvements:
            content += f"- {improvement}\n"

        return AssistantResponse(
            content=content,
            confidence=ConfidenceLevel.HIGH,
            suggestions=[
                f"Tone score improved to {optimization.tone_score:.1%}",
                f"Clarity score improved to {optimization.clarity_score:.1%}"
            ]
        )

    def _handle_question(
        self,
        message: str,
        conv: ConversationContext,
        context: Optional[Dict[str, Any]]
    ) -> AssistantResponse:
        """Handle general question."""
        # Simple knowledge base responses
        responses = {
            "best practices": "Here are some code review best practices:\n1. Be constructive and specific\n2. Focus on the code, not the person\n3. Provide actionable suggestions\n4. Explain the 'why' behind your comments",
            "review checklist": "Code review checklist:\n- Functionality: Does it work as intended?\n- Code quality: Is it readable and maintainable?\n- Tests: Are there adequate tests?\n- Security: Are there any vulnerabilities?\n- Performance: Are there any bottlenecks?",
        }

        message_lower = message.lower()
        for key, response in responses.items():
            if key in message_lower:
                return AssistantResponse(
                    content=response,
                    confidence=ConfidenceLevel.HIGH
                )

        return AssistantResponse(
            content="I'm here to help with code review tasks. I can explain code, optimize review comments, and answer questions about best practices.",
            confidence=ConfidenceLevel.MEDIUM
        )

    def _handle_general(
        self,
        message: str,
        conv: ConversationContext,
        context: Optional[Dict[str, Any]]
    ) -> AssistantResponse:
        """Handle general message."""
        return AssistantResponse(
            content="I'm your AI code review assistant. I can help you:\n- Explain code snippets\n- Optimize review comments\n- Suggest review points\n- Answer questions about best practices\n\nHow can I assist you today?",
            confidence=ConfidenceLevel.HIGH
        )

    def _extract_code(self, message: str) -> Optional[str]:
        """Extract code from message."""
        # Look for code blocks
        code_pattern = r"```(?:\w+)?\n(.*?)\n```"
        match = re.search(code_pattern, message, re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _extract_comment(self, message: str) -> Optional[str]:
        """Extract comment from message."""
        # Look for quoted text
        quote_pattern = r'"([^"]+)"'
        match = re.search(quote_pattern, message)
        if match:
            return match.group(1)
        return None

    def _extract_key_concepts(self, code: str, language: str) -> List[str]:
        """Extract key concepts from code."""
        concepts = []

        if language == "python":
            if "class " in code:
                concepts.append("Object-Oriented Programming")
            if "def " in code:
                concepts.append("Functions")
            if "async " in code or "await " in code:
                concepts.append("Asynchronous Programming")
            if "with " in code:
                concepts.append("Context Managers")
            if "try:" in code or "except" in code:
                concepts.append("Exception Handling")

        return concepts

    def _analyze_complexity(self, code: str, language: str) -> Dict[str, Any]:
        """Analyze code complexity."""
        lines = code.split("\n")
        non_empty_lines = [l for l in lines if l.strip()]

        # Simple cyclomatic complexity estimation
        complexity = 1
        for line in non_empty_lines:
            if any(keyword in line for keyword in ["if ", "elif ", "for ", "while ", "and ", "or "]):
                complexity += 1

        return {
            "lines": len(non_empty_lines),
            "cyclomatic": complexity,
            "level": "low" if complexity < 5 else "medium" if complexity < 10 else "high"
        }

    def _detect_issues(self, code: str, language: str) -> List[Dict[str, Any]]:
        """Detect potential issues in code."""
        issues = []

        if language == "python":
            if "except:" in code:
                issues.append({
                    "message": "Bare except clause detected",
                    "severity": "warning",
                    "fix": "Consider catching specific exceptions"
                })
            if "eval(" in code or "exec(" in code:
                issues.append({
                    "message": "Use of eval/exec detected",
                    "severity": "error",
                    "fix": "Avoid eval/exec - potential security risk"
                })
            if "TODO" in code or "FIXME" in code:
                issues.append({
                    "message": "Unresolved TODO/FIXME comments",
                    "severity": "info",
                    "fix": "Complete or remove TODO/FIXME comments"
                })

        return issues

    def _generate_improvements(self, code: str, language: str) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        complexity = self._analyze_complexity(code, language)
        if complexity["cyclomatic"] > 10:
            suggestions.append("Consider breaking down complex functions")

        if len(code.split("\n")) > 50:
            suggestions.append("Consider splitting into smaller functions")

        return suggestions

    def _generate_explanation(
        self,
        code: str,
        language: str,
        concepts: List[str],
        complexity: Dict[str, Any],
        issues: List[Dict[str, Any]]
    ) -> str:
        """Generate code explanation."""
        explanation = f"This {language} code "

        if concepts:
            explanation += f"demonstrates {', '.join(concepts)}. "

        explanation += f"It has {complexity['lines']} lines with {complexity['level']} complexity. "

        if issues:
            explanation += f"Note: {len(issues)} potential issue(s) detected."

        return explanation

    def _analyze_tone(self, comment: str) -> float:
        """Analyze comment tone (0-1, higher is more constructive)."""
        negative_words = ["bad", "wrong", "terrible", "awful", "stupid"]
        positive_words = ["consider", "suggest", "could", "might", "perhaps"]

        comment_lower = comment.lower()
        negative_count = sum(1 for word in negative_words if word in comment_lower)
        positive_count = sum(1 for word in positive_words if word in comment_lower)

        if negative_count > positive_count:
            return 0.3
        elif positive_count > 0:
            return 0.9
        else:
            return 0.6

    def _analyze_clarity(self, comment: str) -> float:
        """Analyze comment clarity (0-1, higher is clearer)."""
        # Simple heuristic: longer, more detailed comments are clearer
        words = comment.split()
        if len(words) < 5:
            return 0.4
        elif len(words) < 15:
            return 0.7
        else:
            return 0.9

    def _make_constructive(self, comment: str) -> str:
        """Make comment more constructive."""
        # Replace negative words with constructive alternatives
        replacements = {
            "bad": "could be improved",
            "wrong": "might not be optimal",
            "terrible": "needs improvement",
            "don't": "consider not",
            "shouldn't": "might want to avoid"
        }

        result = comment
        for old, new in replacements.items():
            result = result.replace(old, new)

        return result

    def _improve_clarity(self, comment: str) -> str:
        """Improve comment clarity."""
        if not comment.endswith("."):
            comment += "."

        if not any(word in comment.lower() for word in ["because", "since", "as", "to"]):
            comment += " This will improve code quality."

        return comment

    def _has_actionable_suggestion(self, comment: str) -> bool:
        """Check if comment has actionable suggestion."""
        action_words = ["consider", "try", "use", "change", "add", "remove", "update"]
        return any(word in comment.lower() for word in action_words)

    def _add_suggestion(self, comment: str) -> str:
        """Add actionable suggestion to comment."""
        if not comment.endswith("."):
            comment += "."
        comment += " Consider refactoring this section."
        return comment

    def _detect_patterns(self, code: str) -> List[Dict[str, Any]]:
        """Detect code patterns."""
        patterns = []

        # Detect long functions
        lines = code.split("\n")
        if len(lines) > 50:
            patterns.append({
                "description": "Long function detected",
                "suggestion": "Consider breaking into smaller functions"
            })

        return patterns

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file path."""
        ext = file_path.split(".")[-1].lower()
        language_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "java": "java",
            "go": "go",
            "rs": "rust"
        }
        return language_map.get(ext, "unknown")


# Global assistant instance
_assistant_instance: Optional[AIAssistant] = None


def get_assistant() -> AIAssistant:
    """Get global AI assistant instance."""
    global _assistant_instance
    if _assistant_instance is None:
        _assistant_instance = AIAssistant()
    return _assistant_instance
