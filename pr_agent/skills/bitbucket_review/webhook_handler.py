"""
Webhook事件处理器
解析和处理Bitbucket Server webhook事件
"""
import hashlib
import hmac
import re
from typing import Any, Dict, List, Optional, Tuple

from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger


class WebhookHandler:
    """
    处理Bitbucket Server webhook事件
    """

    def __init__(self, secret: Optional[str] = None):
        """
        初始化Webhook处理器

        Args:
            secret: Webhook密钥（用于验证签名）
        """
        self.secret = secret

    def verify_signature(self, payload: str, signature: str) -> bool:
        """
        验证webhook签名

        Args:
            payload: 原始payload字符串
            signature: 请求头中的签名

        Returns:
            bool: 签名是否有效
        """
        if not self.secret:
            # 如果没有配置密钥，跳过验证
            return True

        try:
            expected_signature = hmac.new(
                self.secret.encode(), payload.encode(), hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            get_logger().error(f"Signature verification failed: {e}")
            return False

    def parse_event(self, payload: Dict[str, Any]) -> Tuple[str, str, Dict[str, Any]]:
        """
        解析webhook事件

        Args:
            payload: Webhook payload

        Returns:
            Tuple[str, str, Dict]: (event_type, pr_url, pr_data)
        """
        event_key = payload.get("eventKey", "")
        pr_data = payload.get("pullRequest", {})

        # 提取PR信息
        pr_id = pr_data.get("id")
        from_ref = pr_data.get("fromRef", {})
        repository = from_ref.get("repository", {})
        project = repository.get("project", {})

        # 构建PR URL
        server_url = get_settings().get("BITBUCKET_SERVER.URL", "")
        project_key = project.get("key", "")
        repo_slug = repository.get("slug", "")

        if server_url and project_key and repo_slug and pr_id:
            pr_url = (
                f"{server_url}/projects/{project_key}/"
                f"repos/{repo_slug}/pull-requests/{pr_id}"
            )
        else:
            pr_url = ""

        # 确定事件类型
        if "pr:opened" in event_key:
            event_type = "opened"
        elif "pr:modified" in event_key or "pr:from_ref_updated" in event_key:
            event_type = "updated"
        elif "pr:comment:added" in event_key:
            event_type = "commented"
        elif "pr:merged" in event_key:
            event_type = "merged"
        elif "pr:declined" in event_key:
            event_type = "declined"
        else:
            event_type = "unknown"

        return event_type, pr_url, pr_data

    def should_process(
        self,
        pr_data: Dict[str, Any],
        ignore_repositories: List[str],
        ignore_pr_authors: List[str],
        ignore_pr_title: List[str],
    ) -> bool:
        """
        判断是否应该处理该PR

        Args:
            pr_data: PR数据
            ignore_repositories: 要忽略的仓库列表（支持正则）
            ignore_pr_authors: 要忽略的作者列表（支持正则）
            ignore_pr_title: 要忽略的标题列表（支持正则）

        Returns:
            bool: 是否应该处理
        """
        # 提取仓库信息
        from_ref = pr_data.get("fromRef", {})
        repository = from_ref.get("repository", {})
        project = repository.get("project", {})
        project_key = project.get("key", "")
        repo_slug = repository.get("slug", "")
        repo_full_name = f"{project_key}/{repo_slug}" if project_key and repo_slug else ""

        # 检查仓库过滤
        if repo_full_name and ignore_repositories:
            for regex in ignore_repositories:
                if re.search(regex, repo_full_name):
                    get_logger().info(
                        f"Ignoring PR from repository '{repo_full_name}' "
                        f"due to ignore_repositories setting"
                    )
                    return False

        # 提取作者信息
        author = pr_data.get("author", {})
        author_user = author.get("user", {})
        author_name = author_user.get("name", "")

        # 检查作者过滤
        if author_name and ignore_pr_authors:
            for regex in ignore_pr_authors:
                if re.search(regex, author_name):
                    get_logger().info(
                        f"Ignoring PR from author '{author_name}' "
                        f"due to ignore_pr_authors setting"
                    )
                    return False

        # 提取PR标题
        pr_title = pr_data.get("title", "")

        # 检查标题过滤
        if pr_title and ignore_pr_title:
            for regex in ignore_pr_title:
                if re.search(regex, pr_title):
                    get_logger().info(
                        f"Ignoring PR with title '{pr_title}' "
                        f"due to ignore_pr_title setting"
                    )
                    return False

        return True

    def extract_commands(
        self,
        event_type: str,
        is_new_pr: bool,
        pr_data: Dict[str, Any],
        default_commands: List[str],
    ) -> List[str]:
        """
        提取要执行的命令

        Args:
            event_type: 事件类型
            is_new_pr: 是否是新PR
            pr_data: PR数据
            default_commands: 默认命令列表

        Returns:
            List[str]: 要执行的命令列表
        """
        commands = []

        # 如果是评论事件，尝试从评论中提取命令
        if event_type == "commented":
            comment_text = pr_data.get("comment", {}).get("text", "")
            # 查找 /review, /describe, /improve 等命令
            command_pattern = r"/(review|describe|improve|ask|update_changelog|help|test)"
            matches = re.findall(command_pattern, comment_text, re.IGNORECASE)
            if matches:
                commands = [match.lower() for match in matches]

        # 如果没有从评论中提取到命令，使用默认命令
        if not commands:
            commands = default_commands.copy()

        return commands

    def extract_comment_args(self, pr_data: Dict[str, Any]) -> List[str]:
        """
        从评论中提取命令参数

        Args:
            pr_data: PR数据

        Returns:
            List[str]: 参数列表
        """
        comment_text = pr_data.get("comment", {}).get("text", "")

        # 查找命令和参数，例如: /review --num_code_suggestions=5
        pattern = r"/\w+\s+(.*?)(?=\n|$)"
        match = re.search(pattern, comment_text)

        if match:
            args_str = match.group(1).strip()
            # 简单的参数解析（支持 --key=value 格式）
            import shlex

            try:
                return shlex.split(args_str)
            except Exception:
                return []

        return []
