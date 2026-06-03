"""
Bitbucket Server API客户端封装
简化Bitbucket Server API访问
"""
from typing import Any, Dict, List, Optional

from atlassian.bitbucket import Bitbucket

from pr_agent.config_loader import get_settings
from pr_agent.git_providers.bitbucket_server_provider import BitbucketServerProvider
from pr_agent.log import get_logger


class BitbucketServerClient:
    """
    封装BitbucketServerProvider的核心API访问方法
    提供简化的接口用于skill
    """

    def __init__(
        self,
        server_url: str,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        初始化Bitbucket Server客户端

        Args:
            server_url: Bitbucket Server URL
            token: Bearer token (推荐)
            username: 用户名 (如果不使用token)
            password: 密码 (如果不使用token)
        """
        self.server_url = server_url
        self.token = token
        self.username = username
        self.password = password

        # 初始化底层Bitbucket客户端
        if self.token:
            self.bitbucket_client = Bitbucket(url=server_url, token=token)
        else:
            self.bitbucket_client = Bitbucket(
                url=server_url, username=username, password=password
            )

        # 缓存provider实例
        self._providers: Dict[str, BitbucketServerProvider] = {}

    def _get_provider(self, pr_url: str) -> BitbucketServerProvider:
        """获取或创建BitbucketServerProvider实例"""
        if pr_url not in self._providers:
            # 临时设置配置
            original_git_provider = get_settings().get("CONFIG.GIT_PROVIDER")
            get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")

            try:
                self._providers[pr_url] = BitbucketServerProvider(
                    pr_url=pr_url, bitbucket_client=self.bitbucket_client
                )
            finally:
                # 恢复原始配置
                if original_git_provider:
                    get_settings().set("CONFIG.GIT_PROVIDER", original_git_provider)

        return self._providers[pr_url]

    def authenticate(self) -> bool:
        """
        验证凭证是否有效

        Returns:
            bool: 认证是否成功
        """
        try:
            # 尝试获取应用信息来验证连接
            self.bitbucket_client.get("rest/api/1.0/application-properties")
            return True
        except Exception as e:
            get_logger().error(f"Authentication failed: {e}")
            return False

    def get_pr(self, pr_url: str) -> Dict[str, Any]:
        """
        获取PR详情

        Args:
            pr_url: PR URL

        Returns:
            Dict: PR数据
        """
        provider = self._get_provider(pr_url)
        return provider.get_pr_data()

    def get_diff(self, pr_url: str) -> str:
        """
        获取PR diff

        Args:
            pr_url: PR URL

        Returns:
            str: PR diff内容
        """
        provider = self._get_provider(pr_url)
        return provider.get_diff_files()

    def get_files(self, pr_url: str) -> List[str]:
        """
        获取PR修改的文件列表

        Args:
            pr_url: PR URL

        Returns:
            List[str]: 文件路径列表
        """
        provider = self._get_provider(pr_url)
        return provider.get_files()

    def post_comment(self, pr_url: str, text: str) -> bool:
        """
        发布PR评论

        Args:
            pr_url: PR URL
            text: 评论内容

        Returns:
            bool: 是否成功
        """
        try:
            provider = self._get_provider(pr_url)
            provider.publish_comment(text)
            return True
        except Exception as e:
            get_logger().error(f"Failed to post comment: {e}")
            return False

    def post_inline_comment(
        self, pr_url: str, file_path: str, line: int, text: str
    ) -> bool:
        """
        发布行内评论

        Args:
            pr_url: PR URL
            file_path: 文件路径
            line: 行号
            text: 评论内容

        Returns:
            bool: 是否成功
        """
        try:
            provider = self._get_provider(pr_url)
            provider.publish_inline_comment(text, file_path, line)
            return True
        except Exception as e:
            get_logger().error(f"Failed to post inline comment: {e}")
            return False

    def get_pr_description(self, pr_url: str) -> str:
        """
        获取PR描述

        Args:
            pr_url: PR URL

        Returns:
            str: PR描述
        """
        provider = self._get_provider(pr_url)
        return provider.get_pr_description()

    def get_pr_labels(self, pr_url: str) -> List[str]:
        """
        获取PR标签

        Args:
            pr_url: PR URL

        Returns:
            List[str]: 标签列表
        """
        provider = self._get_provider(pr_url)
        return provider.get_pr_labels()

    def test_connection(self) -> Dict[str, Any]:
        """
        测试连接并返回服务器信息

        Returns:
            Dict: 服务器信息
        """
        try:
            app_props = self.bitbucket_client.get("rest/api/1.0/application-properties")
            return {
                "status": "connected",
                "server_url": self.server_url,
                "version": app_props.get("version", "unknown"),
                "display_name": app_props.get("displayName", "Bitbucket Server"),
            }
        except Exception as e:
            return {
                "status": "failed",
                "server_url": self.server_url,
                "error": str(e),
            }
