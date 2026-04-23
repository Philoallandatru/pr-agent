# Backend End-to-End Integration Testing

完整的后端端到端集成测试系统，验证整个代码审查平台的工作流程。

## 测试架构

### 测试层次

```
┌─────────────────────────────────────┐
│   E2E Integration Tests             │
├─────────────────────────────────────┤
│ - Complete Workflows                │
│ - API Integration                   │
│ - Database Integration              │
│ - External Services                 │
│ - Performance & Load                │
│ - Security                          │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Test Infrastructure               │
├─────────────────────────────────────┤
│ - Test Client (FastAPI)             │
│ - Test Database (SQLite)            │
│ - Mock Services                     │
│ - Test Data Generators              │
└─────────────────────────────────────┘
         ↓
┌─────────────────────────────────────┐
│   Application Under Test            │
├─────────────────────────────────────┤
│ - Web Platform API                  │
│ - Business Logic                    │
│ - Data Storage                      │
│ - External Integrations             │
└─────────────────────────────────────┘
```

## 测试套件

### 1. 工作流测试 (test_workflows.py)

测试完整的业务流程：

**完整审查生命周期:**
```python
async def test_full_review_lifecycle(test_client, auth_headers):
    # 1. 注册仓库
    repo_response = await test_client.post(
        "/api/repositories",
        json={"name": "test-repo", "url": "https://github.com/test/repo.git"},
        headers=auth_headers
    )
    
    # 2. 创建 PR
    pr_response = await test_client.post(
        "/api/reviews",
        json={"repository": "test-repo", "pr_number": 123},
        headers=auth_headers
    )
    
    # 3. 分配审查者
    # 4. 添加评论
    # 5. 完成审查
    # 6. 验证最终状态
```

**自动化审查触发:**
- PR 创建自动触发审查
- 验证审查状态
- 检查通知发送

**AI 助手集成:**
- 代码解释
- 审查建议
- 评论优化

**调度工作流:**
- 定期审查调度
- 事件触发审查
- 任务优先级管理

**报告生成:**
- 生成多种格式报告
- 导出报告
- 报告数据验证

**协作工作流:**
- 多审查者协作
- 评论线程
- 决策投票

**知识库集成:**
- 搜索知识条目
- 应用最佳实践
- 相关条目推荐

### 2. 性能测试 (test_performance.py)

测试系统性能指标：

**API 响应时间:**
```python
async def test_api_response_time(test_client, auth_headers):
    start_time = time.time()
    response = await test_client.get("/api/reviews", headers=auth_headers)
    elapsed_time = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed_time < 1.0  # 所有 API 端点响应时间 < 1 秒
```

**数据库查询性能:**
- 大数据集查询优化
- 索引效果验证
- 查询时间限制

**并发处理:**
- 并发审查创建
- 并发用户会话
- 资源竞争处理

**大文件处理:**
- 1000+ 行代码分析
- 大型 PR 处理
- 内存使用监控

### 3. 负载测试 (test_performance.py)

测试系统负载能力：

**持续负载:**
```python
async def test_sustained_load(test_client, auth_headers):
    # 50 个请求，成功率 >= 95%
    # 吞吐量 >= 10 req/s
    tasks = []
    for i in range(50):
        task = test_client.get(f"/api/reviews/{i}", headers=auth_headers)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    success_count = sum(1 for r in results if not isinstance(r, Exception))
    
    assert success_count >= 47  # 95% 成功率
```

**突发流量:**
- 20 个并发请求
- 75% 成功率
- 响应时间稳定

**内存使用:**
- 创建 20 个审查
- 多次查询
- 内存不增长

**可扩展性:**
- 50 个仓库处理
- 分页性能
- 5 个并发用户

**缓存性能:**
- 缓存命中加速
- 缓存失效验证
- 缓存一致性

### 4. 安全测试 (test_security.py)

测试安全特性：

**认证测试:**
```python
async def test_unauthenticated_access_denied(test_client):
    # 未认证请求返回 401
    response = await test_client.get("/api/reviews")
    assert response.status_code == 401
```

**授权测试:**
- 角色权限验证
- 数据访问控制
- 管理员端点保护

**输入验证:**
- SQL 注入防护
- XSS 防护
- 路径遍历防护
- 命令注入防护

**数据保护:**
- 敏感数据不记录日志
- API 密钥不暴露
- 密码不返回响应

**速率限制:**
- 限流执行
- 限流头部
- 429 状态码

**审计日志:**
- 敏感操作记录
- 失败登录记录
- 审计追踪

## 快速开始

### 安装依赖

```bash
pip install pytest pytest-asyncio pytest-cov pytest-xdist httpx
```

### 运行所有测试

```bash
pytest tests/e2e/ -v
```

### 运行特定测试套件

```bash
# 工作流测试
pytest tests/e2e/test_workflows.py -v

# 性能测试
pytest tests/e2e/test_performance.py -v

# 安全测试
pytest tests/e2e/test_security.py -v
```

### 并行执行

```bash
pytest tests/e2e/ -n auto
```

### 生成覆盖率报告

```bash
pytest tests/e2e/ --cov=pr_agent --cov-report=html
```

## 测试配置

### 环境变量

```bash
export TESTING=true
export DATABASE_URL=sqlite:///test.db
export REDIS_URL=redis://localhost:6379
export LOG_LEVEL=INFO
```

### pytest.ini

```ini
[pytest]
testpaths = tests/e2e
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    slow: marks tests as slow
    integration: marks tests as integration tests
    security: marks tests as security tests
```

## Fixtures

### 基础 Fixtures

```python
@pytest.fixture
async def test_client() -> AsyncClient:
    """FastAPI 测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """认证头部"""
    token = create_test_token()
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def test_database() -> Database:
    """测试数据库"""
    db = Database("test.db")
    db.init()
    yield db
    db.close()
    os.remove("test.db")

@pytest.fixture
def test_data_dir(tmp_path) -> Path:
    """测试数据目录"""
    return tmp_path
```

### 数据 Fixtures

```python
@pytest.fixture
def sample_repository() -> Dict:
    """示例仓库数据"""
    return {
        "name": "test-repo",
        "url": "https://github.com/test/repo.git",
        "branch": "main"
    }

@pytest.fixture
def sample_pr_data() -> Dict:
    """示例 PR 数据"""
    return {
        "repository": "test-repo",
        "pr_number": 123,
        "title": "Test PR",
        "author": "test-user"
    }

@pytest.fixture
def sample_code() -> str:
    """示例代码"""
    return """
def calculate_sum(a, b):
    return a + b
"""

@pytest.fixture
def test_data_generator() -> TestDataGenerator:
    """测试数据生成器"""
    return TestDataGenerator()
```

## 测试数据生成

### TestDataGenerator

```python
generator = TestDataGenerator()

# 生成仓库
repos = generator.generate_repositories(count=5)

# 生成 PR
prs = generator.generate_pull_requests("repo-1", count=10)

# 生成审查
reviews = generator.generate_reviews("pr-123", count=3)
```

## CI/CD 集成

### GitHub Actions

工作流文件: `.github/workflows/e2e-tests.yml`

**触发条件:**
- Push 到 main/auto-review 分支
- Pull Request
- 每日定时运行 (2 AM UTC)

**测试矩阵:**
- Python 3.9, 3.10, 3.11
- Redis 服务
- 并行执行

**输出:**
- 测试结果 (JUnit XML)
- 覆盖率报告 (XML/HTML)
- 性能报告 (JSON)
- 安全报告 (JSON)

### 运行 CI 测试

```bash
# 本地模拟 CI 环境
docker-compose -f docker-compose.test.yml up -d
pytest tests/e2e/ -v --cov=pr_agent
docker-compose -f docker-compose.test.yml down
```

## 性能基准

### 响应时间目标

| 端点类型 | 目标时间 | 最大时间 |
|---------|---------|---------|
| 简单查询 | < 100ms | < 500ms |
| 复杂查询 | < 500ms | < 1s |
| 数据创建 | < 200ms | < 1s |
| 报告生成 | < 2s | < 5s |
| AI 分析 | < 3s | < 10s |

### 吞吐量目标

- 简单请求: >= 100 req/s
- 复杂请求: >= 10 req/s
- 并发用户: >= 50 users

### 资源使用目标

- 内存: < 512MB (空闲)
- 内存: < 2GB (负载)
- CPU: < 50% (平均)

## 安全检查清单

- [ ] 所有端点需要认证
- [ ] 角色权限正确实施
- [ ] 输入验证和清理
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] CSRF 防护
- [ ] 速率限制
- [ ] 审计日志
- [ ] 敏感数据保护
- [ ] HTTPS 强制
- [ ] 安全头部设置

## 故障排查

### 常见问题

**1. 测试数据库锁定**
```bash
# 清理测试数据库
rm -f test.db test.db-*
```

**2. 端口冲突**
```bash
# 检查端口占用
lsof -i :8000
# 杀死进程
kill -9 <PID>
```

**3. Redis 连接失败**
```bash
# 启动 Redis
redis-server
# 或使用 Docker
docker run -d -p 6379:6379 redis:7-alpine
```

**4. 测试超时**
```bash
# 增加超时时间
pytest tests/e2e/ --timeout=300
```

## 最佳实践

### 1. 测试隔离

每个测试应该独立运行，不依赖其他测试：

```python
@pytest.fixture(scope="function")
async def clean_database():
    """每个测试前清理数据库"""
    await db.clear()
    yield
    await db.clear()
```

### 2. 使用 Mock

对外部服务使用 Mock：

```python
@pytest.fixture
def mock_github_api(monkeypatch):
    """Mock GitHub API"""
    async def mock_get(*args, **kwargs):
        return MockResponse({"status": "ok"})
    
    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)
```

### 3. 参数化测试

减少重复代码：

```python
@pytest.mark.parametrize("endpoint,method", [
    ("/api/reviews", "GET"),
    ("/api/repositories", "GET"),
    ("/api/metrics", "GET"),
])
async def test_endpoints(test_client, auth_headers, endpoint, method):
    response = await test_client.request(method, endpoint, headers=auth_headers)
    assert response.status_code == 200
```

### 4. 清晰的断言

使用描述性断言消息：

```python
assert response.status_code == 200, \
    f"Expected 200, got {response.status_code}: {response.text}"
```

### 5. 测试数据清理

确保测试后清理：

```python
@pytest.fixture
async def temp_file(tmp_path):
    file_path = tmp_path / "test_file.txt"
    yield file_path
    if file_path.exists():
        file_path.unlink()
```

## 监控和报告

### 测试指标

- 总测试数
- 通过率
- 失败率
- 跳过率
- 平均执行时间
- 覆盖率

### 生成报告

```bash
# HTML 报告
pytest tests/e2e/ --html=report.html --self-contained-html

# JUnit XML
pytest tests/e2e/ --junitxml=junit.xml

# 覆盖率报告
pytest tests/e2e/ --cov=pr_agent --cov-report=html
```

## 相关文档

- [System Integration Testing](INTEGRATION_TESTING.md)
- [Performance Testing](PERFORMANCE_TESTING.md)
- [Security Testing](../SECURITY.md)
- [Frontend E2E Testing](E2E_TESTING.md)
- [CI/CD Pipeline](../../.github/workflows/README.md)
