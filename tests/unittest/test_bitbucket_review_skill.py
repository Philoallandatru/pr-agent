"""
Bitbucket Review Skill单元测试
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from pr_agent.skills.bitbucket_review.config import BitbucketReviewConfig
from pr_agent.skills.bitbucket_review.webhook_handler import WebhookHandler


class TestBitbucketReviewConfig:
    """测试配置类"""

    def test_config_creation(self):
        """测试创建配置"""
        config = BitbucketReviewConfig(
            server_url="https://bitbucket.example.com",
            token="test_token",
        )
        assert config.server_url == "https://bitbucket.example.com"
        assert config.token == "test_token"

    def test_config_validation_with_token(self):
        """测试token验证"""
        config = BitbucketReviewConfig(
            server_url="https://bitbucket.example.com",
            token="test_token",
        )
        assert config.validate() is True

    def test_config_validation_with_username_password(self):
        """测试用户名密码验证"""
        config = BitbucketReviewConfig(
            server_url="https://bitbucket.example.com",
            username="user",
            password="pass",
        )
        assert config.validate() is True

    def test_config_validation_failure_no_auth(self):
        """测试验证失败（无认证）"""
        config = BitbucketReviewConfig(
            server_url="https://bitbucket.example.com",
        )
        assert config.validate() is False

    def test_config_validation_failure_no_url(self):
        """测试验证失败（无URL）"""
        config = BitbucketReviewConfig(
            server_url="",
            token="test_token",
        )
        assert config.validate() is False


class TestWebhookHandler:
    """测试Webhook处理器"""

    def test_parse_pr_opened_event(self):
        """测试解析PR opened事件"""
        handler = WebhookHandler()

        payload = {
            "eventKey": "pr:opened",
            "pullRequest": {
                "id": 123,
                "title": "Test PR",
                "fromRef": {
                    "repository": {
                        "slug": "test-repo",
                        "project": {"key": "TEST"},
                    }
                },
            },
        }

        with patch("pr_agent.skills.bitbucket_review.webhook_handler.get_settings") as mock_settings:
            mock_settings.return_value.get.return_value = "https://bitbucket.example.com"
            event_type, pr_url, pr_data = handler.parse_event(payload)

        assert event_type == "opened"
        assert "pull-requests/123" in pr_url
        assert pr_data["id"] == 123

    def test_parse_pr_updated_event(self):
        """测试解析PR updated事件"""
        handler = WebhookHandler()

        payload = {
            "eventKey": "pr:from_ref_updated",
            "pullRequest": {
                "id": 456,
                "fromRef": {
                    "repository": {
                        "slug": "repo",
                        "project": {"key": "PROJ"},
                    }
                },
            },
        }

        with patch("pr_agent.skills.bitbucket_review.webhook_handler.get_settings") as mock_settings:
            mock_settings.return_value.get.return_value = "https://bitbucket.example.com"
            event_type, pr_url, pr_data = handler.parse_event(payload)

        assert event_type == "updated"

    def test_should_process_no_filters(self):
        """测试无过滤器时应该处理"""
        handler = WebhookHandler()

        pr_data = {
            "author": {"user": {"name": "testuser"}},
            "title": "Test PR",
            "fromRef": {
                "repository": {
                    "slug": "repo",
                    "project": {"key": "PROJ"},
                }
            },
        }

        result = handler.should_process(pr_data, [], [], [])
        assert result is True

    def test_should_process_repository_filter(self):
        """测试仓库过滤"""
        handler = WebhookHandler()

        pr_data = {
            "author": {"user": {"name": "testuser"}},
            "title": "Test PR",
            "fromRef": {
                "repository": {
                    "slug": "archived-repo",
                    "project": {"key": "ARCHIVE"},
                }
            },
        }

        result = handler.should_process(pr_data, ["ARCHIVE/.*"], [], [])
        assert result is False

    def test_should_process_author_filter(self):
        """测试作者过滤"""
        handler = WebhookHandler()

        pr_data = {
            "author": {"user": {"name": "bot-user"}},
            "title": "Test PR",
            "fromRef": {
                "repository": {
                    "slug": "repo",
                    "project": {"key": "PROJ"},
                }
            },
        }

        result = handler.should_process(pr_data, [], ["bot-.*"], [])
        assert result is False

    def test_should_process_title_filter(self):
        """测试标题过滤"""
        handler = WebhookHandler()

        pr_data = {
            "author": {"user": {"name": "user"}},
            "title": "WIP: Work in progress",
            "fromRef": {
                "repository": {
                    "slug": "repo",
                    "project": {"key": "PROJ"},
                }
            },
        }

        result = handler.should_process(pr_data, [], [], ["WIP:.*"])
        assert result is False

    def test_extract_commands_from_comment(self):
        """测试从评论提取命令"""
        handler = WebhookHandler()

        pr_data = {
            "comment": {"text": "Please /review this PR and /improve the code"}
        }

        commands = handler.extract_commands("commented", False, pr_data, ["review"])
        assert "review" in commands
        assert "improve" in commands

    def test_extract_commands_default(self):
        """测试使用默认命令"""
        handler = WebhookHandler()

        pr_data = {"comment": {"text": "No commands here"}}

        commands = handler.extract_commands("opened", True, pr_data, ["review"])
        assert commands == ["review"]

    def test_verify_signature_no_secret(self):
        """测试无密钥时跳过验证"""
        handler = WebhookHandler()
        assert handler.verify_signature("payload", "signature") is True

    def test_verify_signature_with_secret(self):
        """测试签名验证"""
        handler = WebhookHandler(secret="test_secret")

        import hashlib
        import hmac

        payload = '{"test": "data"}'
        expected_sig = hmac.new(
            "test_secret".encode(), payload.encode(), hashlib.sha256
        ).hexdigest()

        assert handler.verify_signature(payload, expected_sig) is True
        assert handler.verify_signature(payload, "wrong_signature") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
