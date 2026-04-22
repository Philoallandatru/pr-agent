# PR-Agent 快速参考指南

## 目录
- [常用命令](#常用命令)
- [API 端点](#api-端点)
- [配置参数](#配置参数)
- [故障排查](#故障排查)
- [最佳实践](#最佳实践)

## 常用命令

### Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 停止所有服务
docker-compose down

# 查看日志
docker-compose logs -f [service]

# 重启服务
docker-compose restart [service]

# 查看服务状态
docker-compose ps

# 进入容器
docker-compose exec [service] bash

# 重新构建
docker-compose build [service]
```

### Kubernetes

```bash
# 查看 Pod 状态
kubectl get pods -n pr-agent

# 查看日志
kubectl logs -f <pod-name> -n pr-agent

# 进入容器
kubectl exec -it <pod-name> -n pr-agent -- bash

# 查看服务
kubectl get svc -n pr-agent

# 查看配置
kubectl get configmap -n pr-agent
kubectl get secret -n pr-agent

# 应用配置
kubectl apply -k k8s/overlays/production

# 回滚部署
kubectl rollout undo deployment/pr-agent-backend -n pr-agent

# 扩容
kubectl scale deployment/pr-agent-backend --replicas=3 -n pr-agent
```

### 数据库管理

```bash
# 运行迁移
python -m pr_agent.storage.migration upgrade

# 回滚迁移
python -m pr_agent.storage.migration downgrade

# 查看迁移状态
python -m pr_agent.storage.migration current

# 创建新迁移
python -m pr_agent.storage.migration create "description"

# 备份数据库
pg_dump pr_agent > backup.sql

# 恢复数据库
psql pr_agent < backup.sql
```

### 应用管理

```bash
# 创建管理员用户
python -m pr_agent.cli.create_admin

# 启动 Web 服务
python -m pr_agent.servers.web_platform

# 启动轮询服务
python -m pr_agent.servers.bitbucket_server_polling

# 运行测试
pytest tests/

# 运行特定测试
pytest tests/unittest/test_specific.py

# 生成覆盖率报告
pytest --cov=pr_agent tests/
```

## API 端点

### 认证 API

```bash
# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# 刷新 Token
curl -X POST http://localhost:8000/api/auth/refresh \
  -H "Authorization: Bearer <token>"

# 登出
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer <token>"
```

### 仓库管理 API

```bash
# 列出仓库
curl -X GET http://localhost:8000/api/repositories \
  -H "Authorization: Bearer <token>"

# 添加仓库
curl -X POST http://localhost:8000/api/repositories \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-repo",
    "url": "https://bitbucket.example.com/projects/PRJ/repos/my-repo",
    "enabled": true
  }'

# 删除仓库
curl -X DELETE http://localhost:8000/api/repositories/{id} \
  -H "Authorization: Bearer <token>"
```

### 代码审查 API

```bash
# 触发审查
curl -X POST http://localhost:8000/api/reviews \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "pr_id": "123",
    "repository": "my-repo",
    "mode": "comprehensive"
  }'

# 获取审查结果
curl -X GET http://localhost:8000/api/reviews/{id} \
  -H "Authorization: Bearer <token>"

# 列出审查
curl -X GET "http://localhost:8000/api/reviews?repository=my-repo&status=completed" \
  -H "Authorization: Bearer <token>"
```

### 规则管理 API

```bash
# 列出规则
curl -X GET http://localhost:8000/api/rules \
  -H "Authorization: Bearer <token>"

# 创建规则
curl -X POST http://localhost:8000/api/rules \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_id": "custom-rule-1",
    "name": "Custom Rule",
    "description": "Check for specific pattern",
    "severity": "warning",
    "category": "style",
    "pattern": "TODO:",
    "message": "TODO comments should be resolved",
    "file_patterns": ["**/*.py"],
    "enabled": true
  }'

# 执行规则检查
curl -X POST http://localhost:8000/api/rules/check \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "src/main.py",
    "content": "# TODO: implement this"
  }'
```

### 报告生成 API

```bash
# 生成报告
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "report_type": "quality_trends",
    "start_date": "2024-01-01",
    "end_date": "2024-04-01",
    "format": "html"
  }'

# 下载报告
curl -X GET http://localhost:8000/api/reports/{id}/download \
  -H "Authorization: Bearer <token>" \
  -o report.html
```

### 健康检查 API

```bash
# 综合健康检查
curl http://localhost:8000/api/health

# 就绪检查
curl http://localhost:8000/api/health/ready

# 存活检查
curl http://localhost:8000/api/health/live

# Prometheus 指标
curl http://localhost:8000/metrics
```

## 配置参数

### 核心配置

```toml
[config]
git_provider = "bitbucket_server"  # Git 提供商
log_level = "INFO"                 # 日志级别: DEBUG, INFO, WARNING, ERROR

[bitbucket_server]
url = "https://bitbucket.example.com"  # Bitbucket 服务器地址
username = "your-username"              # 用户名
password = "your-password"              # 密码或访问令牌
verify_ssl = true                       # 是否验证 SSL 证书
timeout = 30                            # 请求超时时间（秒）
```

### 轮询配置

```toml
[bitbucket_server_polling]
enabled = true                          # 是否启用轮询
poll_interval = 300                     # 轮询间隔（秒）
repositories = [                        # 监控的仓库列表
    "project/repo1",
    "project/repo2"
]
max_workers = 5                         # 最大并发 worker 数
state_file = ".pr_agent/polling_state.json"  # 状态文件路径
```

### Web 平台配置

```toml
[web_platform]
host = "0.0.0.0"                       # 监听地址
port = 8000                            # 监听端口
cors_origins = [                       # CORS 允许的源
    "http://localhost:3000",
    "https://pr-agent.example.com"
]
workers = 4                            # Worker 进程数
```

### 安全配置

```toml
[security]
secret_key = "your-secret-key-here"    # 应用密钥（必须修改）
jwt_algorithm = "HS256"                # JWT 算法
access_token_expire_minutes = 30       # 访问令牌过期时间
refresh_token_expire_days = 7          # 刷新令牌过期时间
```

### 数据库配置

```toml
[database]
url = "postgresql://user:pass@localhost/pr_agent"  # 数据库连接字符串
pool_size = 10                         # 连接池大小
max_overflow = 20                      # 最大溢出连接数
pool_timeout = 30                      # 连接超时时间
```

### 缓存配置

```toml
[redis]
host = "localhost"                     # Redis 主机
port = 6379                            # Redis 端口
db = 0                                 # 数据库编号
password = ""                          # 密码（如有）
max_connections = 50                   # 最大连接数

[cache]
enabled = true                         # 是否启用缓存
default_ttl = 3600                     # 默认 TTL（秒）
strategy = "lru"                       # 缓存策略: lru, lfu, fifo, ttl
max_size = 1000                        # 最大缓存条目数
```

### 性能配置

```toml
[performance]
batch_size = 100                       # 批处理大小
async_workers = 10                     # 异步 worker 数
query_timeout = 30                     # 查询超时时间
enable_profiling = false               # 是否启用性能分析
```

### 监控配置

```toml
[monitoring]
enabled = true                         # 是否启用监控
metrics_port = 9090                    # Prometheus 指标端口
log_format = "json"                    # 日志格式: json, text
log_file = "logs/pr-agent.log"        # 日志文件路径
```

## 故障排查

### 常见问题

#### 1. 无法连接到 Bitbucket

**症状**: 轮询服务报错 "Connection refused" 或 "Timeout"

**检查步骤**:
```bash
# 1. 测试网络连接
curl -v https://bitbucket.example.com

# 2. 检查配置
cat pr_agent/settings/configuration.toml | grep -A 5 bitbucket_server

# 3. 验证凭据
curl -u username:password https://bitbucket.example.com/rest/api/1.0/projects

# 4. 查看日志
docker-compose logs bitbucket-polling
```

**解决方案**:
- 确认 Bitbucket URL 正确
- 验证用户名和密码
- 检查网络防火墙规则
- 确认 SSL 证书有效

#### 2. 数据库连接失败

**症状**: 应用启动失败，报错 "could not connect to server"

**检查步骤**:
```bash
# 1. 检查数据库服务
docker-compose ps postgres
# 或
systemctl status postgresql

# 2. 测试连接
psql -h localhost -U pr_agent -d pr_agent

# 3. 检查连接字符串
echo $DATABASE_URL

# 4. 查看数据库日志
docker-compose logs postgres
```

**解决方案**:
- 确认数据库服务运行
- 验证连接字符串格式
- 检查用户权限
- 确认网络可达

#### 3. Redis 连接问题

**症状**: 缓存功能不工作，日志显示 Redis 错误

**检查步骤**:
```bash
# 1. 检查 Redis 服务
docker-compose ps redis
# 或
systemctl status redis

# 2. 测试连接
redis-cli ping

# 3. 检查配置
cat pr_agent/settings/configuration.toml | grep -A 5 redis

# 4. 查看 Redis 日志
docker-compose logs redis
```

**解决方案**:
- 确认 Redis 服务运行
- 验证连接参数
- 检查密码配置
- 清除缓存重试

#### 4. 审查任务失败

**症状**: 审查任务状态为 "failed"

**检查步骤**:
```bash
# 1. 查看审查日志
curl -X GET http://localhost:8000/api/reviews/{id}/logs \
  -H "Authorization: Bearer <token>"

# 2. 检查系统日志
docker-compose logs backend

# 3. 验证规则配置
curl -X GET http://localhost:8000/api/rules \
  -H "Authorization: Bearer <token>"

# 4. 测试单个规则
curl -X POST http://localhost:8000/api/rules/check \
  -H "Authorization: Bearer <token>" \
  -d '{"file_path": "test.py", "content": "print(\"test\")"}'
```

**解决方案**:
- 检查规则配置是否正确
- 验证文件路径和内容
- 查看详细错误信息
- 禁用有问题的规则

#### 5. 性能问题

**症状**: 响应缓慢，超时

**检查步骤**:
```bash
# 1. 查看资源使用
docker stats

# 2. 检查慢查询
# 在 PostgreSQL 中
SELECT * FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

# 3. 查看缓存命中率
curl http://localhost:8000/metrics | grep cache_hit_rate

# 4. 分析性能指标
curl http://localhost:8000/api/performance/stats \
  -H "Authorization: Bearer <token>"
```

**解决方案**:
- 增加 worker 数量
- 优化数据库查询
- 启用缓存
- 增加资源配置

### 日志位置

```bash
# Docker Compose
docker-compose logs [service]

# Kubernetes
kubectl logs <pod-name> -n pr-agent

# 本地部署
tail -f logs/pr-agent.log
tail -f logs/audit.log
tail -f logs/access.log
```

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG

# 或在配置文件中
[config]
log_level = "DEBUG"

# 重启服务
docker-compose restart backend
```

## 最佳实践

### 1. 安全

- ✅ 使用强随机密钥
- ✅ 启用 HTTPS
- ✅ 定期更新依赖
- ✅ 限制 API 访问
- ✅ 启用审计日志
- ✅ 定期备份数据

### 2. 性能

- ✅ 启用 Redis 缓存
- ✅ 配置合理的 TTL
- ✅ 使用连接池
- ✅ 启用批处理
- ✅ 监控慢查询
- ✅ 定期清理数据

### 3. 可靠性

- ✅ 配置健康检查
- ✅ 设置资源限制
- ✅ 启用自动重启
- ✅ 配置告警规则
- ✅ 定期测试恢复
- ✅ 保持文档更新

### 4. 运维

- ✅ 使用版本控制
- ✅ 自动化部署
- ✅ 监控关键指标
- ✅ 定期审查日志
- ✅ 保持系统更新
- ✅ 文档化流程

### 5. 开发

- ✅ 遵循代码规范
- ✅ 编写单元测试
- ✅ 代码审查
- ✅ 持续集成
- ✅ 版本管理
- ✅ 文档同步

## 快速链接

- **项目主页**: https://github.com/Philoallandatru/pr-agent
- **文档**: https://github.com/Philoallandatru/pr-agent/tree/auto-review/docs
- **问题反馈**: https://github.com/Philoallandatru/pr-agent/issues
- **API 文档**: http://localhost:8000/docs
- **监控面板**: http://localhost:3000/grafana

## 获取帮助

如果遇到问题:

1. 查看本文档的故障排查部分
2. 搜索 GitHub Issues
3. 查看详细文档
4. 提交新 Issue

---

**版本**: 1.0.0  
**最后更新**: 2024-04
