# Bitbucket Server Review Skill 实现计划

## 目标

将现有的Bitbucket Server webhook服务器、验证、访问功能（如comment等）与PR review功能整合，创建一个独立的skill，可以通过Claude Code的/review或类似命令触发。

---

## 当前架构分析

### 1. 现有组件

**Webhook服务器层** (`pr_agent/servers/bitbucket_server_webhook.py`)
- FastAPI路由处理webhook事件
- 验证webhook签名
- 解析PR事件（opened, updated, commented）
- 过滤逻辑（ignore_repositories, ignore_pr_authors等）
- 后台任务调度

**Git Provider层** (`pr_agent/git_providers/bitbucket_server_provider.py`)
- Bitbucket Server API客户端封装
- 认证（Bearer Token或用户名密码）
- PR数据获取（diff, files, comments）
- 评论发布（publish_comment, publish_inline_comment）
- 分支、文件操作

**PR审查层** (`pr_agent/tools/pr_reviewer.py`)
- AI驱动的代码审查逻辑
- 生成审查建议
- 效率指标追踪

**核心代理** (`pr_agent/agent/pr_agent.py`)
- 命令路由（review, describe, improve等）
- 工具编排

### 2. 依赖关系

```
Webhook Server
    ↓ (解析事件，构建PR URL)
PRAgent
    ↓ (路由命令)
PRReviewer
    ↓ (获取PR数据)
BitbucketServerProvider
    ↓ (调用API)
Bitbucket Server REST API
```

---

## 设计方案

### 方案架构

创建一个**独立的skill**，包含三个核心能力：

1. **Webhook监听能力** - 接收并处理Bitbucket Server事件
2. **Bitbucket访问能力** - 封装API调用（认证、获取PR、发布评论）
3. **Review集成能力** - 调用PR审查逻辑并处理结果

### Skill结构

```
pr_agent/
├── skills/
│   └── bitbucket_review/
│       ├── __init__.py
│       ├── skill.py              # Skill主入口
│       ├── webhook_handler.py    # Webhook处理逻辑
│       ├── bitbucket_client.py   # Bitbucket API客户端封装
│       ├── review_runner.py      # Review执行器
│       └── config.py              # Skill配置
└── .claude/
    └── skills/
        └── bitbucket-review.md   # Skill定义（Claude Code格式）
```

---

## 实现步骤

### Phase 1: 提取和封装核心组件 (2-3小时)

#### 1.1 创建Skill目录结构

```bash
mkdir -p pr_agent/skills/bitbucket_review
touch pr_agent/skills/__init__.py
touch pr_agent/skills/bitbucket_review/{__init__.py,skill.py,webhook_handler.py,bitbucket_client.py,review_runner.py,config.py}
```

#### 1.2 提取Bitbucket客户端封装

**文件**: `pr_agent/skills/bitbucket_review/bitbucket_client.py`

**功能**:
- 封装`BitbucketServerProvider`的核心API访问方法
- 提供简化的接口：`get_pr()`, `get_diff()`, `post_comment()`, `post_inline_comment()`
- 集成认证逻辑

**从以下位置提取**:
- `pr_agent/git_providers/bitbucket_server_provider.py` (第24-600行)
- 方法：`__init__`, `publish_comment`, `publish_inline_comment`, `get_diff_files`, `get_pr_description`

**伪代码**:
```python
class BitbucketServerClient:
    def __init__(self, server_url, token=None, username=None, password=None):
        # 初始化Bitbucket API客户端
        
    def authenticate(self):
        # 验证凭证
        
    def get_pr(self, pr_url):
        # 获取PR详情
        
    def get_diff(self, pr_url):
        # 获取PR diff
        
    def post_comment(self, pr_url, text):
        # 发布评论
        
    def post_inline_comment(self, pr_url, file_path, line, text):
        # 发布行内评论
```

#### 1.3 提取Webhook处理逻辑

**文件**: `pr_agent/skills/bitbucket_review/webhook_handler.py`

**功能**:
- 解析webhook payload
- 验证webhook签名
- 提取PR信息
- 应用过滤规则

**从以下位置提取**:
- `pr_agent/servers/bitbucket_server_webhook.py` (第64-143行, 第148-218行)
- 函数：`should_process_pr_logic`, `handle_webhook`

**伪代码**:
```python
class WebhookHandler:
    def __init__(self, secret=None):
        self.secret = secret
        
    def verify_signature(self, payload, signature):
        # 验证webhook签名
        
    def parse_event(self, payload):
        # 解析webhook事件
        # 返回：event_type, pr_url, pr_data
        
    def should_process(self, pr_data):
        # 应用过滤规则
        # 返回：bool
        
    def extract_commands(self, event_type, is_new_pr):
        # 提取要执行的命令
        # 返回：List[str]
```

#### 1.4 创建Review执行器

**文件**: `pr_agent/skills/bitbucket_review/review_runner.py`

**功能**:
- 调用PRReviewer
- 处理异常
- 格式化输出

**集成点**:
- `pr_agent/tools/pr_reviewer.py` (PRReviewer类)
- `pr_agent/agent/pr_agent.py` (PRAgent类)

**伪代码**:
```python
class ReviewRunner:
    def __init__(self, bitbucket_client):
        self.client = bitbucket_client
        
    async def run_review(self, pr_url, extra_args=None):
        # 1. 初始化PRReviewer
        # 2. 执行审查
        # 3. 格式化结果
        # 4. 通过bitbucket_client发布评论
        
    async def run_describe(self, pr_url):
        # 运行describe命令
        
    async def run_improve(self, pr_url):
        # 运行improve命令
```

### Phase 2: 实现Skill主入口 (1-2小时)

#### 2.1 创建Skill配置

**文件**: `pr_agent/skills/bitbucket_review/config.py`

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class BitbucketReviewConfig:
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
    review_commands: list = None  # 默认["review"]
    
    # 过滤配置
    ignore_repositories: list = None
    ignore_pr_authors: list = None
    ignore_pr_title: list = None
    
    @classmethod
    def from_settings(cls):
        # 从pr_agent配置加载
```

#### 2.2 实现Skill主类

**文件**: `pr_agent/skills/bitbucket_review/skill.py`

```python
class BitbucketReviewSkill:
    """
    Bitbucket Server PR审查Skill
    
    功能：
    1. 启动webhook服务器监听PR事件
    2. 手动触发PR审查
    3. 管理Bitbucket Server连接
    """
    
    def __init__(self, config: BitbucketReviewConfig):
        self.config = config
        self.client = BitbucketServerClient(
            config.server_url, 
            config.token, 
            config.username, 
            config.password
        )
        self.webhook_handler = WebhookHandler(config.webhook_secret)
        self.review_runner = ReviewRunner(self.client)
        
    # === Public API ===
    
    async def review_pr(self, pr_url: str, **kwargs):
        """手动触发PR审查"""
        
    async def start_webhook_server(self):
        """启动webhook服务器"""
        
    async def handle_webhook(self, payload: dict, signature: str):
        """处理webhook事件"""
        
    def test_connection(self):
        """测试Bitbucket Server连接"""
```

### Phase 3: 创建Claude Code Skill定义 (30分钟)

**文件**: `.claude/skills/bitbucket-review.md`

```markdown
# bitbucket-review

Review Bitbucket Server pull requests with AI assistance.

## Usage

### Start webhook server
/bitbucket-review start-webhook

### Review a specific PR
/bitbucket-review review <pr_url>

### Check connection status
/bitbucket-review status

## Configuration

Set these environment variables or in `.pr_agent.toml`:

- BITBUCKET_SERVER_URL
- BITBUCKET_SERVER_TOKEN (或 USERNAME + PASSWORD)
- OPENAI_API_KEY (或其他AI provider key)

## Examples

```
# 启动webhook服务器
/bitbucket-review start-webhook

# 审查特定PR
/bitbucket-review review https://bitbucket.example.com/projects/PROJ/repos/repo/pull-requests/123

# 检查连接状态
/bitbucket-review status
```

## Implementation

This skill integrates:
- Bitbucket Server webhook handling
- PR data fetching via Bitbucket REST API
- AI-powered code review
- Automated comment posting
```

### Phase 4: 集成和测试 (1-2小时)

#### 4.1 单元测试

**文件**: `tests/unittest/test_bitbucket_review_skill.py`

测试覆盖：
- BitbucketServerClient基本操作
- WebhookHandler事件解析
- ReviewRunner审查流程
- 认证和错误处理

#### 4.2 集成测试

**文件**: `tests/integration/test_bitbucket_review_skill_e2e.py`

测试场景：
- 完整的webhook接收->审查->评论流程
- 手动触发审查
- 过滤规则验证

#### 4.3 文档更新

更新以下文档：
- `docs/SKILLS.md` (新建) - 列出所有可用skills
- `docs/BITBUCKET_SERVER_QUICKSTART.md` - 添加使用skill的方式
- `README.md` - 添加skill使用示例

---

## 向后兼容性

### 保留现有方式

原有的启动方式继续可用：
```bash
# 方式1: 直接启动webhook服务器（旧方式）
python -m pr_agent.servers.bitbucket_server_webhook

# 方式2: 使用启动脚本（旧方式）
./start_webhook.sh

# 方式3: 使用新的skill（新方式）
claude code /bitbucket-review start-webhook
```

### 迁移路径

1. Skill复用现有的`BitbucketServerProvider`
2. 配置系统保持兼容（优先读取`.pr_agent.toml`）
3. 逐步弃用直接调用服务器的方式，推荐使用skill

---

## 优势

### 1. 模块化
- Skill是自包含的，易于维护
- 清晰的职责分离
- 便于测试

### 2. 可扩展性
- 其他Git平台可以创建类似的skill（github-review, gitlab-review）
- 复用review逻辑

### 3. 用户友好
- 通过Claude Code统一入口
- 简化配置和使用
- 更好的错误提示

### 4. 集成coding agent
- 可以在Claude Code会话中直接调用
- 与其他skill协同工作
- 支持交互式审查流程

---

## 风险和缓解

### 风险1: 代码重复
**缓解**: 复用现有的`BitbucketServerProvider`和`PRReviewer`，只提取必要的包装层

### 风险2: 配置复杂性
**缓解**: 提供默认配置，自动从环境变量和`.pr_agent.toml`加载

### 风险3: 向后兼容性
**缓解**: 保留所有现有入口，skill作为新的可选方式

---

## 时间估算

- **Phase 1**: 2-3小时（提取和封装）
- **Phase 2**: 1-2小时（Skill主入口）
- **Phase 3**: 30分钟（Claude Code定义）
- **Phase 4**: 1-2小时（集成测试）

**总计**: 5-8小时

---

## 下一步

1. 确认设计方案
2. 创建skill目录结构
3. 开始Phase 1实现
4. 迭代测试和优化

---

## 待讨论的问题

1. Skill的命令接口设计是否符合预期？
2. 是否需要支持其他Bitbucket命令（如approve, merge）？
3. 是否需要交互式审查模式（逐个确认每条建议）？
4. 如何处理长时间运行的审查任务？（异步通知？）
