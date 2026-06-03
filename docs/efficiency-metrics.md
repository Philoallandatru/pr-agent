# AI效率指标系统

PR-Agent的AI效率指标系统自动收集、持久化和监控代码审查过程中的关键指标，帮助团队了解AI辅助的价值和成本。

## 功能特性

- **自动收集**: 在review过程中无需人工干预地收集指标
- **全面性**: 涵盖代码质量、效率、成本效益等多维度
- **持久化**: 长期保存数据到SQLite数据库支持趋势分析
- **可观测性**: 通过Prometheus暴露实时指标供监控使用
- **低侵入**: 使用context manager模式最小化对现有代码的修改

## 收集的指标

### 代码质量指标

- **问题发现**: 总问题数、高/中/低严重性问题数、安全问题数
- **改进建议**: 代码改进建议数量

### 效率指标

- **时间指标**: review处理耗时、估算节省的人工审查时间
- **成本指标**: API调用次数、token使用量、API成本（美元）

### PR特征指标

- **规模**: 代码行数、修改文件数
- **复杂度**: PR复杂度评分（0-1）、涉及的编程语言
- **Review类型**: standard/agentic、使用的AI模型、agentic搜索迭代次数

## 配置

### 启用/禁用指标收集

在`.pr_agent.toml`或`pr_agent/settings/configuration.toml`中配置：

```toml
[efficiency_metrics]
enabled = true  # 设置为false禁用指标收集
database_path = "pr_agent.db"
prometheus_enabled = true
```

### 自定义估算参数

```toml
[efficiency_metrics.estimation]
base_review_time_minutes = 10
time_per_file_minutes = 2
time_per_100_lines_minutes = 5
max_review_time_minutes = 240
```

### 自定义复杂度权重

```toml
[efficiency_metrics.complexity]
file_count_weight = 0.3
line_count_weight = 0.3
language_diversity_weight = 0.2
dispersion_weight = 0.2
```

### 自定义API定价

```toml
[efficiency_metrics.pricing.gpt-4]
prompt = 0.03
completion = 0.06

[efficiency_metrics.pricing.claude-opus]
prompt = 0.015
completion = 0.075
```

## 数据库查询

### 查询最近的效率指标

```python
from pr_agent.storage.database import Database

db = Database()
metrics = db.get_efficiency_metrics(limit=10)
for m in metrics:
    print(f"PR Review {m['pr_review_id']}: "
          f"{m['issues_found_total']} issues, "
          f"{m['estimated_human_time_saved_minutes']} min saved, "
          f"${m['api_cost_usd']:.4f} cost")
db.close()
```

### 查询特定PR的指标

```python
db = Database()
metrics = db.get_efficiency_metrics(pr_review_id=123)
if metrics:
    m = metrics[0]
    print(f"Complexity: {m['pr_complexity_score']:.2f}")
    print(f"Languages: {m['pr_languages']}")
    print(f"Processing time: {m['review_processing_time_seconds']:.1f}s")
db.close()
```

## Prometheus指标

### 访问指标端点

如果PR-Agent作为服务运行，访问`http://localhost:PORT/metrics`查看Prometheus指标。

### 常用查询

**平均review处理时间**:
```promql
rate(pr_agent_ai_review_processing_time_seconds_sum[5m]) / 
rate(pr_agent_ai_review_processing_time_seconds_count[5m])
```

**每小时发现的高严重性问题数**:
```promql
rate(pr_agent_ai_issues_found_total{severity="high"}[1h]) * 3600
```

**API成本趋势**:
```promql
rate(pr_agent_ai_cost_usd_total[1h]) * 3600
```

**平均时间节省**:
```promql
rate(pr_agent_ai_time_saved_minutes_sum[1h]) / 
rate(pr_agent_ai_time_saved_minutes_count[1h])
```

**PR复杂度分布**:
```promql
histogram_quantile(0.95, rate(pr_agent_ai_pr_complexity_score_bucket[5m]))
```

## 监控和告警

### 推荐的Prometheus告警规则

```yaml
groups:
  - name: pr_agent_efficiency
    rules:
      - alert: HighAPIcost
        expr: rate(pr_agent_ai_cost_usd_total[1h]) > 10
        annotations:
          summary: "API成本过高"
          description: "过去1小时API成本超过$10"
          
      - alert: LowIssueDetectionRate
        expr: rate(pr_agent_ai_issues_found_total[1h]) < 0.1
        annotations:
          summary: "问题检测率过低"
          description: "过去1小时平均每个review发现的问题少于0.1个"
          
      - alert: SlowReviewProcessing
        expr: |
          rate(pr_agent_ai_review_processing_time_seconds_sum[5m]) / 
          rate(pr_agent_ai_review_processing_time_seconds_count[5m]) > 300
        annotations:
          summary: "Review处理速度慢"
          description: "平均review处理时间超过5分钟"
```

## 数据分析示例

### 计算ROI

```python
from pr_agent.storage.database import Database

db = Database()
metrics = db.get_efficiency_metrics(limit=100)

total_time_saved = sum(m['estimated_human_time_saved_minutes'] or 0 for m in metrics)
total_cost = sum(m['api_cost_usd'] or 0 for m in metrics)

# 假设人工审查成本为$50/小时
human_cost_per_minute = 50 / 60
total_value = total_time_saved * human_cost_per_minute

roi = (total_value - total_cost) / total_cost * 100
print(f"ROI: {roi:.1f}%")
print(f"Total time saved: {total_time_saved:.0f} minutes")
print(f"Total API cost: ${total_cost:.2f}")
print(f"Total value: ${total_value:.2f}")

db.close()
```

### 分析复杂度与处理时间的关系

```python
import matplotlib.pyplot as plt
from pr_agent.storage.database import Database

db = Database()
metrics = db.get_efficiency_metrics(limit=1000)

complexity = [m['pr_complexity_score'] for m in metrics if m['pr_complexity_score']]
time = [m['review_processing_time_seconds'] for m in metrics if m['review_processing_time_seconds']]

plt.scatter(complexity, time)
plt.xlabel('PR Complexity Score')
plt.ylabel('Review Processing Time (seconds)')
plt.title('Complexity vs Processing Time')
plt.show()

db.close()
```

## 故障排除

### 指标未收集

1. 检查配置: `efficiency_metrics.enabled = true`
2. 检查日志: 查找"EfficiencyTracker"相关的错误信息
3. 检查数据库: 确认`efficiency_metrics`表存在

### Prometheus指标未暴露

1. 确认`prometheus_client`已安装: `pip install prometheus-client`
2. 检查配置: `efficiency_metrics.prometheus_enabled = true`
3. 确认服务正在运行并暴露`/metrics`端点

### 数据库错误

1. 检查数据库路径: `efficiency_metrics.database_path`
2. 确认目录存在且有写权限
3. 检查SQLite版本: `sqlite3 --version`

## 性能影响

指标收集对review性能的影响：
- **开销**: < 5%的额外处理时间
- **数据库写入**: 异步执行，不阻塞review流程
- **Prometheus更新**: 无锁操作，几乎无开销

## 数据保留

- **默认**: 保留所有历史数据
- **清理**: 可通过SQL手动清理旧数据
- **归档**: 建议定期导出数据到外部存储

```sql
-- 删除30天前的数据
DELETE FROM efficiency_metrics 
WHERE created_at < datetime('now', '-30 days');
```

## 扩展

### 添加自定义指标

1. 在`efficiency_metrics`表中添加新字段
2. 在`EfficiencyTracker`中添加追踪方法
3. 在`metrics.py`中添加Prometheus指标
4. 更新`_update_prometheus`方法

### 集成到其他工具

指标数据可以导出到：
- Grafana: 通过Prometheus数据源
- Datadog: 通过Prometheus集成
- 自定义仪表板: 直接查询SQLite数据库

## 参考

- 设计文档: `docs/superpowers/specs/2026-05-28-ai-efficiency-metrics-design.md`
- 实现计划: `docs/superpowers/plans/2026-05-28-ai-efficiency-metrics.md`
- 源代码: `pr_agent/monitoring/efficiency_tracker.py`
