# PR-Agent 生产部署检查清单

## 部署前准备

### 1. 环境准备 ✓

#### 硬件要求
- [ ] CPU: 4 核心以上
- [ ] 内存: 8GB 以上
- [ ] 磁盘: 100GB 以上 SSD
- [ ] 网络: 稳定的互联网连接

#### 软件要求
- [ ] Docker 20.10+
- [ ] Docker Compose 2.0+
- [ ] Kubernetes 1.24+ (如使用 K8s)
- [ ] PostgreSQL 13+ (生产环境)
- [ ] Redis 6.0+
- [ ] Python 3.12+
- [ ] Node.js 18+

### 2. 配置文件准备 ✓

#### 必需配置
- [ ] 复制 `.env.example` 到 `.env`
- [ ] 设置 `SECRET_KEY` (强随机字符串)
- [ ] 设置 `JWT_SECRET` (强随机字符串)
- [ ] 配置 `DATABASE_URL`
- [ ] 配置 `REDIS_URL`
- [ ] 设置 Bitbucket 凭据

#### 可选配置
- [ ] AI 模型 API 密钥 (OpenAI/Anthropic)
- [ ] Webhook 通知配置 (Slack/钉钉)
- [ ] SMTP 邮件配置
- [ ] 监控配置 (Prometheus/Grafana)

### 3. 安全配置 ✓

#### 密钥管理
- [ ] 生成强随机密钥
- [ ] 使用密钥管理服务 (AWS Secrets Manager/Vault)
- [ ] 不在代码中硬编码密钥
- [ ] 定期轮换密钥

#### 网络安全
- [ ] 配置防火墙规则
- [ ] 启用 HTTPS/TLS
- [ ] 配置 CORS 白名单
- [ ] 设置 rate limiting
- [ ] 实施 IP 白名单 (可选)

#### 认证授权
- [ ] 创建管理员账户
- [ ] 配置 RBAC 角色
- [ ] 设置密码策略
- [ ] 启用审计日志

### 4. 数据库准备 ✓

#### PostgreSQL 设置
- [ ] 创建数据库: `CREATE DATABASE pr_agent;`
- [ ] 创建用户: `CREATE USER pr_agent WITH PASSWORD 'xxx';`
- [ ] 授予权限: `GRANT ALL PRIVILEGES ON DATABASE pr_agent TO pr_agent;`
- [ ] 配置连接池
- [ ] 启用 SSL 连接

#### 数据库迁移
- [ ] 运行迁移: `python -m pr_agent.storage.migration upgrade`
- [ ] 验证表结构
- [ ] 创建初始数据
- [ ] 备份空数据库

#### Redis 设置
- [ ] 配置持久化 (AOF/RDB)
- [ ] 设置最大内存
- [ ] 配置驱逐策略
- [ ] 启用密码认证

## 部署步骤

### 方式 1: Docker Compose 部署 (推荐用于开发/测试)

#### 步骤 1: 准备配置
```bash
# 克隆仓库
git clone https://github.com/Philoallandatru/pr-agent.git
cd pr-agent
git checkout auto-review

# 配置环境变量
cp .env.example .env
nano .env  # 编辑配置
```

- [ ] 完成配置文件编辑

#### 步骤 2: 构建镜像
```bash
# 构建所有服务
docker-compose build

# 验证镜像
docker images | grep pr-agent
```

- [ ] 镜像构建成功

#### 步骤 3: 启动服务
```bash
# 启动所有服务
docker-compose up -d

# 检查服务状态
docker-compose ps
docker-compose logs -f
```

- [ ] 所有服务运行正常

#### 步骤 4: 初始化数据
```bash
# 运行数据库迁移
docker-compose exec backend python -m pr_agent.storage.migration upgrade

# 创建管理员用户
docker-compose exec backend python -m pr_agent.cli.create_admin
```

- [ ] 数据库初始化完成
- [ ] 管理员账户创建成功

#### 步骤 5: 验证部署
- [ ] 访问 Web UI: http://localhost:3000
- [ ] 访问 API 文档: http://localhost:8000/docs
- [ ] 测试登录功能
- [ ] 测试基本功能

### 方式 2: Kubernetes 部署 (推荐用于生产)

#### 步骤 1: 准备 K8s 集群
- [ ] 集群已创建并可访问
- [ ] kubectl 已配置
- [ ] Helm 已安装 (可选)

#### 步骤 2: 创建命名空间
```bash
kubectl create namespace pr-agent
kubectl config set-context --current --namespace=pr-agent
```

- [ ] 命名空间创建成功

#### 步骤 3: 创建 Secrets
```bash
# 创建数据库密钥
kubectl create secret generic db-credentials \
  --from-literal=username=pr_agent \
  --from-literal=password=your-password

# 创建应用密钥
kubectl create secret generic app-secrets \
  --from-literal=secret-key=your-secret-key \
  --from-literal=jwt-secret=your-jwt-secret

# 创建 Bitbucket 凭据
kubectl create secret generic bitbucket-credentials \
  --from-literal=username=your-username \
  --from-literal=password=your-password
```

- [ ] 所有 Secrets 创建成功

#### 步骤 4: 创建 ConfigMap
```bash
kubectl create configmap pr-agent-config \
  --from-file=pr_agent/settings/configuration.toml
```

- [ ] ConfigMap 创建成功

#### 步骤 5: 部署应用
```bash
# 应用生产环境配置
kubectl apply -k k8s/overlays/production

# 检查部署状态
kubectl get pods
kubectl get svc
kubectl get ingress
```

- [ ] 所有 Pod 运行正常
- [ ] Service 创建成功
- [ ] Ingress 配置正确

#### 步骤 6: 配置 Ingress
```bash
# 如使用 cert-manager 自动 HTTPS
kubectl apply -f k8s/base/certificate.yaml
```

- [ ] Ingress 可访问
- [ ] HTTPS 证书有效

#### 步骤 7: 配置监控
```bash
# 部署 Prometheus
kubectl apply -f monitoring/prometheus/

# 部署 Grafana
kubectl apply -f monitoring/grafana/
```

- [ ] Prometheus 运行正常
- [ ] Grafana 可访问
- [ ] 仪表板配置完成

### 方式 3: 手动部署

#### 步骤 1: 安装依赖
```bash
# 后端依赖
pip install -r requirements.txt

# 前端依赖
cd frontend
npm install
npm run build
cd ..
```

- [ ] 依赖安装成功

#### 步骤 2: 配置应用
```bash
# 复制配置文件
cp pr_agent/settings/configuration.toml.example \
   pr_agent/settings/configuration.toml

# 编辑配置
nano pr_agent/settings/configuration.toml
```

- [ ] 配置文件编辑完成

#### 步骤 3: 初始化数据库
```bash
python -m pr_agent.storage.migration upgrade
```

- [ ] 数据库迁移成功

#### 步骤 4: 启动服务
```bash
# 启动后端 (使用 systemd)
sudo systemctl start pr-agent-web
sudo systemctl start pr-agent-polling

# 或使用 supervisor
supervisorctl start pr-agent:*

# 配置 Nginx 反向代理
sudo cp deployment/nginx/pr-agent.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/pr-agent.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

- [ ] 后端服务运行正常
- [ ] Nginx 配置正确
- [ ] 前端可访问

## 部署后验证

### 1. 功能测试 ✓

#### 基础功能
- [ ] 用户登录/登出
- [ ] 仓库添加/删除
- [ ] PR 列表显示
- [ ] 代码审查触发
- [ ] 审查结果查看

#### 高级功能
- [ ] 规则引擎工作正常
- [ ] 自动分配功能
- [ ] 通知发送成功
- [ ] 报告生成正常
- [ ] 仪表板数据正确

### 2. 性能测试 ✓

#### 响应时间
- [ ] API 响应 < 200ms (P95)
- [ ] 页面加载 < 2s
- [ ] 审查完成 < 30s

#### 并发测试
- [ ] 10 并发用户正常
- [ ] 50 并发用户正常
- [ ] 100 并发用户正常 (可选)

#### 资源使用
- [ ] CPU 使用 < 70%
- [ ] 内存使用 < 80%
- [ ] 磁盘 I/O 正常
- [ ] 网络带宽充足

### 3. 安全测试 ✓

#### 认证授权
- [ ] 未授权访问被拒绝
- [ ] Token 过期正常处理
- [ ] 权限控制生效
- [ ] API Key 验证正常

#### 数据安全
- [ ] 敏感数据加密
- [ ] SQL 注入防护
- [ ] XSS 防护
- [ ] CSRF 防护

### 4. 监控验证 ✓

#### 日志
- [ ] 应用日志正常输出
- [ ] 审计日志记录完整
- [ ] 错误日志可查询
- [ ] 日志轮转配置

#### 指标
- [ ] Prometheus 采集正常
- [ ] Grafana 仪表板显示
- [ ] 告警规则配置
- [ ] 告警通知测试

#### 健康检查
- [ ] /api/health 返回 200
- [ ] /api/health/ready 正常
- [ ] /api/health/live 正常
- [ ] K8s 探针工作正常

## 备份和恢复

### 1. 备份策略 ✓

#### 数据库备份
```bash
# 每日全量备份
pg_dump pr_agent > backup_$(date +%Y%m%d).sql

# 配置自动备份
0 2 * * * /usr/local/bin/backup-database.sh
```

- [ ] 备份脚本配置
- [ ] 备份存储位置
- [ ] 备份保留策略 (30 天)

#### 配置备份
```bash
# 备份配置文件
tar -czf config_backup_$(date +%Y%m%d).tar.gz \
  pr_agent/settings/ \
  .env \
  k8s/
```

- [ ] 配置备份自动化

#### 代码备份
- [ ] Git 仓库已推送
- [ ] 标签已创建
- [ ] 发布版本已归档

### 2. 恢复测试 ✓

#### 数据库恢复
```bash
# 恢复数据库
psql pr_agent < backup_20240101.sql
```

- [ ] 恢复流程测试
- [ ] 恢复时间记录
- [ ] 数据完整性验证

#### 灾难恢复
- [ ] 完整恢复流程文档
- [ ] 恢复时间目标 (RTO) < 4 小时
- [ ] 恢复点目标 (RPO) < 1 小时
- [ ] 定期演练 (每季度)

## 运维准备

### 1. 文档准备 ✓

- [ ] 部署文档完整
- [ ] 运维手册编写
- [ ] 故障排查指南
- [ ] API 文档更新
- [ ] 用户使用手册

### 2. 团队培训 ✓

- [ ] 开发团队培训
- [ ] 运维团队培训
- [ ] 用户培训
- [ ] 管理员培训

### 3. 支持准备 ✓

- [ ] 问题反馈渠道
- [ ] 紧急联系方式
- [ ] 值班安排
- [ ] 升级流程

## 上线计划

### 1. 灰度发布 ✓

#### 阶段 1: 内部测试 (1-2 周)
- [ ] 开发团队使用
- [ ] 收集反馈
- [ ] 修复问题

#### 阶段 2: 小范围试用 (2-4 周)
- [ ] 选择 1-2 个项目
- [ ] 监控性能和稳定性
- [ ] 优化配置

#### 阶段 3: 全面推广
- [ ] 所有项目接入
- [ ] 持续监控
- [ ] 定期优化

### 2. 回滚计划 ✓

#### 回滚触发条件
- [ ] 严重 bug 影响使用
- [ ] 性能严重下降
- [ ] 数据丢失风险
- [ ] 安全漏洞

#### 回滚步骤
```bash
# K8s 回滚
kubectl rollout undo deployment/pr-agent-backend

# Docker Compose 回滚
docker-compose down
git checkout <previous-version>
docker-compose up -d
```

- [ ] 回滚流程测试
- [ ] 回滚时间 < 15 分钟

## 持续改进

### 1. 监控和告警 ✓

- [ ] 设置关键指标告警
- [ ] 配置告警通知
- [ ] 定期查看监控数据
- [ ] 优化告警阈值

### 2. 性能优化 ✓

- [ ] 定期性能测试
- [ ] 分析慢查询
- [ ] 优化缓存策略
- [ ] 调整资源配置

### 3. 安全加固 ✓

- [ ] 定期安全扫描
- [ ] 更新依赖版本
- [ ] 审查访问日志
- [ ] 渗透测试 (可选)

### 4. 功能迭代 ✓

- [ ] 收集用户反馈
- [ ] 规划新功能
- [ ] 定期版本发布
- [ ] 文档持续更新

## 签署确认

### 部署负责人
- 姓名: _______________
- 日期: _______________
- 签名: _______________

### 技术负责人
- 姓名: _______________
- 日期: _______________
- 签名: _______________

### 运维负责人
- 姓名: _______________
- 日期: _______________
- 签名: _______________

---

**检查清单版本**: 1.0  
**最后更新**: 2024-04  
**适用版本**: PR-Agent v1.0.0
