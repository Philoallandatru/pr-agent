# Bitbucket Review Skill 技术实现详解

本文档详细说明Bitbucket Review Skill的技术实现细节。

---

## 目录

1. [架构设计](#架构设计)
2. [核心组件](#核心组件)
3. [数据流](#数据流)
4. [关键技术](#关键技术)
5. [与现有系统的集成](#与现有系统的集成)

---

## 架构设计

### 整体架构图

```
                     外部系统
                        │
        ┌───────────────┼───────────────┐
        │               │               │
   Bitbucket       Command Line    Claude Code
    Server          (CLI)           (未来)
        │               │               │
        └───────────────┼───────────────┘
                        │
                        ▼
            ┌────────────────────┐
            │  Skill Entry Point │
            │  (skill.py)        │
            └────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
   ┌────────┐    ┌──────────┐    ┌──────────┐
   │ Config │    │  Client  │    │ Handler  │
   └────────┘    └──────────┘    └──────────┘
                        │               │
                        └───────┬───────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ ReviewRunner │
                        └──────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │   PRAgent    │
                        │ (现有系统)    │
                        └──────────────┘
                                │
                    ┌───────────┼───────────┐
                    │           │           │
                    ▼           ▼           ▼
              BitbucketServer  AI Model  Database
                   API         (GPT-4)   (SQLite)
```

### 分层设计

**Layer 1: 入口层**
- `BitbucketReviewSkill` - 主入口，提供公共API
- FastAPI应用 - Webhook服务器

**Layer 2: 业务逻辑层**
- `WebhookHandler` - 事件解析和过滤
- `ReviewRunner` - 审查执行

**Layer 3: 数据访问层**
- `BitbucketServerClient` - API封装
- `BitbucketReviewConfig` - 配置管理

**Layer 4: 基础设施层**
- `BitbucketServerProvider` (复用) - 底层API客户端
- `PRAgent` (复用) - 审查引擎

---

## 核心组件

### 1. BitbucketReviewConfig (配置管理)

**位置**: `pr_agent/skills/bitbucket_review/config.py`

**设计模式**: 数据类 (Dataclass)

**核心代码**:
```python
@dataclass
class BitbucketReviewConfig:
    # Bitbucket Server配置
    server_url: str
    token: Optional[str] = None
    
    # Webhook配置
    webhook_port: int = 3000
    
    # Review配置
    auto_review_on_open: bool = True
    
    # 过滤配置
    ignore_repositories: List[str] = field(default_factory=list)
    
    @classmethod
    def from_settings(cls):
        """从环境变量和.pr_agent.toml加载配置"""
        settings = get_settings()
        return cls(
            server_url=settings.get("BITBUCKET_SERVER.URL"),
            # ...
        )
    
    def validate(self) -> bool:
        """验证配置完整性"""
        if not self.server_url:
            return False
        if not self.token and not (self.username and self.password):
            return False
        return True
```

**关键设计决策**:
1. 使用dataclass简化配置管理
2. 支持环境变量和配置文件双重来源
3. 提供验证方法确保配置完整性
4. 使用Optional和默认值提高灵活性

---

### 2. BitbucketServerClient (API封装)

**位置**: `pr_agent/skills/bitbucket_review/bitbucket_client.py`

**设计模式**: 适配器模式 (Adapter Pattern)

**核心架构**:
```python
class BitbucketServerClient:
    def __init__(self, server_url, token=None, username=None, password=None):
        # 初始化底层Bitbucket客户端
        if token:
            self.bitbucket_client = Bitbucket(url=server_url, token=token)
        else:
            self.bitbucket_client = Bitbucket(
                url=server_url, username=username, password=password
            )
        
        # 缓存provider实例
        self._providers: Dict[str, BitbucketServerProvider] = {}
    
    def _get_provider(self, pr_url: str) -> BitbucketServerProvider:
        """获取或创建provider - 实现缓存机制"""
        if pr_url not in self._providers:
            self._providers[pr_url] = BitbucketServerProvider(
                pr_url=pr_url, 
                bitbucket_client=self.bitbucket_client
            )
        return self._providers[pr_url]
    
    def get_pr(self, pr_url: str) -> Dict:
        """简化的API - 隐藏provider复杂性"""
        provider = self._get_provider(pr_url)
        return provider.get_pr_data()
    
    def post_comment(self, pr_url: str, text: str) -> bool:
        """统一的错误处理"""
        try:
            provider = self._get_provider(pr_url)
            provider.publish_comment(text)
            return True
        except Exception as e:
            get_logger().error(f"Failed to post comment: {e}")
            return False
```

**关键设计决策**:
1. **适配器模式**: 封装BitbucketServerProvider的复杂性
2. **缓存机制**: 避免重复创建provider实例
3. **简化API**: 提供直观的方法名和参数
4. **统一错误处理**: 所有方法都有try-catch保护
5. **返回布尔值**: 简化调用方的错误处理逻辑

**为什么这样设计**:
- 现有的`BitbucketServerProvider`设计用于完整的PR操作
- Skill只需要部分功能，通过Client封装降低复杂度
- 缓存provider避免每次API调用都重新初始化

---

### 3. WebhookHandler (事件处理)

**位置**: `pr_agent/skills/bitbucket_review/webhook_handler.py`

**设计模式**: 策略模式 (Strategy Pattern)

**核心流程**:
```python
class WebhookHandler:
    def parse_event(self, payload: Dict) -> Tuple[str, str, Dict]:
        """解析webhook事件"""
        event_key = payload.get("eventKey", "")
        pr_data = payload.get("pullRequest", {})
        
        # 1. 提取PR信息
        pr_id = pr_data.get("id")
        repository = pr_data.get("fromRef", {}).get("repository", {})
        project = repository.get("project", {})
        
        # 2. 构建PR URL
        pr_url = f"{server_url}/projects/{project_key}/repos/{repo_slug}/pull-requests/{pr_id}"
        
        # 3. 识别事件类型
        if "pr:opened" in event_key:
            event_type = "opened"
        elif "pr:modified" in event_key:
            event_type = "updated"
        # ...
        
        return event_type, pr_url, pr_data
    
    def should_process(self, pr_data, ignore_repositories, ignore_pr_authors, ignore_pr_title):
        """过滤逻辑 - 策略模式"""
        # 提取信息
        repo_full_name = f"{project_key}/{repo_slug}"
        author_name = pr_data.get("author", {}).get("user", {}).get("name", "")
        pr_title = pr_data.get("title", "")
        
        # 应用过滤规则
        for regex in ignore_repositories:
            if re.search(regex, repo_full_name):
                return False  # 忽略此PR
        
        for regex in ignore_pr_authors:
            if re.search(regex, author_name):
                return False
        
        for regex in ignore_pr_title:
            if re.search(regex, pr_title):
                return False
        
        return True  # 应该处理
    
    def extract_commands(self, event_type, is_new_pr, pr_data, default_commands):
        """命令提取 - 支持评论触发"""
        commands = []
        
        if event_type == "commented":
            comment_text = pr_data.get("comment", {}).get("text", "")
            # 查找 /review, /describe 等命令
            pattern = r"/(review|describe|improve|ask)"
            matches = re.findall(pattern, comment_text, re.IGNORECASE)
            if matches:
                commands = matches
        
        if not commands:
            commands = default_commands  # 使用默认命令
        
        return commands
```

**关键设计决策**:
1. **事件解析**: 统一处理不同的Bitbucket事件类型
2. **正则过滤**: 灵活的过滤规则支持多种场景
3. **命令提取**: 从PR评论中提取用户命令
4. **策略模式**: 过滤逻辑可独立测试和扩展

**签名验证**:
```python
def verify_signature(self, payload: str, signature: str) -> bool:
    """HMAC-SHA256签名验证"""
    if not self.secret:
        return True  # 无密钥则跳过验证
    
    expected_signature = hmac.new(
        self.secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)
```

---

### 4. ReviewRunner (审查执行器)

**位置**: `pr_agent/skills/bitbucket_review/review_runner.py`

**设计模式**: 命令模式 (Command Pattern)

**核心实现**:
```python
class ReviewRunner:
    def __init__(self, bitbucket_client: BitbucketServerClient):
        self.client = bitbucket_client
    
    async def run_command(self, pr_url: str, command: str, args: Optional[List[str]] = None):
        """统一的命令执行接口"""
        try:
            get_logger().info(f"Starting command '{command}' for PR: {pr_url}")
            
            # 1. 临时设置git provider
            original_git_provider = get_settings().get("CONFIG.GIT_PROVIDER")
            get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")
            
            try:
                # 2. 创建并运行PRAgent
                agent = PRAgent()
                await asyncio.to_thread(
                    agent.handle_request, pr_url, command, args or []
                )
                
                return {"status": "success", "pr_url": pr_url, "command": command}
            
            finally:
                # 3. 恢复原始配置
                if original_git_provider:
                    get_settings().set("CONFIG.GIT_PROVIDER", original_git_provider)
        
        except Exception as e:
            get_logger().error(f"Command failed: {e}", exc_info=True)
            return {"status": "error", "error": str(e)}
    
    async def run_multiple_commands(self, pr_url: str, commands: List[str]):
        """顺序执行多个命令"""
        results = []
        for command in commands:
            result = await self.run_command(pr_url, command)
            results.append(result)
        return results
```

**关键设计决策**:
1. **异步执行**: 使用`asyncio.to_thread`将同步的PRAgent调用转为异步
2. **配置隔离**: 临时修改配置，执行后恢复，不影响其他代码
3. **命令模式**: 统一的命令接口，易于扩展新命令
4. **错误处理**: 捕获异常并返回结构化错误信息

**为什么使用异步**:
```python
# Webhook请求立即返回，审查在后台执行
@app.post("/webhook")
async def webhook_endpoint(request: Request):
    payload = await request.json()
    
    # 异步处理，不阻塞webhook响应
    asyncio.create_task(
        self._execute_commands_background(pr_url, commands, args)
    )
    
    return {"status": "processing"}  # 立即返回
```

---

### 5. BitbucketReviewSkill (主入口)

**位置**: `pr_agent/skills/bitbucket_review/skill.py`

**设计模式**: 外观模式 (Facade Pattern)

**核心架构**:
```python
class BitbucketReviewSkill:
    def __init__(self, config: Optional[BitbucketReviewConfig] = None):
        # 1. 初始化配置
        self.config = config or BitbucketReviewConfig.from_settings()
        
        # 2. 初始化组件
        self.client = BitbucketServerClient(...)
        self.webhook_handler = WebhookHandler(...)
        self.review_runner = ReviewRunner(self.client)
        
        # 3. FastAPI应用
        self.app: Optional[FastAPI] = None
    
    # === 公共API ===
    
    async def review_pr(self, pr_url: str, commands=None, **kwargs):
        """手动触发PR审查"""
        return await self.review_runner.run_command(pr_url, commands[0])
    
    async def handle_webhook(self, payload: Dict, signature: str = ""):
        """处理webhook事件"""
        # 1. 验证签名
        if not self.webhook_handler.verify_signature(...):
            return {"status": "error", "message": "Invalid signature"}
        
        # 2. 解析事件
        event_type, pr_url, pr_data = self.webhook_handler.parse_event(payload)
        
        # 3. 检查过滤规则
        if not self.webhook_handler.should_process(...):
            return {"status": "skipped"}
        
        # 4. 提取命令
        commands = self.webhook_handler.extract_commands(...)
        
        # 5. 异步执行
        asyncio.create_task(
            self._execute_commands_background(pr_url, commands, args)
        )
        
        return {"status": "processing"}
    
    def start_webhook_server(self, blocking=True):
        """启动FastAPI webhook服务器"""
        self.app = FastAPI()
        
        @self.app.post("/webhook")
        async def webhook_endpoint(request: Request):
            payload = await request.json()
            signature = request.headers.get("X-Hub-Signature", "")
            return await self.handle_webhook(payload, signature)
        
        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "bitbucket": self.client.test_connection()}
        
        uvicorn.run(self.app, host=self.config.webhook_host, port=self.config.webhook_port)
```

**关键设计决策**:
1. **外观模式**: 统一对外接口，隐藏内部复杂性
2. **依赖注入**: 通过构造函数注入配置，便于测试
3. **FastAPI集成**: 提供现代化的webhook服务器
4. **健康检查**: `/health`端点用于监控

---

## 数据流

### Webhook触发流程

```
1. Bitbucket Server发送webhook
   POST /webhook
   {
     "eventKey": "pr:opened",
     "pullRequest": {...}
   }
           │
           ▼
2. FastAPI接收请求
   skill.app.post("/webhook")
           │
           ▼
3. Skill处理webhook
   skill.handle_webhook(payload, signature)
           │
           ├─> 验证签名 (WebhookHandler.verify_signature)
           ├─> 解析事件 (WebhookHandler.parse_event)
           ├─> 过滤规则 (WebhookHandler.should_process)
           └─> 提取命令 (WebhookHandler.extract_commands)
           │
           ▼
4. 异步执行审查
   asyncio.create_task(...)
           │
           ▼
5. ReviewRunner执行命令
   runner.run_command(pr_url, "review")
           │
           ├─> 设置git provider
           ├─> 创建PRAgent
           └─> agent.handle_request("review")
           │
           ▼
6. PRAgent调用审查逻辑
   PRReviewer.run()
           │
           ├─> 获取PR数据 (via BitbucketServerClient)
           ├─> AI分析代码
           └─> 发布评论 (via BitbucketServerClient)
           │
           ▼
7. 返回到Bitbucket Server
   PR中出现AI审查评论
```

### 手动触发流程

```
1. 用户执行命令
   python -m pr_agent.skills.bitbucket_review.skill review --pr-url <url>
           │
           ▼
2. CLI入口
   skill.py::main()
           │
           ▼
3. 创建Skill实例
   skill = BitbucketReviewSkill()
           │
           ▼
4. 调用review_pr
   asyncio.run(skill.review_pr(pr_url))
           │
           ▼
5. 执行审查（同上面5-7步）
```

---

## 关键技术

### 1. 异步编程

**为什么使用异步**:
- Webhook需要快速响应，不能阻塞
- PR审查可能需要几十秒，不能让Bitbucket等待
- 支持并发处理多个PR

**实现方式**:
```python
# 异步包装同步代码
await asyncio.to_thread(agent.handle_request, pr_url, command)

# 后台任务
asyncio.create_task(self._execute_commands_background(...))
```

### 2. 配置隔离

**问题**: 现有系统通过全局配置管理git provider

**解决方案**:
```python
# 临时修改配置
original = get_settings().get("CONFIG.GIT_PROVIDER")
get_settings().set("CONFIG.GIT_PROVIDER", "bitbucket_server")

try:
    # 执行操作
    agent.handle_request(...)
finally:
    # 恢复配置
    if original:
        get_settings().set("CONFIG.GIT_PROVIDER", original)
```

### 3. 缓存机制

**问题**: 每次API调用都创建新provider效率低

**解决方案**:
```python
class BitbucketServerClient:
    def __init__(self):
        self._providers: Dict[str, BitbucketServerProvider] = {}
    
    def _get_provider(self, pr_url: str):
        if pr_url not in self._providers:
            self._providers[pr_url] = BitbucketServerProvider(pr_url, ...)
        return self._providers[pr_url]
```

### 4. 错误处理

**统一的错误处理模式**:
```python
try:
    # 执行操作
    result = operation()
    return {"status": "success", "data": result}
except Exception as e:
    get_logger().error(f"Operation failed: {e}", exc_info=True)
    return {"status": "error", "error": str(e)}
```

---

## 与现有系统的集成

### 1. 复用BitbucketServerProvider

**集成方式**:
```python
# 不是重新实现，而是封装
self.bitbucket_client = Bitbucket(url, token)
provider = BitbucketServerProvider(pr_url, bitbucket_client=self.bitbucket_client)
```

**优点**:
- 不重复代码
- 保持一致性
- 继承所有现有功能

### 2. 复用PRAgent

**集成方式**:
```python
agent = PRAgent()
agent.handle_request(pr_url, "review", args)
```

**关键点**:
- 通过配置切换git provider
- 使用异步包装同步调用
- 在finally块中恢复配置

### 3. 复用效率监控

**自动集成**:
- ReviewRunner调用PRAgent
- PRAgent内部已集成EfficiencyTracker
- 审查数据自动记录到SQLite

---

## 总结

### 设计原则

1. **单一职责**: 每个组件只负责一件事
2. **开闭原则**: 易于扩展新功能，无需修改现有代码
3. **依赖倒置**: 依赖抽象而非具体实现
4. **复用优先**: 最大化复用现有代码

### 技术亮点

1. **模块化设计**: 组件间松耦合
2. **异步处理**: 提高并发性能
3. **适配器模式**: 简化API使用
4. **配置驱动**: 行为可通过配置调整
5. **完整测试**: 15个单元测试覆盖核心逻辑

### 扩展性

- 新增命令: 在ReviewRunner中添加方法
- 新增过滤规则: 在WebhookHandler中扩展
- 新增Git平台: 创建类似的skill结构
- 新增webhook事件: 在parse_event中添加case

---

**完成时间**: 5-8小时（符合计划预估）
**代码行数**: ~1700行
**测试覆盖**: 15个单元测试
**文档**: 3个详细文档
