# 代码审查报告生成系统

全面的报告生成系统，支持多种报告类型和输出格式，用于代码审查数据的可视化和分析。

## 功能特性

### 1. 报告类型

- **审查总结报告** (REVIEW_SUMMARY): 审查活动的综合概览
- **质量趋势报告** (QUALITY_TRENDS): 代码质量指标的时间序列分析
- **效率分析报告** (EFFICIENCY_ANALYSIS): 审查流程效率指标
- **问题分布报告** (ISSUE_DISTRIBUTION): 问题按严重性和类别的分布
- **团队表现报告** (TEAM_PERFORMANCE): 团队级别的审查指标
- **个人表现报告** (INDIVIDUAL_PERFORMANCE): 个人审查者的详细指标

### 2. 输出格式

- **JSON**: 结构化数据，便于程序处理
- **Markdown**: 纯文本格式，易于版本控制
- **HTML**: 富文本格式，包含样式和交互
- **PDF**: 打印友好格式（需要额外库支持）

### 3. 可视化

- 图表支持（条形图、折线图、饼图、散点图）
- 趋势分析可视化
- 分布图表
- 对比图表

### 4. 模板系统

- 自定义报告模板
- 预定义报告布局
- 可重用的报告结构

### 5. 调度功能

- 定期报告生成
- Cron 表达式支持
- 自动数据收集

## 核心概念

### ReportType

报告类型枚举：

```python
class ReportType(Enum):
    REVIEW_SUMMARY = "review_summary"
    QUALITY_TRENDS = "quality_trends"
    EFFICIENCY_ANALYSIS = "efficiency_analysis"
    ISSUE_DISTRIBUTION = "issue_distribution"
    TEAM_PERFORMANCE = "team_performance"
    INDIVIDUAL_PERFORMANCE = "individual_performance"
```

### ReportFormat

输出格式枚举：

```python
class ReportFormat(Enum):
    PDF = "pdf"
    HTML = "html"
    MARKDOWN = "markdown"
    JSON = "json"
```

### ReportConfig

报告配置：

```python
@dataclass
class ReportConfig:
    report_id: str
    report_type: ReportType
    title: str
    description: str = ""
    format: ReportFormat = ReportFormat.HTML
    include_charts: bool = True
    include_raw_data: bool = False
    template_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## 使用示例

### Python API

#### 生成审查总结报告

```python
from pr_agent.report_generator import (
    ReportGenerator,
    ReportType,
    ReportFormat,
    ReportConfig
)
from datetime import datetime, timezone

generator = ReportGenerator()

# 准备数据
data = {
    'total_reviews': 100,
    'avg_duration': 24.5,
    'total_comments': 450,
    'reviews_by_status': {
        'approved': 60,
        'changes_requested': 30,
        'pending': 10
    }
}

# 配置报告
config = ReportConfig(
    report_id="monthly-summary-2024-01",
    report_type=ReportType.REVIEW_SUMMARY,
    title="January 2024 Review Summary",
    description="Monthly code review activity summary",
    format=ReportFormat.HTML,
    include_charts=True
)

# 生成报告
report = generator.generate_report(
    config,
    data,
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    end_date=datetime(2024, 1, 31, tzinfo=timezone.utc)
)

print(f"Report generated: {report.file_path}")
```

#### 生成质量趋势报告

```python
data = {
    'quality_scores': {
        'dates': ['2024-01-01', '2024-01-08', '2024-01-15', '2024-01-22'],
        'scores': [85, 87, 90, 88]
    }
}

config = ReportConfig(
    report_id="quality-trends-q1",
    report_type=ReportType.QUALITY_TRENDS,
    title="Q1 Quality Trends",
    format=ReportFormat.MARKDOWN
)

report = generator.generate_report(config, data)
```

#### 生成效率分析报告

```python
data = {
    'time_to_first_comment': {
        'average': 2.5
    },
    'review_duration': {
        '0-4h': 20,
        '4-8h': 30,
        '8-24h': 35,
        '24h+': 15
    }
}

config = ReportConfig(
    report_id="efficiency-2024-01",
    report_type=ReportType.EFFICIENCY_ANALYSIS,
    title="January Efficiency Analysis",
    format=ReportFormat.HTML
)

report = generator.generate_report(config, data)
```

#### 生成问题分布报告

```python
data = {
    'issues_by_severity': {
        'critical': 5,
        'high': 15,
        'medium': 30,
        'low': 50
    },
    'issues_by_category': {
        'security': 10,
        'performance': 20,
        'style': 40,
        'bugs': 30
    }
}

config = ReportConfig(
    report_id="issues-2024-01",
    report_type=ReportType.ISSUE_DISTRIBUTION,
    title="January Issue Distribution",
    format=ReportFormat.JSON
)

report = generator.generate_report(config, data)
```

#### 生成团队表现报告

```python
data = {
    'team_metrics': {
        'total_members': 10,
        'total_reviews': 100,
        'avg_reviews_per_member': 10.0,
        'team_quality_score': 85.5
    },
    'top_reviewers': {
        'alice': 25,
        'bob': 20,
        'charlie': 15
    }
}

config = ReportConfig(
    report_id="team-performance-2024-01",
    report_type=ReportType.TEAM_PERFORMANCE,
    title="January Team Performance",
    format=ReportFormat.HTML
)

report = generator.generate_report(config, data)
```

#### 生成个人表现报告

```python
data = {
    'individual_metrics': {
        'total_reviews': 25,
        'avg_quality_score': 88.5,
        'total_comments': 120,
        'issues_found': 45,
        'avg_response_time': 2.3
    }
}

config = ReportConfig(
    report_id="alice-performance-2024-01",
    report_type=ReportType.INDIVIDUAL_PERFORMANCE,
    title="Alice's January Performance",
    format=ReportFormat.PDF
)

report = generator.generate_report(config, data)
```

#### 使用模板

```python
# 注册模板
template = {
    'sections': ['overview', 'details', 'recommendations'],
    'chart_style': 'modern',
    'color_scheme': 'blue'
}

generator.register_template("standard-template", template)

# 使用模板生成报告
config = ReportConfig(
    report_id="templated-report",
    report_type=ReportType.REVIEW_SUMMARY,
    title="Templated Report",
    format=ReportFormat.HTML,
    template_id="standard-template"
)

report = generator.generate_report(config, data)
```

#### 调度定期报告

```python
config = ReportConfig(
    report_id="weekly-summary",
    report_type=ReportType.REVIEW_SUMMARY,
    title="Weekly Review Summary",
    format=ReportFormat.HTML
)

# 每周一上午9点生成
schedule_id = generator.schedule_report(
    config,
    schedule="0 9 * * 1",  # Cron expression
    data_source="metrics_collector"
)

print(f"Scheduled: {schedule_id}")
```

#### 获取和列出报告

```python
# 获取特定报告
report = generator.get_report("monthly-summary-2024-01")
if report:
    print(f"Report: {report.title}")
    print(f"Generated: {report.generated_at}")
    print(f"File: {report.file_path}")

# 列出所有报告
all_reports = generator.list_reports()
print(f"Total reports: {len(all_reports)}")

# 按类型过滤
summary_reports = generator.list_reports(
    report_type=ReportType.REVIEW_SUMMARY
)

# 按格式过滤
html_reports = generator.list_reports(
    format=ReportFormat.HTML
)
```

### REST API

#### 生成报告

```bash
POST /api/reports/generate
Content-Type: application/json

{
  "report_id": "monthly-summary-2024-01",
  "report_type": "review_summary",
  "title": "January 2024 Review Summary",
  "description": "Monthly code review activity summary",
  "format": "html",
  "include_charts": true,
  "data": {
    "total_reviews": 100,
    "avg_duration": 24.5,
    "total_comments": 450,
    "reviews_by_status": {
      "approved": 60,
      "changes_requested": 30,
      "pending": 10
    }
  },
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z"
}
```

响应：
```json
{
  "report_id": "monthly-summary-2024-01",
  "report_type": "review_summary",
  "format": "html",
  "title": "January 2024 Review Summary",
  "generated_at": "2024-02-01T10:00:00Z",
  "file_path": "/path/to/report.html",
  "metadata": {}
}
```

#### 获取报告

```bash
GET /api/reports/monthly-summary-2024-01
```

响应：
```json
{
  "report_id": "monthly-summary-2024-01",
  "report_type": "review_summary",
  "format": "html",
  "title": "January 2024 Review Summary",
  "generated_at": "2024-02-01T10:00:00Z",
  "file_path": "/path/to/report.html",
  "content": null,
  "metadata": {}
}
```

#### 列出报告

```bash
GET /api/reports?report_type=review_summary&format=html
```

响应：
```json
{
  "reports": [
    {
      "report_id": "monthly-summary-2024-01",
      "report_type": "review_summary",
      "format": "html",
      "title": "January 2024 Review Summary",
      "generated_at": "2024-02-01T10:00:00Z",
      "file_path": "/path/to/report.html",
      "metadata": {}
    }
  ]
}
```

#### 注册模板

```bash
POST /api/reports/templates
Content-Type: application/json

{
  "template_id": "standard-template",
  "sections": ["overview", "details", "recommendations"],
  "chart_style": "modern",
  "color_scheme": "blue"
}
```

#### 调度报告

```bash
POST /api/reports/schedule
Content-Type: application/json

{
  "report_id": "weekly-summary",
  "report_type": "review_summary",
  "title": "Weekly Review Summary",
  "format": "html",
  "schedule": "0 9 * * 1",
  "data_source": "metrics_collector"
}
```

响应：
```json
{
  "schedule_id": "schedule_weekly-summary_1706781234.567"
}
```

#### 下载报告

```bash
GET /api/reports/monthly-summary-2024-01/download
```

返回报告文件作为下载。

## 报告数据结构

### 审查总结数据

```python
{
    'total_reviews': int,
    'avg_duration': float,  # hours
    'total_comments': int,
    'reviews_by_status': {
        'approved': int,
        'changes_requested': int,
        'pending': int
    }
}
```

### 质量趋势数据

```python
{
    'quality_scores': {
        'dates': List[str],  # ISO date strings
        'scores': List[float]  # 0-100
    }
}
```

### 效率分析数据

```python
{
    'time_to_first_comment': {
        'average': float,  # hours
        'median': float,
        'p90': float
    },
    'review_duration': {
        '0-4h': int,
        '4-8h': int,
        '8-24h': int,
        '24h+': int
    }
}
```

### 问题分布数据

```python
{
    'issues_by_severity': {
        'critical': int,
        'high': int,
        'medium': int,
        'low': int
    },
    'issues_by_category': {
        'security': int,
        'performance': int,
        'style': int,
        'bugs': int
    }
}
```

### 团队表现数据

```python
{
    'team_metrics': {
        'total_members': int,
        'total_reviews': int,
        'avg_reviews_per_member': float,
        'team_quality_score': float
    },
    'top_reviewers': {
        'reviewer_name': int  # review count
    }
}
```

### 个人表现数据

```python
{
    'individual_metrics': {
        'total_reviews': int,
        'avg_quality_score': float,
        'total_comments': int,
        'issues_found': int,
        'avg_response_time': float  # hours
    }
}
```

## 最佳实践

### 1. 定期生成报告

设置自动化报告生成：

```python
# 每日报告
daily_config = ReportConfig(
    report_id="daily-summary",
    report_type=ReportType.REVIEW_SUMMARY,
    title="Daily Review Summary",
    format=ReportFormat.HTML
)
generator.schedule_report(daily_config, "0 9 * * *", "metrics")

# 每周报告
weekly_config = ReportConfig(
    report_id="weekly-trends",
    report_type=ReportType.QUALITY_TRENDS,
    title="Weekly Quality Trends",
    format=ReportFormat.PDF
)
generator.schedule_report(weekly_config, "0 9 * * 1", "metrics")

# 每月报告
monthly_config = ReportConfig(
    report_id="monthly-performance",
    report_type=ReportType.TEAM_PERFORMANCE,
    title="Monthly Team Performance",
    format=ReportFormat.HTML
)
generator.schedule_report(monthly_config, "0 9 1 * *", "metrics")
```

### 2. 使用适当的格式

根据用途选择格式：

```python
# 用于邮件分发
email_config = ReportConfig(
    report_id="email-report",
    report_type=ReportType.REVIEW_SUMMARY,
    title="Weekly Summary",
    format=ReportFormat.HTML  # 富文本，易于阅读
)

# 用于存档
archive_config = ReportConfig(
    report_id="archive-report",
    report_type=ReportType.REVIEW_SUMMARY,
    title="Q1 Archive",
    format=ReportFormat.PDF  # 打印友好，长期保存
)

# 用于程序处理
api_config = ReportConfig(
    report_id="api-report",
    report_type=ReportType.REVIEW_SUMMARY,
    title="API Data",
    format=ReportFormat.JSON  # 结构化，易于解析
)

# 用于版本控制
vcs_config = ReportConfig(
    report_id="vcs-report",
    report_type=ReportType.REVIEW_SUMMARY,
    title="VCS Report",
    format=ReportFormat.MARKDOWN  # 纯文本，diff 友好
)
```

### 3. 包含相关图表

启用图表以提高可读性：

```python
config = ReportConfig(
    report_id="visual-report",
    report_type=ReportType.ISSUE_DISTRIBUTION,
    title="Issue Distribution with Charts",
    format=ReportFormat.HTML,
    include_charts=True  # 包含可视化
)
```

### 4. 添加元数据

使用元数据进行分类和搜索：

```python
config = ReportConfig(
    report_id="tagged-report",
    report_type=ReportType.REVIEW_SUMMARY,
    title="Tagged Report",
    format=ReportFormat.HTML,
    metadata={
        'team': 'backend',
        'project': 'api-v2',
        'quarter': 'Q1-2024',
        'author': 'system'
    }
)
```

### 5. 组合多个报告类型

生成综合报告：

```python
def generate_comprehensive_report(period_start, period_end):
    """Generate a comprehensive multi-section report."""
    
    # 收集所有数据
    summary_data = get_summary_data(period_start, period_end)
    quality_data = get_quality_data(period_start, period_end)
    efficiency_data = get_efficiency_data(period_start, period_end)
    
    # 生成各个部分
    reports = []
    
    for report_type, data in [
        (ReportType.REVIEW_SUMMARY, summary_data),
        (ReportType.QUALITY_TRENDS, quality_data),
        (ReportType.EFFICIENCY_ANALYSIS, efficiency_data)
    ]:
        config = ReportConfig(
            report_id=f"comprehensive-{report_type.value}",
            report_type=report_type,
            title=f"Comprehensive Report - {report_type.value}",
            format=ReportFormat.HTML
        )
        
        report = generator.generate_report(config, data, period_start, period_end)
        reports.append(report)
    
    return reports
```

## 集成示例

### 与指标收集器集成

```python
from pr_agent.metrics import get_metrics_collector, TimeRange

def generate_metrics_report(time_range: TimeRange):
    """Generate report from metrics collector."""
    collector = get_metrics_collector()
    generator = ReportGenerator()
    
    # 获取指标摘要
    summary = collector.get_metrics_summary(time_range)
    
    # 准备报告数据
    data = {
        'total_reviews': summary.process.total_reviews,
        'avg_duration': summary.efficiency.avg_total_review_time_minutes / 60,
        'total_comments': summary.process.total_reviews * summary.quality.avg_comments_per_review,
        'reviews_by_status': {
            'approved': int(summary.process.total_reviews * summary.quality.approval_rate),
            'changes_requested': summary.process.total_reviews - summary.process.completed_reviews,
            'pending': summary.process.pending_reviews
        }
    }
    
    # 生成报告
    config = ReportConfig(
        report_id=f"metrics-report-{time_range.value}",
        report_type=ReportType.REVIEW_SUMMARY,
        title=f"Metrics Report - {time_range.value}",
        format=ReportFormat.HTML
    )
    
    return generator.generate_report(config, data)
```

### 邮件分发

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def email_report(report: GeneratedReport, recipients: List[str]):
    """Email a generated report."""
    msg = MIMEMultipart()
    msg['Subject'] = report.title
    msg['From'] = 'reports@example.com'
    msg['To'] = ', '.join(recipients)
    
    # 添加正文
    if report.format == ReportFormat.HTML:
        body = Path(report.file_path).read_text()
        msg.attach(MIMEText(body, 'html'))
    else:
        body = f"Please find attached: {report.title}"
        msg.attach(MIMEText(body, 'plain'))
    
    # 添加附件
    if report.file_path:
        with open(report.file_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename={Path(report.file_path).name}'
            )
            msg.attach(part)
    
    # 发送
    with smtplib.SMTP('smtp.example.com', 587) as server:
        server.starttls()
        server.login('user', 'password')
        server.send_message(msg)
```

## 故障排除

### 报告生成失败

检查数据格式：

```python
# 确保数据包含必需字段
required_fields = {
    ReportType.REVIEW_SUMMARY: ['total_reviews', 'avg_duration'],
    ReportType.QUALITY_TRENDS: ['quality_scores'],
    ReportType.EFFICIENCY_ANALYSIS: ['time_to_first_comment']
}

def validate_data(report_type: ReportType, data: Dict):
    """Validate report data."""
    required = required_fields.get(report_type, [])
    missing = [f for f in required if f not in data]
    
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
```

### 文件路径问题

确保输出目录存在：

```python
output_dir = Path(".pr_agent/reports")
output_dir.mkdir(parents=True, exist_ok=True)

generator = ReportGenerator(output_dir=str(output_dir))
```

### 格式不支持

检查格式支持：

```python
supported_formats = [ReportFormat.JSON, ReportFormat.MARKDOWN, ReportFormat.HTML]

if config.format not in supported_formats:
    print(f"Format {config.format} may require additional libraries")
```

## 相关文档

- [指标收集系统](METRICS_COLLECTION.md)
- [仪表板系统](DASHBOARD.md)
- [质量评分系统](QUALITY_SCORING.md)
- [趋势分析](TRENDS.md)
