"""
Bitbucket Review Skill Configuration
"""
from dataclasses import dataclass, field
from typing import List, Optional

from pr_agent.config_loader import get_settings


@dataclass
class BitbucketReviewConfig:
    """Bitbucket Server Review Skill配置"""

    # Bitbucket Server配置
    server_url: str
    token: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # Webhook配置
    webhook_secret: Optional[str] = None
    webhook_port: int = 3000
    webhook_host: str = "0.0.0.0"

    # Review配置
    auto_review_on_open: bool = True
    auto_review_on_update: bool = False
    review_commands: List[str] = field(default_factory=lambda: ["review"])

    # 过滤配置
    ignore_repositories: List[str] = field(default_factory=list)
    ignore_pr_authors: List[str] = field(default_factory=list)
    ignore_pr_title: List[str] = field(default_factory=list)

    @classmethod
    def from_settings(cls):
        """从pr_agent配置加载"""
        settings = get_settings()

        return cls(
            # Bitbucket Server配置
            server_url=settings.get("BITBUCKET_SERVER.URL", ""),
            token=settings.get("BITBUCKET_SERVER.BEARER_TOKEN"),
            username=settings.get("BITBUCKET_SERVER.USERNAME"),
            password=settings.get("BITBUCKET_SERVER.PASSWORD"),
            # Webhook配置
            webhook_secret=settings.get("BITBUCKET_SERVER.WEBHOOK_SECRET"),
            webhook_port=int(settings.get("WEBHOOK_PORT", 3000)),
            webhook_host=settings.get("WEBHOOK_HOST", "0.0.0.0"),
            # Review配置
            auto_review_on_open=settings.get("BITBUCKET_SERVER.AUTO_REVIEW_ON_OPEN", True),
            auto_review_on_update=settings.get("BITBUCKET_SERVER.AUTO_REVIEW_ON_UPDATE", False),
            review_commands=settings.get("BITBUCKET_SERVER.PR_COMMANDS", ["review"]),
            # 过滤配置
            ignore_repositories=settings.get("CONFIG.IGNORE_REPOSITORIES", []),
            ignore_pr_authors=settings.get("CONFIG.IGNORE_PR_AUTHORS", []),
            ignore_pr_title=settings.get("CONFIG.IGNORE_PR_TITLE", []),
        )

    def validate(self) -> bool:
        """验证配置是否有效"""
        if not self.server_url:
            return False

        # 必须提供token或username+password
        if not self.token and not (self.username and self.password):
            return False

        return True
