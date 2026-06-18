# 效率指标监控使用手册

本文档介绍如何在不部署Grafana/Prometheus的情况下监控PR-Agent的AI效率指标。

## 概述

PR-Agent提供三种监控方案：

1. **SQLite数据库仪表板** (`pr_agent/monitoring/efficiency_monitor.py`) - 推荐方案
2. **Prometheus指标查看器** (`pr_agent/monitoring/metrics_viewer.py`) - 轻量级方案
3. **Web监控界面** (`pr_agent/monitoring/web_dashboard.py`) - 可视化方案

## 前置条件

### 启用效率指标收集

在 `.pr_agent.toml` 或 `pr_agent/settings/configuration.toml` 中配置：

```toml
[efficiency_metrics]
enabled = true
database_path = "pr_agent.db"
prometheus_enabled = true
```

### 安装依赖

```bash
# 基础依赖（已包含在requirements.txt）
pip install sqlite3

# Web监控界面额外依赖
pip install flask

# Prometheus查看器额外依赖
pip install requests
```

## 方案1：SQLite数据库仪表板（推荐）

### 特点
- ✅ 无需额外服务
- ✅ 直接查询数据库
- ✅ 提供ROI分析
- ✅ 支持导出CSV
- ✅ 历史趋势分析

### 使用方法

```bash
# 显示完整仪表板
python -m pr_agent.monitoring.efficiency_monitor

# 导出数据到CSV
python -m pr_agent.monitoring.efficiency_monitor --export metrics_export.csv

# 指定数据库路径
python -m pr_agent.monitoring.efficiency_monitor --db-path /path/to/pr_agent.db
```

### 输出示例

```
╔══════════════════════════════════════════════════════════════╗
║           PR-Agent 效率指标监控仪表板                          ║
╚══════════════════════════════════════════════════════════════╝

📊 7天统计摘要
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  总审查次数: 45
  发现问题数: 127
  代码建议数: 89
  总处理时间: 23.5 分钟
  总API成本: $2.34
  预估节省时间: 450.0 分钟

💰 ROI分析
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  时间投资回报率: 19.15x
  成本效益比: 192.31 分钟/$
  平均每次审查节省: 10.0 分钟
  平均每次审查成本: $0.05

📈 每日趋势（最近7天）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  2024-01-15: 8次审查, 发现23个问题, 节省80分钟
  2024-01-16: 6次审查, 发现18个问题, 节省60分钟
  ...

🔤 语言分布
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Python, JavaScript: 25次
  TypeScript: 12次
  Go: 8次

💵 模型成本分布
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  gpt-4: $1.20 (15次调用)
  claude-opus-4: $0.89 (12次调用)
  gpt-3.5-turbo: $0.25 (18次调用)
```

### 高级用法

```python
from pr_agent.monitoring.efficiency_monitor import EfficiencyMonitor

# 创建监控实例
monitor = EfficiencyMonitor(db_path='pr_agent.db')

# 获取摘要数据
summary = monitor.get_summary(days=7)
print(f"总审查次数: {summary['total_reviews']}")

# 获取每日统计
daily_stats = monitor.get_daily_stats(days=30)
for stat in daily_stats:
    print(f"{stat['date']}: {stat['review_count']}次审查")

# 获取ROI分析
roi = monitor.get_roi_analysis(days=7)
print(f"时间ROI: {roi['time_roi']:.2f}x")

# 导出数据
monitor.export_csv('metrics.csv', days=30)
```

## 方案2：Prometheus指标查看器

### 特点
- ✅ 轻量级
- ✅ 实时指标
- ✅ 无需数据库
- ⚠️ 需要PR-Agent服务运行

### 使用方法

```bash
# 查看所有指标
python -m pr_agent.monitoring.metrics_viewer

# 指定Prometheus端点
python -m pr_agent.monitoring.metrics_viewer --url http://localhost:8080/metrics

# 只显示特定指标
python -m pr_agent.monitoring.metrics_viewer --filter ai_review
```

### 输出示例

```
╔══════════════════════════════════════════════════════════════╗
║              Prometheus 指标查看器                            ║
╚══════════════════════════════════════════════════════════════╝

📊 AI效率指标
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Counter: ai_issues_found_total
  总计: 127

Counter: ai_code_suggestions_total
  总计: 89

Counter: ai_api_calls_total
  gpt-4: 15
  claude-opus-4: 12
  gpt-3.5-turbo: 18

Histogram: ai_review_processing_time_seconds
  总计: 1410.5
  样本数: 45
  平均: 31.3秒

Gauge: ai_agentic_iterations
  当前值: 3
```

### 集成到监控系统

如果您有现有的Prometheus服务器，可以配置抓取PR-Agent的指标端点：

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'pr-agent'
    static_configs:
      - targets: ['localhost:8080']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

## 方案3：Web监控界面

### 特点
- ✅ 可视化界面
- ✅ 实时刷新
- ✅ 易于分享
- ⚠️ 需要运行Web服务

### 使用方法

```bash
# 启动Web服务（默认端口5000）
python -m pr_agent.monitoring.web_dashboard

# 指定端口
python -m pr_agent.monitoring.web_dashboard --port 8080

# 指定数据库路径
python -m pr_agent.monitoring.web_dashboard --db-path /path/to/pr_agent.db

# 后台运行
nohup python -m pr_agent.monitoring.web_dashboard > web_monitor.log 2>&1 &
```

### 访问界面

打开浏览器访问：`http://localhost:5000`

界面包含：
- 📊 统计卡片（审查次数、问题数、建议数、成本）
- 💰 ROI分析
- 📈 每日趋势图表
- 🔤 语言分布
- 💵 模型成本分布

### Docker部署

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt flask

COPY pr_agent ./pr_agent
COPY pr_agent.db .

EXPOSE 5000
CMD ["python", "-m", "pr_agent.monitoring.web_dashboard", "--host", "0.0.0.0"]
```

```bash
# 构建并运行
docker build -t pr-agent-monitor .
docker run -p 5000:5000 -v $(pwd)/pr_agent.db:/app/pr_agent.db pr-agent-monitor
```

## 数据库结构

效率指标存储在 `efficiency_metrics` 表中，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| pr_url | TEXT | PR链接 |
| pr_number | INTEGER | PR编号 |
| repository | TEXT | 仓库名称 |
| review_id | TEXT | 审查ID |
| created_at | TIMESTAMP | 创建时间 |
| pr_size_lines | INTEGER | PR代码行数 |
| pr_files_changed | INTEGER | 修改文件数 |
| pr_languages | TEXT | 编程语言（JSON数组） |
| pr_complexity_score | REAL | 复杂度评分（0-1） |
| issues_found | INTEGER | 发现问题数 |
| code_suggestions | INTEGER | 代码建议数 |
| processing_time_seconds | REAL | 处理时间（秒） |
| api_calls_count | INTEGER | API调用次数 |
| total_tokens_used | INTEGER | 使用token总数 |
| input_tokens | INTEGER | 输入token数 |
| output_tokens | INTEGER | 输出token数 |
| api_cost_usd | REAL | API成本（美元） |
| model_name | TEXT | 使用的模型 |
| estimated_human_time_minutes | REAL | 预估人工审查时间 |
| time_saved_minutes | REAL | 节省时间 |
| agentic_iterations | INTEGER | 代理迭代次数 |

### 直接SQL查询

```bash
# 连接数据库
sqlite3 pr_agent.db

# 查询最近的审查
SELECT pr_url, issues_found, time_saved_minutes, api_cost_usd
FROM efficiency_metrics
ORDER BY created_at DESC
LIMIT 10;

# 计算总ROI
SELECT 
    SUM(time_saved_minutes) as total_time_saved,
    SUM(api_cost_usd) as total_cost,
    SUM(time_saved_minutes) / SUM(api_cost_usd) as cost_efficiency
FROM efficiency_metrics
WHERE created_at >= datetime('now', '-7 days');

# 按语言统计
SELECT 
    pr_languages,
    COUNT(*) as review_count,
    AVG(complexity_score) as avg_complexity,
    SUM(time_saved_minutes) as total_time_saved
FROM efficiency_metrics
GROUP BY pr_languages
ORDER BY review_count DESC;
```

## 常见问题

### Q: 数据库文件在哪里？

A: 默认位置是 `pr_agent.db`，可以在配置文件中修改：

```toml
[efficiency_metrics]
database_path = "/path/to/custom/pr_agent.db"
```

### Q: 如何清理旧数据？

A: 使用SQL删除旧记录：

```bash
sqlite3 pr_agent.db "DELETE FROM efficiency_metrics WHERE created_at < datetime('now', '-90 days');"
```

或者在Python中：

```python
from pr_agent.storage.database import Database

db = Database()
db.execute("DELETE FROM efficiency_metrics WHERE created_at < datetime('now', '-90 days')")
```

### Q: 指标没有数据怎么办？

A: 检查以下几点：

1. 确认效率指标已启用：
```bash
grep -A 3 "\[efficiency_metrics\]" .pr_agent.toml
```

2. 确认数据库文件存在：
```bash
ls -lh pr_agent.db
```

3. 检查是否有审查记录：
```bash
sqlite3 pr_agent.db "SELECT COUNT(*) FROM efficiency_metrics;"
```

4. 查看PR-Agent日志：
```bash
tail -f pr_agent.log | grep -i efficiency
```

### Q: Web界面无法访问？

A: 检查：

1. Flask是否安装：`pip list | grep -i flask`
2. 端口是否被占用：`netstat -an | grep 5000`
3. 防火墙设置：`sudo ufw allow 5000`
4. 使用 `--host 0.0.0.0` 允许外部访问

### Q: 如何集成到CI/CD？

A: 在CI流程中添加监控报告：

```yaml
# .github/workflows/pr-agent.yml
- name: Generate Efficiency Report
  run: |
    python -m pr_agent.monitoring.efficiency_monitor > efficiency_report.txt
    cat efficiency_report.txt >> $GITHUB_STEP_SUMMARY

- name: Upload Report
  uses: actions/upload-artifact@v3
  with:
    name: efficiency-report
    path: efficiency_report.txt
```

### Q: 如何导出数据到其他系统？

A: 使用CSV导出功能：

```bash
# 导出最近30天的数据
python -m pr_agent.monitoring.efficiency_monitor --export metrics.csv --days 30

# 导入到其他系统（例如Excel、Tableau、Power BI）
```

或者直接查询数据库：

```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('pr_agent.db')
df = pd.read_sql_query("SELECT * FROM efficiency_metrics", conn)
df.to_excel('metrics.xlsx', index=False)
```

## 最佳实践

### 1. 定期备份数据库

```bash
# 每日备份
cp pr_agent.db pr_agent_backup_$(date +%Y%m%d).db

# 或使用cron
0 2 * * * cp /path/to/pr_agent.db /backup/pr_agent_$(date +\%Y\%m\%d).db
```

### 2. 设置数据保留策略

```python
# cleanup_old_metrics.py
from pr_agent.storage.database import Database
from datetime import datetime, timedelta

db = Database()
cutoff_date = datetime.now() - timedelta(days=90)
db.execute(
    "DELETE FROM efficiency_metrics WHERE created_at < ?",
    (cutoff_date,)
)
print(f"Deleted metrics older than {cutoff_date}")
```

### 3. 监控告警

```python
# check_metrics.py
from pr_agent.monitoring.efficiency_monitor import EfficiencyMonitor

monitor = EfficiencyMonitor()
summary = monitor.get_summary(days=1)

# 检查异常情况
if summary['total_cost'] > 10.0:
    print("⚠️ 警告：今日API成本超过$10")

if summary['avg_processing_time'] > 60:
    print("⚠️ 警告：平均处理时间超过60秒")

if summary['total_reviews'] == 0:
    print("⚠️ 警告：今日没有审查记录")
```

### 4. 性能优化

对于大量数据，建议：

1. 定期清理旧数据
2. 添加额外索引：
```sql
CREATE INDEX idx_efficiency_metrics_date ON efficiency_metrics(created_at);
CREATE INDEX idx_efficiency_metrics_repo ON efficiency_metrics(repository);
```

3. 使用分页查询：
```python
def get_metrics_paginated(page=1, page_size=100):
    offset = (page - 1) * page_size
    return db.execute(
        "SELECT * FROM efficiency_metrics ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (page_size, offset)
    )
```

## 技术支持

如有问题，请：

1. 查看日志文件：`pr_agent.log`
2. 检查配置文件：`.pr_agent.toml`
3. 提交Issue：[GitHub Issues](https://github.com/Codium-ai/pr-agent/issues)
4. 查看文档：[PR-Agent Documentation](https://pr-agent-docs.codium.ai/)

## 更新日志

- **2024-01-15**: 初始版本，支持三种监控方案
- **2024-01-15**: 添加CSV导出功能
- **2024-01-15**: 添加Web监控界面
