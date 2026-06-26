"""
Bitbucket Review Skill
整合webhook服务器、Bitbucket访问和PR审查功能
"""
import asyncio
import json
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, Request
from starlette.responses import JSONResponse

from pr_agent.log import get_logger
from pr_agent.skills.bitbucket_review.bitbucket_client import BitbucketServerClient
from pr_agent.skills.bitbucket_review.config import BitbucketReviewConfig
from pr_agent.skills.bitbucket_review.review_runner import ReviewRunner
from pr_agent.skills.bitbucket_review.webhook_handler import WebhookHandler


class BitbucketReviewSkill:
    """
    Bitbucket Server PR审查Skill

    功能：
    1. 启动webhook服务器监听PR事件
    2. 手动触发PR审查
    3. 管理Bitbucket Server连接
    """

    def __init__(self, config: Optional[BitbucketReviewConfig] = None):
        """
        初始化Skill

        Args:
            config: 配置对象，如果为None则从设置加载
        """
        self.config = config or BitbucketReviewConfig.from_settings()

        # 验证配置
        if not self.config.validate():
            raise ValueError(
                "Invalid configuration. Please provide server_url and "
                "either token or username+password"
            )

        # 初始化组件
        self.client = BitbucketServerClient(
            self.config.server_url,
            self.config.token,
            self.config.username,
            self.config.password,
        )

        self.webhook_handler = WebhookHandler(self.config.webhook_secret)
        self.review_runner = ReviewRunner(self.client)

        # FastAPI应用（用于webhook服务器）
        self.app: Optional[FastAPI] = None
        self._server_task: Optional[asyncio.Task] = None

    # === Public API ===

    async def review_pr(
        self, pr_url: str, commands: Optional[List[str]] = None, **kwargs
    ) -> Dict[str, Any]:
        """
        手动触发PR审查

        Args:
            pr_url: PR URL
            commands: 要执行的命令列表，默认为["review"]
            **kwargs: 额外参数

        Returns:
            Dict: 审查结果
        """
        commands = commands or ["review"]
        extra_args = kwargs.get("args", [])

        get_logger().info(f"Manual review triggered for PR: {pr_url}")

        if len(commands) == 1:
            return await self.review_runner.run_command(pr_url, commands[0], extra_args)
        else:
            results = await self.review_runner.run_multiple_commands(
                pr_url, commands, extra_args
            )
            return {"status": "success", "pr_url": pr_url, "results": results}

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        signature: str = "",
        raw_body: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        """
        处理webhook事件

        Args:
            payload: Webhook payload
            signature: 请求签名
            raw_body: Bitbucket签名使用的原始请求体

        Returns:
            Dict: 处理结果
        """
        # 验证签名
        if self.config.webhook_secret:
            body_to_verify = raw_body if raw_body is not None else json.dumps(
                payload, separators=(",", ":")
            )
            if not self.webhook_handler.verify_signature(body_to_verify, signature):
                get_logger().warning("Webhook signature verification failed")
                return {"status": "error", "message": "Invalid signature"}

        # 解析事件
        event_type, pr_url, pr_data = self.webhook_handler.parse_event(payload)

        if not pr_url:
            get_logger().warning("Could not extract PR URL from webhook payload")
            return {"status": "error", "message": "Invalid PR URL"}

        # 检查是否应该处理
        should_process = self.webhook_handler.should_process(
            pr_data,
            self.config.ignore_repositories,
            self.config.ignore_pr_authors,
            self.config.ignore_pr_title,
        )

        if not should_process:
            get_logger().info(f"Skipping PR {pr_url} due to filter rules")
            return {"status": "skipped", "pr_url": pr_url, "reason": "filtered"}

        # 根据事件类型决定是否自动审查
        is_new_pr = event_type == "opened"
        is_update = event_type == "updated"

        auto_review = False
        if is_new_pr and self.config.auto_review_on_open:
            auto_review = True
        elif is_update and self.config.auto_review_on_update:
            auto_review = True

        # 提取命令
        commands = self.webhook_handler.extract_commands(
            event_type, is_new_pr, pr_data, self.config.review_commands
        )

        # 如果不自动审查且不是评论触发，跳过
        if not auto_review and event_type != "commented":
            get_logger().info(
                f"Skipping PR {pr_url} - auto review disabled for {event_type}"
            )
            return {
                "status": "skipped",
                "pr_url": pr_url,
                "reason": "auto_review_disabled",
            }

        # 提取参数
        args = self.webhook_handler.extract_comment_args(pr_data)

        # 异步执行审查
        get_logger().info(
            f"Processing PR {pr_url} - event: {event_type}, commands: {commands}"
        )

        # 在后台执行命令
        asyncio.create_task(
            self._execute_commands_background(pr_url, commands, args)
        )

        return {
            "status": "processing",
            "pr_url": pr_url,
            "event_type": event_type,
            "commands": commands,
        }

    async def _execute_commands_background(
        self, pr_url: str, commands: List[str], args: List[str]
    ):
        """在后台执行命令"""
        try:
            if len(commands) == 1:
                await self.review_runner.run_command(pr_url, commands[0], args)
            else:
                await self.review_runner.run_multiple_commands(pr_url, commands, args)
        except Exception as e:
            get_logger().error(
                f"Background command execution failed for {pr_url}: {e}",
                exc_info=True,
            )

    def start_webhook_server(self, blocking: bool = True):
        """
        启动webhook服务器

        Args:
            blocking: 是否阻塞运行
        """
        self.app = FastAPI(title="Bitbucket Review Skill Webhook")

        @self.app.get("/")
        async def root():
            return {"status": "ok", "skill": "bitbucket-review"}

        @self.app.get("/health")
        async def health():
            conn_status = self.client.test_connection()
            return {
                "status": "healthy",
                "bitbucket": conn_status,
                "config": {
                    "server_url": self.config.server_url,
                    "auto_review_on_open": self.config.auto_review_on_open,
                    "auto_review_on_update": self.config.auto_review_on_update,
                },
            }

        @self.app.post("/webhook")
        async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
            raw_body = await request.body()
            payload = json.loads(raw_body)
            signature = request.headers.get("X-Hub-Signature", "")

            # 在后台处理webhook
            result = await self.handle_webhook(payload, signature, raw_body=raw_body)

            return JSONResponse(content=result)

        get_logger().info(
            f"Starting webhook server on {self.config.webhook_host}:{self.config.webhook_port}"
        )

        if blocking:
            uvicorn.run(
                self.app,
                host=self.config.webhook_host,
                port=self.config.webhook_port,
            )
        else:
            # 非阻塞模式
            config = uvicorn.Config(
                self.app,
                host=self.config.webhook_host,
                port=self.config.webhook_port,
                log_level="info",
            )
            server = uvicorn.Server(config)
            self._server_task = asyncio.create_task(server.serve())

    async def stop_webhook_server(self):
        """停止webhook服务器"""
        if self._server_task:
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                # Expected when stop_webhook_server cancels the background server task.
                get_logger().debug("Webhook server task cancellation acknowledged")
            self._server_task = None
            get_logger().info("Webhook server stopped")

    def test_connection(self) -> Dict[str, Any]:
        """
        测试Bitbucket Server连接

        Returns:
            Dict: 连接状态信息
        """
        return self.client.test_connection()


# === CLI入口 ===


def main():
    """CLI入口函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Bitbucket Review Skill")
    parser.add_argument(
        "command",
        choices=["start-webhook", "review", "test-connection"],
        help="Command to execute",
    )
    parser.add_argument("--pr-url", help="PR URL (for review command)")
    parser.add_argument(
        "--commands",
        nargs="+",
        default=["review"],
        help="Commands to run (default: review)",
    )

    args = parser.parse_args()

    # 创建skill实例
    skill = BitbucketReviewSkill()

    if args.command == "start-webhook":
        print("Starting webhook server...")
        skill.start_webhook_server(blocking=True)

    elif args.command == "review":
        if not args.pr_url:
            print("Error: --pr-url is required for review command")
            return

        print(f"Reviewing PR: {args.pr_url}")
        result = asyncio.run(skill.review_pr(args.pr_url, args.commands))
        print(f"Result: {result}")

    elif args.command == "test-connection":
        print("Testing connection...")
        result = skill.test_connection()
        print(f"Connection status: {result}")


if __name__ == "__main__":
    main()
