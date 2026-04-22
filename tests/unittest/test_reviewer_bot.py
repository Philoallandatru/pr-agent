"""Tests for code review bot system."""

import pytest
from pathlib import Path
import tempfile
import shutil
from pr_agent.bot import (
    ReviewerBot,
    BotConfig,
    BotComment,
    BotCapability,
    CommentType,
    ReviewMode
)


@pytest.fixture
def temp_storage():
    """Create temporary storage directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def bot_config():
    """Create test bot configuration."""
    return BotConfig(
        bot_id="test-bot",
        name="Test Bot",
        capabilities=[
            BotCapability.SYNTAX_CHECK,
            BotCapability.STYLE_CHECK,
            BotCapability.SECURITY_SCAN,
            BotCapability.PERFORMANCE_ANALYSIS,
            BotCapability.BEST_PRACTICES,
            BotCapability.DOCUMENTATION_CHECK
        ],
        confidence_threshold=0.7,
        max_comments_per_file=10,
        learning_enabled=True
    )


@pytest.fixture
def bot(bot_config, temp_storage):
    """Create test bot."""
    return ReviewerBot(bot_config, temp_storage)


class TestBotConfig:
    """Test bot configuration."""

    def test_create_config(self):
        """Test creating bot configuration."""
        config = BotConfig(
            bot_id="bot1",
            name="Bot 1",
            capabilities=[BotCapability.SYNTAX_CHECK]
        )
        assert config.bot_id == "bot1"
        assert config.name == "Bot 1"
        assert BotCapability.SYNTAX_CHECK in config.capabilities
        assert config.enabled is True
        assert config.auto_comment is True

    def test_config_with_custom_settings(self):
        """Test configuration with custom settings."""
        config = BotConfig(
            bot_id="bot2",
            name="Bot 2",
            capabilities=[BotCapability.SECURITY_SCAN],
            enabled=False,
            confidence_threshold=0.9,
            max_comments_per_file=5
        )
        assert config.enabled is False
        assert config.confidence_threshold == 0.9
        assert config.max_comments_per_file == 5


class TestBotComment:
    """Test bot comments."""

    def test_create_comment(self):
        """Test creating a comment."""
        comment = BotComment(
            comment_id="c1",
            file_path="test.py",
            line_number=10,
            comment_type=CommentType.SUGGESTION,
            message="Test message",
            confidence=0.9
        )
        assert comment.comment_id == "c1"
        assert comment.file_path == "test.py"
        assert comment.line_number == 10
        assert comment.comment_type == CommentType.SUGGESTION
        assert comment.confidence == 0.9

    def test_comment_to_dict(self):
        """Test converting comment to dictionary."""
        comment = BotComment(
            comment_id="c1",
            file_path="test.py",
            line_number=10,
            comment_type=CommentType.ERROR,
            message="Error message",
            suggestion="Fix suggestion"
        )
        data = comment.to_dict()
        assert data["comment_id"] == "c1"
        assert data["file_path"] == "test.py"
        assert data["comment_type"] == "error"
        assert data["suggestion"] == "Fix suggestion"


class TestReviewerBot:
    """Test reviewer bot."""

    def test_create_bot(self, bot):
        """Test creating a bot."""
        assert bot.config.bot_id == "test-bot"
        assert len(bot.config.capabilities) == 6
        assert bot.reviews == {}

    def test_review_pr_empty(self, bot):
        """Test reviewing empty PR."""
        result = bot.review_pr("pr1", {})
        assert result.pr_id == "pr1"
        assert result.bot_id == "test-bot"
        assert len(result.comments) == 0
        assert result.issues_found == 0

    def test_review_pr_with_trailing_whitespace(self, bot):
        """Test detecting trailing whitespace."""
        files = {
            "test.py": "def foo():  \n    pass\n"
        }
        result = bot.review_pr("pr1", files)
        assert len(result.comments) > 0
        assert any(c.rule_id == "syntax_trailing_whitespace" for c in result.comments)

    def test_review_pr_with_mixed_indentation(self, bot):
        """Test detecting mixed indentation."""
        files = {
            "test.py": "def foo():\n\t    pass\n"
        }
        result = bot.review_pr("pr1", files)
        assert any(c.rule_id == "syntax_mixed_indentation" for c in result.comments)

    def test_review_pr_with_long_line(self, bot):
        """Test detecting long lines."""
        long_line = "x = " + "a" * 120
        files = {
            "test.py": long_line + "\n"
        }
        result = bot.review_pr("pr1", files)
        assert any(c.rule_id == "style_line_length" for c in result.comments)

    def test_review_pr_with_hardcoded_password(self, bot):
        """Test detecting hardcoded passwords."""
        files = {
            "test.py": 'password = "secret123"\n'
        }
        result = bot.review_pr("pr1", files)
        assert any(c.rule_id == "security_hardcoded_secret" for c in result.comments)
        assert any(c.comment_type == CommentType.ERROR for c in result.comments)

    def test_review_pr_with_bare_except(self, bot):
        """Test detecting bare except."""
        files = {
            "test.py": "try:\n    pass\nexcept:\n    pass\n"
        }
        result = bot.review_pr("pr1", files)
        assert any(c.rule_id == "best_practice_bare_except" for c in result.comments)

    def test_review_pr_with_missing_docstring(self, bot):
        """Test detecting missing docstrings."""
        files = {
            "test.py": "def foo():\n    pass\n"
        }
        result = bot.review_pr("pr1", files)
        assert any(c.rule_id == "doc_missing_docstring" for c in result.comments)

    def test_confidence_threshold_filtering(self, bot):
        """Test confidence threshold filtering."""
        bot.config.confidence_threshold = 0.95
        files = {
            "test.py": "def foo():  \n    pass\n"  # Trailing whitespace (0.9 confidence)
        }
        result = bot.review_pr("pr1", files)
        # Should filter out comments below 0.95 confidence
        assert all(c.confidence >= 0.95 for c in result.comments)

    def test_max_comments_per_file(self, bot):
        """Test max comments per file limit."""
        bot.config.max_comments_per_file = 2
        # Create file with many issues
        lines = ["x = 1  \n"] * 10  # 10 trailing whitespace issues
        files = {
            "test.py": "".join(lines)
        }
        result = bot.review_pr("pr1", files)
        # Should limit to 2 comments
        assert len(result.comments) <= 2

    def test_review_modes(self, bot):
        """Test different review modes."""
        files = {
            "test.py": "def foo():  \n    pass\n"
        }

        # Full mode
        result_full = bot.review_pr("pr1", files, ReviewMode.FULL)
        assert result_full.mode == ReviewMode.FULL

        # Quick mode
        result_quick = bot.review_pr("pr2", files, ReviewMode.QUICK)
        assert result_quick.mode == ReviewMode.QUICK

    def test_custom_checker(self, bot):
        """Test adding custom checker."""
        def custom_checker(file_path: str, content: str):
            if "TODO" in content:
                return [BotComment(
                    comment_id="custom1",
                    file_path=file_path,
                    line_number=1,
                    comment_type=CommentType.INFO,
                    message="TODO found",
                    confidence=1.0,
                    rule_id="custom_todo"
                )]
            return []

        bot.add_custom_checker("todo_checker", custom_checker)
        files = {
            "test.py": "# TODO: fix this\n"
        }
        result = bot.review_pr("pr1", files)
        assert any(c.rule_id == "custom_todo" for c in result.comments)

    def test_remove_custom_checker(self, bot):
        """Test removing custom checker."""
        def custom_checker(file_path: str, content: str):
            return []

        bot.add_custom_checker("test_checker", custom_checker)
        assert "test_checker" in bot.custom_checkers

        bot.remove_custom_checker("test_checker")
        assert "test_checker" not in bot.custom_checkers

    def test_provide_feedback(self, bot):
        """Test providing feedback."""
        files = {
            "test.py": "def foo():  \n    pass\n"
        }
        result = bot.review_pr("pr1", files)

        if result.comments:
            comment = result.comments[0]
            bot.provide_feedback(comment.comment_id, True)

            if comment.rule_id:
                assert comment.rule_id in bot.learning_data
                assert bot.learning_data[comment.rule_id].feedback_count == 1
                assert bot.learning_data[comment.rule_id].positive_feedback == 1

    def test_learning_stats(self, bot):
        """Test getting learning statistics."""
        files = {
            "test.py": "def foo():  \n    pass\n"
        }
        result = bot.review_pr("pr1", files)

        # Provide some feedback
        for comment in result.comments[:3]:
            bot.provide_feedback(comment.comment_id, True)

        stats = bot.get_learning_stats()
        assert "total_rules" in stats
        assert "total_feedback" in stats
        assert "average_accuracy" in stats
        assert stats["total_feedback"] >= 0

    def test_export_config(self, bot):
        """Test exporting configuration."""
        config = bot.export_config()
        assert config["bot_id"] == "test-bot"
        assert config["name"] == "Test Bot"
        assert len(config["capabilities"]) == 6
        assert config["confidence_threshold"] == 0.7

    def test_get_review(self, bot):
        """Test getting a review."""
        files = {
            "test.py": "def foo():\n    pass\n"
        }
        result = bot.review_pr("pr1", files)

        retrieved = bot.get_review(result.review_id)
        assert retrieved is not None
        assert retrieved.review_id == result.review_id

    def test_list_reviews(self, bot):
        """Test listing reviews."""
        files = {
            "test.py": "def foo():\n    pass\n"
        }
        bot.review_pr("pr1", files)
        bot.review_pr("pr2", files)

        reviews = bot.list_reviews()
        assert len(reviews) == 2

    def test_list_reviews_filtered(self, bot):
        """Test listing reviews filtered by PR."""
        files = {
            "test.py": "def foo():\n    pass\n"
        }
        bot.review_pr("pr1", files)
        bot.review_pr("pr1", files)
        bot.review_pr("pr2", files)

        pr1_reviews = bot.list_reviews(pr_id="pr1")
        assert len(pr1_reviews) == 2
        assert all(r.pr_id == "pr1" for r in pr1_reviews)

    def test_review_summary_no_issues(self, bot):
        """Test review summary with no issues."""
        files = {
            "test.py": "def foo():\n    \"\"\"Docstring.\"\"\"\n    pass\n"
        }
        result = bot.review_pr("pr1", files)
        assert "No issues found" in result.summary or result.issues_found == 0

    def test_review_summary_with_issues(self, bot):
        """Test review summary with issues."""
        files = {
            "test.py": 'password = "secret"\n'
        }
        result = bot.review_pr("pr1", files)
        assert result.issues_found > 0
        assert "issues" in result.summary.lower() or "error" in result.summary.lower()

    def test_learning_data_persistence(self, bot, temp_storage):
        """Test learning data persistence."""
        files = {
            "test.py": "def foo():  \n    pass\n"
        }
        result = bot.review_pr("pr1", files)

        if result.comments:
            comment = result.comments[0]
            bot.provide_feedback(comment.comment_id, True)

        # Create new bot with same storage
        new_bot = ReviewerBot(bot.config, temp_storage)

        # Should load learning data
        if result.comments and result.comments[0].rule_id:
            assert result.comments[0].rule_id in new_bot.learning_data

    def test_multiple_file_review(self, bot):
        """Test reviewing multiple files."""
        files = {
            "file1.py": "def foo():  \n    pass\n",
            "file2.py": 'password = "secret"\n',
            "file3.py": "x = " + "a" * 130 + "\n"
        }
        result = bot.review_pr("pr1", files)

        # Should have comments from all files
        file_paths = {c.file_path for c in result.comments}
        assert len(file_paths) > 1

    def test_execution_time_tracking(self, bot):
        """Test execution time tracking."""
        files = {
            "test.py": "def foo():\n    pass\n"
        }
        result = bot.review_pr("pr1", files)
        assert result.execution_time >= 0  # Can be 0 for very fast execution

    def test_disabled_learning(self, bot_config, temp_storage):
        """Test bot with learning disabled."""
        bot_config.learning_enabled = False
        bot = ReviewerBot(bot_config, temp_storage)

        files = {
            "test.py": "def foo():  \n    pass\n"
        }
        result = bot.review_pr("pr1", files)

        if result.comments:
            comment = result.comments[0]
            bot.provide_feedback(comment.comment_id, True)
            # Should not update learning data
            assert len(bot.learning_data) == 0
