"""
Review执行器
运行PR审查并处理结果
"""
from typing import Any, Dict, List, Optional

from pr_agent.agent.pr_agent import PRAgent
from pr_agent.config_loader import get_settings
from pr_agent.log import get_logger
from pr_agent.skills.bitbucket_review.bitbucket_client import BitbucketServerClient


class ReviewRunner:
    """
    执行PR审查并处理结果
    """

    def __init__(self, bitbucket_client: BitbucketServerClient):
        """
        初始化Review执行器

        Args:
            bitbucket_client: Bitbucket客户端实例
        """
        self.client = bitbucket_client

    async def _run_pr_agent_command(
        self, pr_url: str, command: str, args: Optional[List[str]] = None
    ) -> bool:
        agent = PRAgent()
        return await agent.handle_request(pr_url, [command] + (args or []))

    async def run_review(
        self, pr_url: str, extra_args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行PR审查

        Args:
            pr_url: PR URL
            extra_args: 额外参数

        Returns:
            Dict: 审查结果
        """
        try:
            get_logger().info(f"Starting review for PR: {pr_url}")

            # 准备参数
            args = extra_args or []

            # 设置git provider为bitbucket_server
            original_git_provider = get_settings().get("CONFIG.GIT_PROVIDER")
            get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")

            try:
                # 创建并运行PRAgent
                await self._run_pr_agent_command(pr_url, "review", args)

                get_logger().info(f"Review completed for PR: {pr_url}")
                return {
                    "status": "success",
                    "pr_url": pr_url,
                    "command": "review",
                }
            finally:
                # 恢复原始配置
                if original_git_provider:
                    get_settings().set("CONFIG.GIT_PROVIDER", original_git_provider)

        except Exception as e:
            get_logger().error(f"Review failed for PR {pr_url}: {e}", exc_info=True)
            return {
                "status": "error",
                "pr_url": pr_url,
                "command": "review",
                "error": str(e),
            }

    async def run_describe(self, pr_url: str) -> Dict[str, Any]:
        """
        运行PR描述生成

        Args:
            pr_url: PR URL

        Returns:
            Dict: 执行结果
        """
        try:
            get_logger().info(f"Starting describe for PR: {pr_url}")

            # 设置git provider
            original_git_provider = get_settings().get("CONFIG.GIT_PROVIDER")
            get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")

            try:
                await self._run_pr_agent_command(pr_url, "describe")

                get_logger().info(f"Describe completed for PR: {pr_url}")
                return {
                    "status": "success",
                    "pr_url": pr_url,
                    "command": "describe",
                }
            finally:
                if original_git_provider:
                    get_settings().set("CONFIG.GIT_PROVIDER", original_git_provider)

        except Exception as e:
            get_logger().error(f"Describe failed for PR {pr_url}: {e}", exc_info=True)
            return {
                "status": "error",
                "pr_url": pr_url,
                "command": "describe",
                "error": str(e),
            }

    async def run_improve(self, pr_url: str) -> Dict[str, Any]:
        """
        运行代码改进建议

        Args:
            pr_url: PR URL

        Returns:
            Dict: 执行结果
        """
        try:
            get_logger().info(f"Starting improve for PR: {pr_url}")

            original_git_provider = get_settings().get("CONFIG.GIT_PROVIDER")
            get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")

            try:
                await self._run_pr_agent_command(pr_url, "improve")

                get_logger().info(f"Improve completed for PR: {pr_url}")
                return {
                    "status": "success",
                    "pr_url": pr_url,
                    "command": "improve",
                }
            finally:
                if original_git_provider:
                    get_settings().set("CONFIG.GIT_PROVIDER", original_git_provider)

        except Exception as e:
            get_logger().error(f"Improve failed for PR {pr_url}: {e}", exc_info=True)
            return {
                "status": "error",
                "pr_url": pr_url,
                "command": "improve",
                "error": str(e),
            }

    async def run_command(
        self, pr_url: str, command: str, args: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        运行任意PR命令

        Args:
            pr_url: PR URL
            command: 命令名称 (review, describe, improve等)
            args: 命令参数

        Returns:
            Dict: 执行结果
        """
        # 根据命令类型分发
        if command == "review":
            return await self.run_review(pr_url, args)
        elif command == "describe":
            return await self.run_describe(pr_url)
        elif command == "improve":
            return await self.run_improve(pr_url)
        else:
            try:
                get_logger().info(f"Starting command '{command}' for PR: {pr_url}")

                original_git_provider = get_settings().get("CONFIG.GIT_PROVIDER")
                get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")

                try:
                    await self._run_pr_agent_command(pr_url, command, args)

                    get_logger().info(
                        f"Command '{command}' completed for PR: {pr_url}"
                    )
                    return {
                        "status": "success",
                        "pr_url": pr_url,
                        "command": command,
                    }
                finally:
                    if original_git_provider:
                        get_settings().set("CONFIG.GIT_PROVIDER", original_git_provider)

            except Exception as e:
                get_logger().error(
                    f"Command '{command}' failed for PR {pr_url}: {e}", exc_info=True
                )
                return {
                    "status": "error",
                    "pr_url": pr_url,
                    "command": command,
                    "error": str(e),
                }

    async def run_multiple_commands(
        self, pr_url: str, commands: List[str], args: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        顺序运行多个命令

        Args:
            pr_url: PR URL
            commands: 命令列表
            args: 命令参数（应用于所有命令）

        Returns:
            List[Dict]: 每个命令的执行结果
        """
        results = []

        for command in commands:
            result = await self.run_command(pr_url, command, args)
            results.append(result)

            # 如果某个命令失败，可以选择是否继续
            if result.get("status") == "error":
                get_logger().warning(
                    f"Command '{command}' failed, but continuing with next command"
                )

        return results
