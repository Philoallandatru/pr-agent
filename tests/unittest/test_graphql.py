"""
Unit tests for GraphQL API.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from pr_agent.graphql.schema import (
    Query,
    Mutation,
    Repository,
    Review,
    Prompt,
    RepositoryInput,
    PromptInput,
    ReviewFilter,
)


class TestGraphQLQueries:
    """Test GraphQL queries."""

    @patch("pr_agent.graphql.schema.Database")
    def test_repositories_query(self, mock_db_class):
        """Test repositories query."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_repositories.return_value = [
            {
                "id": 1,
                "url": "https://github.com/test/repo",
                "name": "test-repo",
                "enabled": True,
                "last_review": None,
                "total_reviews": 5,
            }
        ]

        query = Query()
        repos = query.repositories(limit=10, offset=0)

        assert len(repos) == 1
        assert repos[0].id == 1
        assert repos[0].name == "test-repo"
        assert repos[0].total_reviews == 5

    @patch("pr_agent.graphql.schema.Database")
    def test_repository_query(self, mock_db_class):
        """Test repository query by ID."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_repository.return_value = {
            "id": 1,
            "url": "https://github.com/test/repo",
            "name": "test-repo",
            "enabled": True,
            "last_review": None,
            "total_reviews": 5,
        }

        query = Query()
        repo = query.repository(id=1)

        assert repo is not None
        assert repo.id == 1
        assert repo.name == "test-repo"

    @patch("pr_agent.graphql.schema.Database")
    def test_repository_not_found(self, mock_db_class):
        """Test repository query when not found."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_repository.return_value = None

        query = Query()
        repo = query.repository(id=999)

        assert repo is None

    @patch("pr_agent.graphql.schema.Database")
    def test_reviews_query(self, mock_db_class):
        """Test reviews query."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_reviews.return_value = [
            {
                "id": 1,
                "repository_id": 1,
                "pr_number": 123,
                "status": "completed",
                "created_at": datetime.now(),
                "completed_at": datetime.now(),
                "result": "approved",
            }
        ]

        query = Query()
        reviews = query.reviews(limit=10, offset=0)

        assert len(reviews) == 1
        assert reviews[0].id == 1
        assert reviews[0].pr_number == 123
        assert reviews[0].status == "completed"

    @patch("pr_agent.graphql.schema.Database")
    def test_reviews_with_filter(self, mock_db_class):
        """Test reviews query with filter."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_reviews.return_value = []

        query = Query()
        filter_obj = ReviewFilter(repository_id=1, status="completed")
        reviews = query.reviews(filter=filter_obj, limit=10, offset=0)

        mock_db.get_reviews.assert_called_once()
        call_args = mock_db.get_reviews.call_args
        assert call_args[1]["filter"]["repository_id"] == 1
        assert call_args[1]["filter"]["status"] == "completed"

    @patch("pr_agent.graphql.schema.Database")
    def test_review_query(self, mock_db_class):
        """Test review query by ID."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_review.return_value = {
            "id": 1,
            "repository_id": 1,
            "pr_number": 123,
            "status": "completed",
            "created_at": datetime.now(),
            "completed_at": datetime.now(),
            "result": "approved",
        }

        query = Query()
        review = query.review(id=1)

        assert review is not None
        assert review.id == 1
        assert review.pr_number == 123

    @patch("pr_agent.graphql.schema.Database")
    def test_prompts_query(self, mock_db_class):
        """Test prompts query."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_prompts.return_value = [
            {
                "id": 1,
                "name": "test-prompt",
                "content": "Test content",
                "created_at": datetime.now(),
                "updated_at": None,
            }
        ]

        query = Query()
        prompts = query.prompts(limit=10, offset=0)

        assert len(prompts) == 1
        assert prompts[0].id == 1
        assert prompts[0].name == "test-prompt"

    @patch("pr_agent.graphql.schema.Database")
    def test_prompt_query(self, mock_db_class):
        """Test prompt query by ID."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.get_prompt.return_value = {
            "id": 1,
            "name": "test-prompt",
            "content": "Test content",
            "created_at": datetime.now(),
            "updated_at": None,
        }

        query = Query()
        prompt = query.prompt(id=1)

        assert prompt is not None
        assert prompt.id == 1
        assert prompt.name == "test-prompt"

    @patch("pr_agent.plugins.get_plugin_manager")
    def test_plugins_query(self, mock_get_manager):
        """Test plugins query."""
        mock_manager = Mock()
        mock_get_manager.return_value = mock_manager
        mock_manager.list_plugins.return_value = [
            {
                "name": "TestPlugin",
                "version": "1.0.0",
                "description": "Test plugin",
                "author": "Test",
                "enabled": True,
            }
        ]

        query = Query()
        plugins = query.plugins()

        assert len(plugins) == 1
        assert plugins[0].name == "TestPlugin"
        assert plugins[0].version == "1.0.0"


class TestGraphQLMutations:
    """Test GraphQL mutations."""

    @patch("pr_agent.graphql.schema.Database")
    def test_create_repository(self, mock_db_class):
        """Test create repository mutation."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.add_repository.return_value = 1
        mock_db.get_repository.return_value = {
            "id": 1,
            "url": "https://github.com/test/repo",
            "name": "test-repo",
            "enabled": True,
        }

        mutation = Mutation()
        input_data = RepositoryInput(
            url="https://github.com/test/repo", name="test-repo", enabled=True
        )
        repo = mutation.create_repository(input=input_data)

        assert repo.id == 1
        assert repo.name == "test-repo"
        mock_db.add_repository.assert_called_once()

    @patch("pr_agent.graphql.schema.Database")
    def test_update_repository(self, mock_db_class):
        """Test update repository mutation."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.update_repository.return_value = True
        mock_db.get_repository.return_value = {
            "id": 1,
            "url": "https://github.com/test/repo",
            "name": "updated-repo",
            "enabled": False,
            "last_review": None,
            "total_reviews": 0,
        }

        mutation = Mutation()
        input_data = RepositoryInput(
            url="https://github.com/test/repo", name="updated-repo", enabled=False
        )
        repo = mutation.update_repository(id=1, input=input_data)

        assert repo is not None
        assert repo.name == "updated-repo"
        assert repo.enabled is False

    @patch("pr_agent.graphql.schema.Database")
    def test_update_repository_not_found(self, mock_db_class):
        """Test update repository when not found."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.update_repository.return_value = False

        mutation = Mutation()
        input_data = RepositoryInput(
            url="https://github.com/test/repo", name="test-repo"
        )
        repo = mutation.update_repository(id=999, input=input_data)

        assert repo is None

    @patch("pr_agent.graphql.schema.Database")
    def test_delete_repository(self, mock_db_class):
        """Test delete repository mutation."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.delete_repository.return_value = True

        mutation = Mutation()
        result = mutation.delete_repository(id=1)

        assert result is True
        mock_db.delete_repository.assert_called_once_with(1)

    @patch("pr_agent.graphql.schema.Database")
    def test_create_prompt(self, mock_db_class):
        """Test create prompt mutation."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.add_prompt.return_value = 1
        mock_db.get_prompt.return_value = {
            "id": 1,
            "name": "test-prompt",
            "content": "Test content",
            "created_at": datetime.now(),
        }

        mutation = Mutation()
        input_data = PromptInput(name="test-prompt", content="Test content")
        prompt = mutation.create_prompt(input=input_data)

        assert prompt.id == 1
        assert prompt.name == "test-prompt"
        mock_db.add_prompt.assert_called_once()

    @patch("pr_agent.graphql.schema.Database")
    def test_update_prompt(self, mock_db_class):
        """Test update prompt mutation."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.update_prompt.return_value = True
        mock_db.get_prompt.return_value = {
            "id": 1,
            "name": "updated-prompt",
            "content": "Updated content",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        mutation = Mutation()
        input_data = PromptInput(name="updated-prompt", content="Updated content")
        prompt = mutation.update_prompt(id=1, input=input_data)

        assert prompt is not None
        assert prompt.name == "updated-prompt"

    @patch("pr_agent.graphql.schema.Database")
    def test_delete_prompt(self, mock_db_class):
        """Test delete prompt mutation."""
        mock_db = Mock()
        mock_db_class.return_value = mock_db
        mock_db.delete_prompt.return_value = True

        mutation = Mutation()
        result = mutation.delete_prompt(id=1)

        assert result is True
        mock_db.delete_prompt.assert_called_once_with(1)
