# 监控工具快速入门

本指南帮助您快速开始使用PR-Agent的效率指标监控工具。

## 前提条件

1. **启用效率指标收集**

编辑 `.pr_agent.toml` 或 `pr_agent/settings/configuration.toml`：

```toml
[efficiency_metrics]
enabled = true
database_path = "pr_agent.db"
prometheus_enabled = true
```

2. **运行至少一次PR审查**

```bash
python -m pr_agent.cli --pr_url https://github.com/owner/repo/pull/123 review
```

## 三种监控方案

### 方案1：SQLite数据库仪表板（推荐）

**特点**：无需额外服务，直接查询数据库，提供完整的ROI分析

**使用方法**：

```bash
# 显示监控面板
python monitor_efficiency.py

# 导出CSV（最近30天）
python monitor_efficiency.py --export metrics.csv --days 30

# 指定数据库路径
python monitor_efficiency.py --db-path /path/to/pr_agent.db
```

**输出示例**：

```
================================================================================
PR-Agent AI效率监控面板
================================================================================

[最近7天汇总]
--------------------------------------------------------------------------------
  总Review数:        45
  发现问题总数:      127
  高严重性问题:      23
  代码建议数:        89
  总Token使用:       125,430
  总API成本:         $2.34
  节省时间:          7.5 小时
  平均处理时间:      31.3 秒
  平均复杂度:        0.65

[ROI分析（最近30天）]
--------------------------------------------------------------------------------
  节省时间:          15.2 小时
  API成本:           $5.67
  估算价值:          $760.00
  净节省:            $754.33
  ROI:               13,305.8%
```

### 方案2：Prometheus指标查看器

**特点**：轻量级，实时指标，需要PR-Agent服务运行

**使用方法**：

```bash
# 查看指标（默认端口8080）
python view_metrics.py

# 指定URL
python view_metrics.py --url http://localhost:8080/metrics
```

**注意**：此工具需要PR-Agent服务（如GitHub App或webhook服务器）正在运行并暴露 `/metrics` 端点。

### 方案3：Web监控界面

**特点**：可视化界面，易于分享

**使用方法**：

```bash
# 启动Web服务（默认端口5000）
python web_monitor.py

# 指定端口和数据库
python web_monitor.py --port 8080 --db-path pr_agent.db
```

然后在浏览器中访问：`http://localhost:5000`

## 常见使用场景

### 场景1：每日检查效率指标

```bash
# 添加到每日工作流
python monitor_efficiency.py
```

### 场景2：生成周报

```bash
# 导出最近7天的数据
python monitor_efficiency.py --export weekly_report.csv --days 7

# 在Excel或其他工具中打开 weekly_report.csv
```

### 场景3：长期趋势分析

```bash
# 导出所有历史数据
python monitor_efficiency.py --export all_metrics.csv

# 使用数据分析工具（Excel、Tableau、Power BI等）进行深度分析
```

### 场景4：团队共享监控面板

```bash
# 启动Web服务并允许外部访问
python web_monitor.py --host 0.0.0.0 --port 5000

# 团队成员可以通过 http://your-server-ip:5000 访问
```

### 场景5：CI/CD集成

在GitHub Actions中添加：

```yaml
- name: Generate Efficiency Report
  run: |
    python monitor_efficiency.py > efficiency_report.txt
    cat efficiency_report.txt >> $GITHUB_STEP_SUMMARY
```

## 直接查询数据库

如果您熟悉SQL，可以直接查询数据库：

```bash
# 使用Python
python -c "
import sqlite3
conn = sqlite3.connect('pr_agent.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM efficiency_metrics')
print(f'总记录数: {cursor.fetchone()[0]}')
"

# 或使用sqlite3命令行（如果已安装）
sqlite3 pr_agent.db "SELECT * FROM efficiency_metrics LIMIT 5;"
```

## 常见问题

### Q: 没有数据怎么办？

**A**: 确认以下几点：

1. 效率指标已启用（检查配置文件）
2. 已运行过至少一次PR审查
3. 数据库文件存在：`ls -lh pr_agent.db`

### Q: 如何清理旧数据？

**A**: 使用Python脚本：

```python
import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('pr_agent.db')
cutoff = datetime.now() - timedelta(days=90)
conn.execute("DELETE FROM efficiency_metrics WHERE created_at < ?", (cutoff,))
conn.commit()
print("已删除90天前的数据")
```

### Q: 如何备份数据？

**A**: 简单复制数据库文件：

```bash
cp pr_agent.db pr_agent_backup_$(date +%Y%m%d).db
```

### Q: Web界面无法访问？

**A**: 检查：

1. Flask是否安装：`pip install flask`
2. 端口是否被占用：`netstat -an | grep 5000`
3. 防火墙设置

### Q: Windows控制台显示乱码？

**A**: 工具已自动处理UTF-8编码。如果仍有问题，在PowerShell中运行：

```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
python monitor_efficiency.py
```

## 数据字段说明

主要字段：

- `pr_url`: PR链接
- `issues_found_total`: 发现的问题总数
- `code_suggestions_count`: 代码建议数
- `processing_time_seconds`: 处理时间（秒）
- `api_cost_usd`: API成本（美元）
- `estimated_human_time_saved_minutes`: 预估节省的人工时间（分钟）
- `pr_complexity_score`: PR复杂度评分（0-1）
- `model_used`: 使用的AI模型

完整字段列表请参考 [MONITORING_GUIDE.md](docs/MONITORING_GUIDE.md)

## 下一步

- 📖 阅读完整文档：[MONITORING_GUIDE.md](docs/MONITORING_GUIDE.md)
- 🔧 自定义配置：编辑 `pr_agent/settings/configuration.toml`
- 📊 集成到仪表板：导出CSV并导入到您的BI工具
- 🚀 自动化：将监控集成到CI/CD流程

## 技术支持

如有问题：

1. 查看完整文档：[docs/MONITORING_GUIDE.md](docs/MONITORING_GUIDE.md)
2. 检查日志：`pr_agent.log`
3. 提交Issue：[GitHub Issues](https://github.com/Codium-ai/pr-agent/issues)
