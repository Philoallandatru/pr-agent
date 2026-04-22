# 代码审查指标收集系统

全面的代码审查指标收集和分析系统，用于追踪审查效率、质量、团队表现等关键指标。

## 功能特性

### 1. 效率指标
- 首次响应时间
- 总审查时间
- 合并时间
- 审查吞吐量
- 响应时间百分位数（P50/P90/P95）

### 2. 质量指标
- 每次审查的平均评论数
- 每次审查发现的问题数
- 建议数量
- 迭代次数
- 批准率和拒绝率
- 彻底性评分（每100行代码的评论数）

### 3. 团队指标
- 活跃审查者数量
- 每个审查者的平均审查数
- 工作负载分布
- 工作负载标准差
- 每个PR的平均审查者数

### 4. 流程指标
- 总审查数
- 完成的审查数
- 待处理的审查数
- 完成率
- 平均代码变更量
- 合并率

### 5. 趋势分析
- 响应时间趋势
- 审查时间趋势
- 评论数趋势
- 问题发现趋势
- 吞吐量趋势

## 核心概念

### ReviewMetrics

单次审查的完整指标：

```python
@dataclass
class ReviewMetrics:
    review_id: str
    pr_id: str
    repository: str
    author: str
    reviewers: List[str]
    
    # 时间指标
    created_at: str
    first_response_time_minutes: Optional[float]
    total_review_time_minutes: Optional[float]
    time_to_merge_minutes: Optional[float]
    
    # 规模指标
    lines_added: int
    lines_deleted: int
    files_changed: int
    
    # 质量指标
    comments_count: int
    issues_found: int
    suggestions_made: int
    iterations: int
    
    # 结果
    approved: bool
    merged: bool
    rejected: bool
```

### TimeRange

时间范围枚举：

- `DAY`: 最近1天
- `WEEK`: 最近7天
- `MONTH`: 最近30天
- `QUARTER`: 最近90天
- `YEAR`: 最近365天
- `ALL_TIME`: 所有时间

## 使用示例

### Python API

#### 记录审查指标

```python
from pr_agent.metrics import get_metrics_collector, ReviewMetrics
from datetime import datetime, timezone

collector = get_metrics_collector()

# 记录审查
metrics = ReviewMetrics(
    review_id="rev-123",
    pr_id="PR-456",
    repository="myorg/myrepo",
    author="alice",
    reviewers=["bob", "charlie"],
    created_at=datetime.now(timezone.utc).isoformat(),
    first_response_time_minutes=45.0,
    total_review_time_minutes=180.0,
    time_to_merge_minutes=360.0,
    lines_added=250,
    lines_deleted=100,
    files_changed=8,
    comments_count=15,
    issues_found=5,
    suggestions_made=8,
    iterations=2,
    approved=True,
    merged=True
)

collector.record_review(metrics)
```

#### 更新审查指标

```python
# 更新审查状态
collector.update_review(
    "rev-123",
    merged=True,
    time_to_merge_minutes=360.0
)
```

#### 获取综合指标摘要

```python
from pr_agent.metrics import TimeRange

# 获取本月摘要
summary = collector.get_metrics_summary(TimeRange.MONTH)

print(f"总审查数: {summary.process.total_reviews}")
print(f"平均响应时间: {summary.efficiency.avg_first_response_time_minutes:.1f} 分钟")
print(f"平均审查时间: {summary.efficiency.avg_total_review_time_minutes:.1f} 分钟")
print(f"平均评论数: {summary.quality.avg_comments_per_review:.1f}")
print(f"批准率: {summary.quality.approval_rate:.1%}")
print(f"活跃审查者: {summary.team.active_reviewers}")
print(f"完成率: {summary.process.completion_rate:.1%}")
```

#### 获取审查者指标

```python
# 获取特定审查者的指标
reviewer_stats = collector.get_reviewer_metrics("bob", TimeRange.MONTH)

print(f"审查数: {reviewer_stats['reviews_count']}")
print(f"平均响应时间: {reviewer_stats['avg_response_time']:.1f} 分钟")
print(f"平均评论数: {reviewer_stats['avg_comments']:.1f}")
print(f"平均发现问题数: {reviewer_stats['avg_issues_found']:.1f}")
print(f"批准率: {reviewer_stats['approval_rate']:.1%}")
```

#### 获取作者指标

```python
# 获取特定作者的指标
author_stats = collector.get_author_metrics("alice", TimeRange.MONTH)

print(f"PR数: {author_stats['prs_count']}")
print(f"平均合并时间: {author_stats['avg_time_to_merge']:.1f} 分钟")
print(f"平均迭代次数: {author_stats['avg_iterations']:.1f}")
print(f"平均代码变更量: {author_stats['avg_lines_changed']:.0f} 行")
print(f"合并率: {author_stats['merge_rate']:.1%}")
```

#### 获取仓库指标

```python
# 获取特定仓库的指标
repo_stats = collector.get_repository_metrics("myorg/myrepo", TimeRange.MONTH)

print(f"审查数: {repo_stats['reviews_count']}")
print(f"活跃作者: {repo_stats['active_authors']}")
print(f"活跃审查者: {repo_stats['active_reviewers']}")
print(f"平均审查时间: {repo_stats['avg_review_time']:.1f} 分钟")
print(f"合并率: {repo_stats['merge_rate']:.1%}")
```

#### 比较时间段

```python
# 比较季度和月度指标
comparison = collector.compare_periods(TimeRange.QUARTER, TimeRange.MONTH)

print("效率变化:")
print(f"  响应时间: {comparison['efficiency']['response_time_change']:+.1f}%")
print(f"  审查时间: {comparison['efficiency']['review_time_change']:+.1f}%")
print(f"  吞吐量: {comparison['efficiency']['throughput_change']:+.1f}%")

print("\n质量变化:")
print(f"  评论数: {comparison['quality']['comments_change']:+.1f}%")
print(f"  问题数: {comparison['quality']['issues_change']:+.1f}%")
print(f"  批准率: {comparison['quality']['approval_rate_change']:+.1f}%")
```

### REST API

#### 记录审查指标

```bash
POST /api/metrics/reviews
Content-Type: application/json

{
  "review_id": "rev-123",
  "pr_id": "PR-456",
  "repository": "myorg/myrepo",
  "author": "alice",
  "reviewers": ["bob", "charlie"],
  "created_at": "2024-01-15T10:00:00Z",
  "first_response_time_minutes": 45.0,
  "total_review_time_minutes": 180.0,
  "lines_added": 250,
  "lines_deleted": 100,
  "files_changed": 8,
  "comments_count": 15,
  "issues_found": 5,
  "suggestions_made": 8,
  "iterations": 2,
  "approved": true,
  "merged": true
}
```

#### 更新审查指标

```bash
PUT /api/metrics/reviews/rev-123
Content-Type: application/json

{
  "merged": true,
  "time_to_merge_minutes": 360.0
}
```

#### 获取指标摘要

```bash
GET /api/metrics/summary?time_range=month&repository=myorg/myrepo
```

响应：
```json
{
  "time_range": "month",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-31T23:59:59Z",
  "efficiency": {
    "avg_first_response_time_minutes": 42.5,
    "avg_total_review_time_minutes": 165.3,
    "avg_time_to_merge_minutes": 345.7,
    "reviews_per_day": 3.2,
    "throughput": 2.8,
    "p90_response_time": 120.0,
    "p95_response_time": 180.0
  },
  "quality": {
    "avg_comments_per_review": 12.3,
    "avg_issues_per_review": 4.2,
    "avg_suggestions_per_review": 6.8,
    "avg_iterations": 1.8,
    "approval_rate": 0.92,
    "rejection_rate": 0.03,
    "thoroughness_score": 8.5,
    "issue_detection_rate": 4.2
  },
  "team": {
    "total_reviewers": 8,
    "active_reviewers": 6,
    "avg_reviews_per_reviewer": 15.3,
    "workload_std_dev": 3.2,
    "avg_reviewers_per_pr": 2.1
  },
  "process": {
    "total_reviews": 92,
    "completed_reviews": 85,
    "pending_reviews": 7,
    "completion_rate": 0.92,
    "avg_lines_changed": 285.5,
    "avg_files_changed": 6.8,
    "merge_rate": 0.89
  },
  "trends": {
    "response_time": [45, 42, 38, 40],
    "review_time": [180, 165, 155, 160],
    "comments": [10, 12, 13, 12],
    "issues": [3, 4, 5, 4],
    "throughput": [2.5, 2.8, 3.0, 2.9]
  }
}
```

#### 获取审查者指标

```bash
GET /api/metrics/reviewer/bob?time_range=month
```

响应：
```json
{
  "reviewer": "bob",
  "reviews_count": 25,
  "avg_response_time": 38.5,
  "median_response_time": 35.0,
  "avg_comments": 11.2,
  "avg_issues_found": 3.8,
  "avg_suggestions": 6.5,
  "approval_rate": 0.94
}
```

#### 获取作者指标

```bash
GET /api/metrics/author/alice?time_range=month
```

响应：
```json
{
  "author": "alice",
  "prs_count": 18,
  "avg_time_to_merge": 325.5,
  "avg_iterations": 1.7,
  "avg_lines_changed": 245.3,
  "avg_files_changed": 5.8,
  "merge_rate": 0.94,
  "avg_issues_per_pr": 3.2
}
```

#### 获取仓库指标

```bash
GET /api/metrics/repository/myorg/myrepo?time_range=month
```

响应：
```json
{
  "repository": "myorg/myrepo",
  "reviews_count": 92,
  "active_authors": 12,
  "active_reviewers": 8,
  "avg_review_time": 165.3,
  "avg_pr_size": 285.5,
  "merge_rate": 0.89
}
```

#### 比较时间段

```bash
GET /api/metrics/compare?period1=quarter&period2=month
```

响应：
```json
{
  "efficiency": {
    "response_time_change": -12.5,
    "review_time_change": -8.3,
    "throughput_change": +15.2
  },
  "quality": {
    "comments_change": +18.7,
    "issues_change": +22.3,
    "approval_rate_change": +3.2
  },
  "team": {
    "active_reviewers_change": +25.0,
    "workload_balance_change": -15.8
  }
}
```

## 指标解释

### 效率指标

- **首次响应时间**: PR创建到第一条审查评论的时间
- **总审查时间**: PR创建到批准的总时间
- **合并时间**: PR创建到合并的总时间
- **吞吐量**: 每天完成的审查数
- **P90/P95响应时间**: 90%/95%的审查在此时间内得到响应

### 质量指标

- **彻底性评分**: 每100行代码的评论数，反映审查深度
- **问题检测率**: 每次审查平均发现的问题数
- **建议率**: 每次审查平均提出的建议数
- **迭代次数**: PR从提交到批准的修改轮数

### 团队指标

- **工作负载标准差**: 审查者之间工作量分布的均衡程度，越小越均衡
- **审查分布**: 每个审查者的审查数量分布

## 最佳实践

### 1. 持续记录

在审查生命周期的关键点记录指标：

```python
# PR创建时
metrics = ReviewMetrics(
    review_id=f"rev-{pr_id}",
    pr_id=pr_id,
    repository=repo,
    author=author,
    reviewers=[],
    created_at=datetime.now(timezone.utc).isoformat()
)
collector.record_review(metrics)

# 第一条评论时
collector.update_review(
    f"rev-{pr_id}",
    first_response_time_minutes=calculate_response_time()
)

# 批准时
collector.update_review(
    f"rev-{pr_id}",
    approved=True,
    total_review_time_minutes=calculate_total_time()
)

# 合并时
collector.update_review(
    f"rev-{pr_id}",
    merged=True,
    time_to_merge_minutes=calculate_merge_time()
)
```

### 2. 定期分析

设置定期报告：

```python
# 每周报告
weekly_summary = collector.get_metrics_summary(TimeRange.WEEK)

# 发送给团队
send_report(weekly_summary)

# 识别趋势
if weekly_summary.efficiency.avg_first_response_time_minutes > 60:
    alert_team("响应时间超过目标")
```

### 3. 个人反馈

为审查者提供个人指标：

```python
def generate_reviewer_report(reviewer):
    stats = collector.get_reviewer_metrics(reviewer, TimeRange.MONTH)
    
    report = f"""
    审查者报告 - {reviewer}
    
    本月审查数: {stats['reviews_count']}
    平均响应时间: {stats['avg_response_time']:.1f} 分钟
    平均评论数: {stats['avg_comments']:.1f}
    批准率: {stats['approval_rate']:.1%}
    
    建议:
    """
    
    if stats['avg_response_time'] > 60:
        report += "- 考虑更快响应PR\n"
    if stats['avg_comments'] < 5:
        report += "- 考虑提供更详细的反馈\n"
    
    return report
```

### 4. 团队优化

基于指标优化团队流程：

```python
summary = collector.get_metrics_summary(TimeRange.MONTH)

# 检查工作负载平衡
if summary.team.workload_std_dev > 5:
    print("工作负载不均衡，考虑重新分配")

# 检查审查质量
if summary.quality.thoroughness_score < 5:
    print("审查深度不足，考虑培训")

# 检查效率
if summary.efficiency.avg_first_response_time_minutes > 120:
    print("响应时间过长，考虑增加审查者")
```

## 集成示例

### 与Bitbucket集成

```python
def on_pr_created(pr_data):
    collector = get_metrics_collector()
    
    metrics = ReviewMetrics(
        review_id=f"rev-{pr_data['id']}",
        pr_id=pr_data['id'],
        repository=pr_data['repository'],
        author=pr_data['author'],
        reviewers=pr_data['reviewers'],
        created_at=pr_data['created_at'],
        lines_added=pr_data['additions'],
        lines_deleted=pr_data['deletions'],
        files_changed=pr_data['changed_files']
    )
    
    collector.record_review(metrics)

def on_pr_commented(pr_data, comment_data):
    collector = get_metrics_collector()
    review_id = f"rev-{pr_data['id']}"
    
    # 更新评论数
    review = collector.reviews.get(review_id)
    if review:
        collector.update_review(
            review_id,
            comments_count=review.comments_count + 1
        )
        
        # 如果是第一条评论，记录响应时间
        if review.first_response_time_minutes is None:
            response_time = calculate_time_diff(
                review.created_at,
                comment_data['created_at']
            )
            collector.update_review(
                review_id,
                first_response_time_minutes=response_time
            )
```

### 仪表板集成

```python
def get_dashboard_data():
    collector = get_metrics_collector()
    
    return {
        "overview": collector.get_metrics_summary(TimeRange.WEEK),
        "top_reviewers": get_top_reviewers(collector),
        "slow_reviews": get_slow_reviews(collector),
        "trends": get_trend_charts(collector)
    }

def get_top_reviewers(collector):
    # 获取所有审查者
    all_reviewers = set()
    for review in collector.reviews.values():
        all_reviewers.update(review.reviewers)
    
    # 获取每个审查者的指标
    reviewer_stats = []
    for reviewer in all_reviewers:
        stats = collector.get_reviewer_metrics(reviewer, TimeRange.WEEK)
        reviewer_stats.append(stats)
    
    # 按审查数排序
    return sorted(
        reviewer_stats,
        key=lambda x: x['reviews_count'],
        reverse=True
    )[:10]
```

## 性能考虑

### 数据保留

定期清理旧数据：

```python
# 保留最近90天的数据
collector.clear_old_data(days=90)
```

### 批量操作

批量记录指标以提高性能：

```python
metrics_batch = []

for pr in prs:
    metrics = ReviewMetrics(...)
    metrics_batch.append(metrics)

# 批量保存
for metrics in metrics_batch:
    collector.record_review(metrics)
```

## 故障排除

### 指标不准确

确保在正确的时间点更新指标：

```python
# 错误：在PR创建时就设置合并时间
metrics = ReviewMetrics(..., time_to_merge_minutes=360)

# 正确：在实际合并时更新
collector.update_review(review_id, time_to_merge_minutes=360)
```

### 性能问题

对于大量数据，使用过滤器：

```python
# 只获取特定仓库的指标
summary = collector.get_metrics_summary(
    TimeRange.MONTH,
    repository="myorg/myrepo"
)
```

## 相关文档

- [仪表板系统](DASHBOARD.md)
- [质量评分系统](QUALITY_SCORING.md)
- [SLA管理](SLA.md)
- [趋势分析](TRENDS.md)
