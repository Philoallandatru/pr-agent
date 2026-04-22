# Webhook Notifications

PR-Agent 支持通过 Webhook 发送 PR 审查事件通知到多个平台。

## 支持的平台

- **Slack** - 企业协作平台
- **DingTalk (钉钉)** - 阿里巴巴企业通讯工具
- **WeCom (企业微信)** - 腾讯企业通讯工具
- **Custom Webhooks** - 自定义 HTTP 端点

## 通知事件

系统会在以下事件发生时发送通知：

- `review_started` - PR 审查开始
- `review_completed` - PR 审查完成
- `review_failed` - PR 审查失败
- `pr_approved` - PR 被批准
- `pr_rejected` - PR 被拒绝

## 配置

在 `configuration.toml` 或 `.pr_agent.toml` 中配置：

```toml
[webhook]
# 启用 Webhook 通知
enabled = true
timeout = 10
retry_count = 3

# Slack 配置
slack_enabled = true
slack_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

# 钉钉配置
dingtalk_enabled = true
dingtalk_url = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
dingtalk_secret = "YOUR_SECRET"  # 可选，用于签名验证

# 企业微信配置
wecom_enabled = true
wecom_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"

# 自定义 Webhook
custom_urls = [
    "https://your-server.com/webhook1",
    "https://your-server.com/webhook2"
]

# 控制发送哪些事件通知
notify_review_started = true
notify_review_completed = true
notify_review_failed = true
notify_pr_approved = false
notify_pr_rejected = false
```

## Slack 设置

### 1. 创建 Incoming Webhook

1. 访问 https://api.slack.com/apps
2. 创建新应用或选择现有应用
3. 启用 "Incoming Webhooks"
4. 添加新的 Webhook 到工作区
5. 复制 Webhook URL

### 2. 配置 PR-Agent

```toml
[webhook]
enabled = true
slack_enabled = true
slack_url = "https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX"
```

### 3. 消息格式

Slack 消息包含：
- 事件标题和状态图标
- 仓库名称
- PR 编号和作者
- PR 标题
- 查看 PR 的按钮链接

## 钉钉设置

### 1. 创建自定义机器人

1. 打开钉钉群聊
2. 点击群设置 → 智能群助手 → 添加机器人
3. 选择"自定义"机器人
4. 设置安全设置（推荐使用加签）
5. 复制 Webhook 地址和密钥

### 2. 配置 PR-Agent

```toml
[webhook]
enabled = true
dingtalk_enabled = true
dingtalk_url = "https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN"
dingtalk_secret = "SEC1234567890abcdef"  # 如果启用了加签
```

### 3. 消息格式

钉钉消息使用 Markdown 格式：
- 标题和事件状态
- 仓库、PR 编号、作者
- PR 标题
- 查看 PR 的链接

## 企业微信设置

### 1. 创建群机器人

1. 在企业微信群中，点击右上角 → 添加群机器人
2. 选择"自定义机器人"
3. 设置机器人名称和头像
4. 复制 Webhook 地址

### 2. 配置 PR-Agent

```toml
[webhook]
enabled = true
wecom_enabled = true
wecom_url = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY"
```

### 3. 消息格式

企业微信消息为纯文本格式，包含所有关键信息。

## 自定义 Webhook

### 1. 配置端点

```toml
[webhook]
enabled = true
custom_urls = [
    "https://your-server.com/pr-notifications"
]
```

### 2. 消息格式

自定义 Webhook 接收 JSON 格式的 POST 请求：

```json
{
  "event": "review_completed",
  "timestamp": "2026-04-22T10:30:00",
  "pr": {
    "repository": "PROJECT/repo-name",
    "pr_number": 123,
    "author": "username",
    "title": "Add new feature",
    "url": "https://bitbucket.example.com/projects/PROJECT/repos/repo-name/pull-requests/123"
  },
  "review": {
    "duration": 45.5,
    "commands": ["/describe", "/review"],
    "status": "success"
  }
}
```

### 3. 实现示例

**Python Flask:**

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/pr-notifications', methods=['POST'])
def handle_notification():
    data = request.json
    event = data['event']
    pr = data['pr']
    
    print(f"Received {event} for PR #{pr['pr_number']}")
    
    # 处理通知...
    
    return {'status': 'ok'}, 200
```

**Node.js Express:**

```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/pr-notifications', (req, res) => {
  const { event, pr, review } = req.body;
  
  console.log(`Received ${event} for PR #${pr.pr_number}`);
  
  // 处理通知...
  
  res.json({ status: 'ok' });
});

app.listen(3000);
```

## 重试机制

系统会自动重试失败的通知：

- 默认重试 3 次
- 使用指数退避策略（2^n 秒）
- 可通过 `retry_count` 配置

```toml
[webhook]
retry_count = 5  # 最多重试 5 次
timeout = 15     # 请求超时 15 秒
```

## 并发发送

通知会并发发送到所有配置的渠道，不会相互阻塞。

## 测试通知

使用 Python 测试通知功能：

```python
import asyncio
from pr_agent.notifications import notify_review_completed

pr_data = {
    'repository': 'TEST/test-repo',
    'pr_number': 123,
    'author': 'testuser',
    'title': 'Test PR',
    'url': 'https://bitbucket.example.com/pr/123'
}

review_data = {
    'duration': 30.5,
    'commands': ['/review'],
    'status': 'success'
}

asyncio.run(notify_review_completed(pr_data, review_data))
```

## 故障排查

### 通知未发送

1. 检查 `webhook.enabled = true`
2. 检查对应平台的 `*_enabled = true`
3. 验证 Webhook URL 正确
4. 查看日志中的错误信息

### Slack 通知失败

- 验证 Webhook URL 格式正确
- 确认应用有发送消息权限
- 检查 Slack 工作区设置

### 钉钉通知失败

- 验证 access_token 正确
- 如果使用加签，确认 secret 正确
- 检查机器人是否被禁用
- 确认群聊中机器人仍然存在

### 企业微信通知失败

- 验证 Webhook key 正确
- 确认机器人未被删除
- 检查企业微信管理后台设置

## 安全建议

1. **保护 Webhook URL**
   - 不要将 URL 提交到公开仓库
   - 使用环境变量或 `.secrets.toml`

2. **使用签名验证**
   - 钉钉：启用加签功能
   - 自定义 Webhook：实现签名验证

3. **限制权限**
   - 仅授予必要的发送消息权限
   - 定期轮换 Webhook URL

## 示例配置

**完整配置示例：**

```toml
[webhook]
enabled = true
timeout = 10
retry_count = 3

# Slack
slack_enabled = true
slack_url = "${SLACK_WEBHOOK_URL}"

# 钉钉
dingtalk_enabled = true
dingtalk_url = "${DINGTALK_WEBHOOK_URL}"
dingtalk_secret = "${DINGTALK_SECRET}"

# 企业微信
wecom_enabled = false
wecom_url = ""

# 自定义
custom_urls = []

# 事件控制
notify_review_started = true
notify_review_completed = true
notify_review_failed = true
notify_pr_approved = false
notify_pr_rejected = false
```

**环境变量（.env）：**

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=YOUR_TOKEN
DINGTALK_SECRET=SEC1234567890abcdef
```

## 相关文档

- [Slack Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [钉钉自定义机器人](https://open.dingtalk.com/document/robots/custom-robot-access)
- [企业微信群机器人](https://developer.work.weixin.qq.com/document/path/91770)
