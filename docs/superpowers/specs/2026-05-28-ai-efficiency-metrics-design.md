# AI效率指标系统设计

**日期**: 2026-05-28  
**状态**: 已批准  
**目标**: 为PR-Agent构建全面的AI提效指标收集、持久化和监控系统

## 1. 概述

本设计为PR-Agent添加AI效率指标追踪能力，在代码审查过程中自动收集关键指标，持久化到数据库，并通过Prometheus暴露供监控和分析使用。

### 核心目标

- **自动收集**: 在review过程中无需人工干预地收集指标
- **全面性**: 涵盖代码质量、效率、成本效益等多维度
- **持久化**: 长期保存数据支持趋势分析
- **可观测性**: 通过Prometheus暴露实时指标
- **低侵入**: 最小化对现有代码的修改

## 2. 架构设计

### 2.1 组件架构

```
┌─────────────────────────────────────────────────────────────┐
│                      PR Review Process                       │
│                    (pr_reviewer.py)                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 │ 1. 创建tracker
                 ▼
┌─────────────────────────────────────────────────────────────┐
│                   EfficiencyTracker                          │
│              (monitoring/efficiency_tracker.py)              │
│                                                              │
│  - Context manager模式                                       │
│  - 收集PR特征 (size, complexity, languages)                  │
│  - 追踪API调用 (tokens, cost)                                │
│  - 追踪发现的问题 (severity, type)                           │
│  - 计算时间节省估算                                          │
└────────┬───────────────────────────────────┬────────────────┘
         │                                   │
         │ 2. 保存到数据库                    │ 3. 更新Prometheus
         ▼                                   ▼
┌─────────────────────────┐    ┌──────────────────────────────┐
│   Database              │    │   Prometheus Metrics         │
│  (storage/database.py)  │    │   (monitoring/metrics.py)    │
│                         │    │                              │
│  - efficiency_metrics   │    │  - Counters                  │
│    表                   │    │  - Histograms                │
│  - 长期数据保留         │    │  - Gauges                    │
└─────────────────────────┘    └──────────────────────────────┘
```

### 2.2 数据流

1. **初始化阶段**: PR review开始时创建EfficiencyTracker，收集PR基础特征
2. **执行阶段**: Review过程中追踪API调用、发现的问题、agentic迭代
3. **完成阶段**: 计算派生指标（时间节省、ROI），保存到数据库，更新Prometheus

### 2.3 集成方式

使用**Context Manager模式**实现无侵入集成：

```python
with EfficiencyTracker(pr_review_id, git_provider) as tracker:
    # 现有review逻辑
    result = self.run()
    
    # 追踪结果
    tracker.track_issues_found(result.issues)
    tracker.track_code_suggestions(result.suggestions)
```

## 3. 指标分类

### 3.1 代码质量指标

**问题发现**:
- `issues_found_total`: 发现的问题总数
- `issues_high_severity`: 高严重性问题数
- `issues_medium_severity`: 中等严重性问题数
- `issues_low_severity`: 低严重性问题数
- `security_issues_found`: 安全问题数

**改进建议**:
- `code_suggestions_count`: 代码改进建议数

### 3.2 效率指标

**时间指标**:
- `review_response_time_seconds`: 从PR创建到review响应的时间
- `review_processing_time_seconds`: review处理耗时
- `estimated_human_time_saved_minutes`: 估算节省的人工审查时间

**成本指标**:
- `tokens_prompt`: 输入token数
- `tokens_completion`: 输出token数
- `tokens_total`: 总token数
- `api_calls_count`: API调用次数
- `api_cost_usd`: API成本（美元）

### 3.3 PR特征指标

**规模指标**:
- `pr_size_lines`: PR代码行数（增删总和）
- `pr_files_count`: 修改的文件数

**复杂度指标**:
- `pr_languages`: 涉及的编程语言（JSON数组）
- `pr_complexity_score`: PR复杂度评分（0-1）

**Review类型**:
- `review_type`: review类型（standard/agentic）
- `agentic_search_iterations`: agentic review的搜索迭代次数
- `model_used`: 使用的AI模型

## 4. 数据库设计

### 4.1 表结构

在现有`pr_reviews`表基础上，新增`efficiency_metrics`表：

```sql
CREATE TABLE efficiency_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_review_id INTEGER NOT NULL,
    
    -- 代码质量指标
    issues_found_total INTEGER DEFAULT 0,
    issues_high_severity INTEGER DEFAULT 0,
    issues_medium_severity INTEGER DEFAULT 0,
    issues_low_severity INTEGER DEFAULT 0,
    security_issues_found INTEGER DEFAULT 0,
    code_suggestions_count INTEGER DEFAULT 0,
    
    -- 效率指标
    estimated_review_effort INTEGER,
    review_response_time_seconds REAL,
    review_processing_time_seconds REAL NOT NULL,
    estimated_human_time_saved_minutes REAL,
    
    -- 成本指标
    tokens_prompt INTEGER DEFAULT 0,
    tokens_completion INTEGER DEFAULT 0,
    tokens_total INTEGER DEFAULT 0,
    api_calls_count INTEGER DEFAULT 0,
    api_cost_usd REAL,
    
    -- PR特征
    pr_size_lines INTEGER DEFAULT 0,
    pr_files_count INTEGER DEFAULT 0,
    pr_languages TEXT,
    pr_complexity_score REAL,
    
    -- Review元数据
    model_used TEXT,
    review_type TEXT,
    agentic_search_iterations INTEGER DEFAULT 0,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY(pr_review_id) REFERENCES pr_reviews(id) ON DELETE CASCADE
);

CREATE INDEX idx_efficiency_metrics_pr_review 
ON efficiency_metrics(pr_review_id);

CREATE INDEX idx_efficiency_metrics_created_at 
ON efficiency_metrics(created_at);
```

### 4.2 数据保留策略

- **短期数据**: 保留所有原始记录
- **长期数据**: 通过索引支持高效查询
- **清理策略**: 可选的数据归档机制（配置驱动）

## 5. EfficiencyTracker实现

### 5.1 核心类设计

```python
class EfficiencyTracker:
    """追踪PR review的效率指标"""
    
    def __init__(self, pr_review_id: int, git_provider: GitProvider):
        self.pr_review_id = pr_review_id
        self.git_provider = git_provider
        self.metrics = {}
        self.start_time = None
        self.end_time = None
        
    def __enter__(self):
        """进入context时收集PR特征"""
        self.start_time = time.time()
        self._collect_pr_features()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出context时保存指标"""
        self.end_time = time.time()
        self.metrics['review_processing_time_seconds'] = (
            self.end_time - self.start_time
        )
        self._calculate_derived_metrics()
        self._save_to_database()
        self._update_prometheus()
        
    def _collect_pr_features(self):
        """收集PR基础特征"""
        # 从git_provider获取PR信息
        # 计算代码行数、文件数、语言分布
        # 计算复杂度评分
        
    def track_api_call(self, tokens_prompt: int, 
                       tokens_completion: int, cost: float):
        """追踪单次API调用"""
        self.metrics['tokens_prompt'] += tokens_prompt
        self.metrics['tokens_completion'] += tokens_completion
        self.metrics['api_calls_count'] += 1
        self.metrics['api_cost_usd'] += cost
        
    def track_issues_found(self, issues: List[Dict]):
        """追踪发现的问题"""
        for issue in issues:
            severity = issue.get('severity', 'low')
            if severity == 'high':
                self.metrics['issues_high_severity'] += 1
            elif severity == 'medium':
                self.metrics['issues_medium_severity'] += 1
            else:
                self.metrics['issues_low_severity'] += 1
                
            if issue.get('type') == 'security':
                self.metrics['security_issues_found'] += 1
                
        self.metrics['issues_found_total'] = len(issues)
        
    def track_code_suggestions(self, suggestions: List[Dict]):
        """追踪代码改进建议"""
        self.metrics['code_suggestions_count'] = len(suggestions)
        
    def track_agentic_iteration(self):
        """追踪agentic review迭代"""
        self.metrics['agentic_search_iterations'] += 1
        
    def _calculate_derived_metrics(self):
        """计算派生指标"""
        # 估算人工审查时间节省
        # 计算ROI
        
    def _save_to_database(self):
        """保存到数据库"""
        # 使用Database类保存到efficiency_metrics表
        
    def _update_prometheus(self):
        """更新Prometheus指标"""
        # 更新counters, histograms, gauges
```

### 5.2 关键方法

**PR特征收集**:
- 从`git_provider.get_diff_files()`获取文件列表和diff
- 计算总行数（增加+删除）
- 识别编程语言（基于文件扩展名）
- 计算复杂度评分（基于文件数、行数、语言多样性）

**API成本计算**:
- 根据模型类型和token数计算成本
- 支持GPT-4、Claude等主流模型的定价

**时间节省估算**:
- 基于PR规模和复杂度估算人工审查时间
- 考虑发现的问题数量和严重性

## 6. Prometheus集成

### 6.1 新增指标

在`pr_agent/monitoring/metrics.py`中添加：

```python
if PROMETHEUS_AVAILABLE:
    # AI效率指标 - Counters
    ai_issues_found_total = Counter(
        'pr_agent_ai_issues_found_total',
        'Total issues found by AI review',
        ['repository', 'severity', 'type']
    )
    
    ai_code_suggestions_total = Counter(
        'pr_agent_ai_code_suggestions_total',
        'Total code suggestions made',
        ['repository']
    )
    
    ai_api_calls_total = Counter(
        'pr_agent_ai_api_calls_total',
        'Total AI API calls',
        ['model', 'repository']
    )
    
    ai_tokens_used_total = Counter(
        'pr_agent_ai_tokens_used_total',
        'Total tokens used',
        ['model', 'token_type']  # token_type: prompt/completion
    )
    
    ai_cost_usd_total = Counter(
        'pr_agent_ai_cost_usd_total',
        'Total AI API cost in USD',
        ['model', 'repository']
    )
    
    # AI效率指标 - Histograms
    ai_review_processing_time_seconds = Histogram(
        'pr_agent_ai_review_processing_time_seconds',
        'AI review processing time distribution',
        ['repository', 'review_type'],
        buckets=[1, 5, 10, 30, 60, 120, 300, 600]
    )
    
    ai_pr_size_lines = Histogram(
        'pr_agent_ai_pr_size_lines',
        'PR size in lines distribution',
        ['repository'],
        buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000]
    )
    
    ai_pr_complexity_score = Histogram(
        'pr_agent_ai_pr_complexity_score',
        'PR complexity score distribution',
        ['repository'],
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    )
    
    ai_time_saved_minutes = Histogram(
        'pr_agent_ai_time_saved_minutes',
        'Estimated human time saved distribution',
        ['repository'],
        buckets=[5, 10, 15, 30, 60, 120, 240]
    )
    
    # AI效率指标 - Gauges
    ai_agentic_iterations = Gauge(
        'pr_agent_ai_agentic_iterations',
        'Number of agentic search iterations',
        ['repository']
    )
```

### 6.2 指标更新时机

- **Counters**: 每次review完成时累加
- **Histograms**: 每次review完成时记录观测值
- **Gauges**: 实时更新当前值

### 6.3 查询示例

```promql
# 平均review处理时间
rate(pr_agent_ai_review_processing_time_seconds_sum[5m]) / 
rate(pr_agent_ai_review_processing_time_seconds_count[5m])

# 每小时发现的高严重性问题数
rate(pr_agent_ai_issues_found_total{severity="high"}[1h]) * 3600

# API成本趋势
rate(pr_agent_ai_cost_usd_total[1h]) * 3600

# 平均时间节省
rate(pr_agent_ai_time_saved_minutes_sum[1h]) / 
rate(pr_agent_ai_time_saved_minutes_count[1h])
```

## 7. 估算算法

### 7.1 人工审查时间估算

```python
def estimate_human_review_time(pr_features: Dict) -> float:
    """
    估算人工审查所需时间（分钟）
    
    基于经验公式：
    - 基础时间：10分钟
    - 文件因素：每个文件 +2分钟
    - 行数因素：每100行 +5分钟
    - 复杂度因素：complexity_score * 20分钟
    - 语言多样性：每种额外语言 +3分钟
    """
    base_time = 10
    
    file_time = pr_features['files_count'] * 2
    line_time = (pr_features['size_lines'] / 100) * 5
    complexity_time = pr_features['complexity_score'] * 20
    language_time = (len(pr_features['languages']) - 1) * 3
    
    total_time = base_time + file_time + line_time + complexity_time + language_time
    
    # 上限：4小时
    return min(total_time, 240)
```

### 7.2 复杂度评分算法

```python
def calculate_complexity_score(pr_features: Dict) -> float:
    """
    计算PR复杂度评分（0-1）
    
    考虑因素：
    - 文件数量（权重：0.3）
    - 代码行数（权重：0.3）
    - 语言多样性（权重：0.2）
    - 修改分散度（权重：0.2）
    """
    # 文件数量评分（归一化到0-1）
    file_score = min(pr_features['files_count'] / 20, 1.0)
    
    # 代码行数评分（归一化到0-1）
    line_score = min(pr_features['size_lines'] / 1000, 1.0)
    
    # 语言多样性评分
    language_score = min(len(pr_features['languages']) / 5, 1.0)
    
    # 修改分散度评分（基于文件路径的目录多样性）
    dispersion_score = calculate_dispersion(pr_features['file_paths'])
    
    complexity = (
        file_score * 0.3 +
        line_score * 0.3 +
        language_score * 0.2 +
        dispersion_score * 0.2
    )
    
    return complexity
```

### 7.3 API成本计算

```python
def calculate_api_cost(model: str, tokens_prompt: int, 
                       tokens_completion: int) -> float:
    """
    计算API调用成本（美元）
    
    定价（2026年5月）：
    - GPT-4: $0.03/1K prompt tokens, $0.06/1K completion tokens
    - GPT-4-turbo: $0.01/1K prompt tokens, $0.03/1K completion tokens
    - Claude Opus: $0.015/1K prompt tokens, $0.075/1K completion tokens
    - Claude Sonnet: $0.003/1K prompt tokens, $0.015/1K completion tokens
    """
    pricing = {
        'gpt-4': (0.03, 0.06),
        'gpt-4-turbo': (0.01, 0.03),
        'claude-opus': (0.015, 0.075),
        'claude-sonnet': (0.003, 0.015),
    }
    
    if model not in pricing:
        return 0.0
        
    prompt_price, completion_price = pricing[model]
    
    cost = (
        (tokens_prompt / 1000) * prompt_price +
        (tokens_completion / 1000) * completion_price
    )
    
    return cost
```

## 8. 集成点

### 8.1 pr_reviewer.py集成

在`PRReviewer.run()`方法中添加tracker：

```python
def run(self):
    # 创建或获取pr_review记录
    pr_review_id = self._get_or_create_pr_review()
    
    # 使用EfficiencyTracker
    with EfficiencyTracker(pr_review_id, self.git_provider) as tracker:
        # 设置review类型
        tracker.set_review_type('agentic' if self.use_agentic else 'standard')
        tracker.set_model(self.ai_handler.model)
        
        # 执行review
        result = self._perform_review()
        
        # 追踪结果
        tracker.track_issues_found(result.get('issues', []))
        tracker.track_code_suggestions(result.get('suggestions', []))
        
        # 如果使用agentic review，追踪迭代次数
        if self.use_agentic:
            tracker.set_agentic_iterations(result.get('iterations', 0))
    
    return result
```

### 8.2 AI Handler集成

在`ai_handlers/base_ai_handler.py`中添加token追踪：

```python
def chat_completion(self, messages, **kwargs):
    response = self._call_api(messages, **kwargs)
    
    # 追踪token使用
    if hasattr(self, 'efficiency_tracker'):
        usage = response.get('usage', {})
        cost = calculate_api_cost(
            self.model,
            usage.get('prompt_tokens', 0),
            usage.get('completion_tokens', 0)
        )
        self.efficiency_tracker.track_api_call(
            tokens_prompt=usage.get('prompt_tokens', 0),
            tokens_completion=usage.get('completion_tokens', 0),
            cost=cost
        )
    
    return response
```

### 8.3 Agentic Review集成

在`pr_agent/algo/agentic_review.py`中追踪迭代：

```python
def run_agentic_review(self, ...):
    iterations = 0
    
    while should_continue:
        # 执行搜索迭代
        self._search_iteration()
        iterations += 1
        
        # 追踪迭代
        if hasattr(self, 'efficiency_tracker'):
            self.efficiency_tracker.track_agentic_iteration()
    
    return result
```

## 9. 配置

### 9.1 配置项

在`configuration.toml`中添加：

```toml
[efficiency_metrics]
enabled = true
database_path = "pr_agent.db"
prometheus_enabled = true

# 估算算法参数
estimation.base_review_time_minutes = 10
estimation.time_per_file_minutes = 2
estimation.time_per_100_lines_minutes = 5
estimation.max_review_time_minutes = 240

# 复杂度评分权重
complexity.file_count_weight = 0.3
complexity.line_count_weight = 0.3
complexity.language_diversity_weight = 0.2
complexity.dispersion_weight = 0.2

# API定价（美元/1K tokens）
pricing.gpt-4.prompt = 0.03
pricing.gpt-4.completion = 0.06
pricing.gpt-4-turbo.prompt = 0.01
pricing.gpt-4-turbo.completion = 0.03
pricing.claude-opus.prompt = 0.015
pricing.claude-opus.completion = 0.075
pricing.claude-sonnet.prompt = 0.003
pricing.claude-sonnet.completion = 0.015
```

### 9.2 功能开关

支持通过配置禁用指标收集：

```python
if get_settings().get('efficiency_metrics.enabled', True):
    with EfficiencyTracker(...) as tracker:
        # 收集指标
else:
    # 跳过指标收集
```

## 10. 部署和测试

### 10.1 数据库迁移

添加数据库迁移脚本：

```python
# pr_agent/storage/migrations/add_efficiency_metrics.py
def migrate(conn):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS efficiency_metrics (
            -- 表结构见第4节
        )
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_efficiency_metrics_pr_review 
        ON efficiency_metrics(pr_review_id)
    """)
    conn.commit()
```

### 10.2 测试策略

**单元测试**:
- `test_efficiency_tracker.py`: 测试EfficiencyTracker各方法
- `test_estimation_algorithms.py`: 测试估算算法准确性
- `test_database_operations.py`: 测试数据库操作

**集成测试**:
- `test_e2e_metrics_collection.py`: 端到端测试指标收集流程
- `test_prometheus_integration.py`: 测试Prometheus指标暴露

**性能测试**:
- 验证指标收集对review性能的影响（目标：<5%开销）

### 10.3 监控和告警

建议的Prometheus告警规则：

```yaml
groups:
  - name: pr_agent_efficiency
    rules:
      - alert: HighAPIcost
        expr: rate(pr_agent_ai_cost_usd_total[1h]) > 10
        annotations:
          summary: "API成本过高"
          
      - alert: LowIssueDetectionRate
        expr: rate(pr_agent_ai_issues_found_total[1h]) < 0.1
        annotations:
          summary: "问题检测率过低"
```

## 11. 未来扩展

### 11.1 短期扩展

- 添加用户反馈收集（问题是否有效、建议是否有用）
- 支持自定义估算算法参数
- 添加更多派生指标（准确率、召回率）

### 11.2 长期扩展

- 机器学习模型优化估算算法
- 跨PR的趋势分析和异常检测
- 与CI/CD系统集成，追踪修复率
- 支持导出到其他监控系统（Datadog、New Relic）

## 12. 风险和缓解

### 12.1 性能风险

**风险**: 指标收集增加review延迟  
**缓解**: 
- 使用异步数据库写入
- Prometheus更新使用无锁操作
- 提供配置开关允许禁用

### 12.2 数据准确性风险

**风险**: 估算算法不准确  
**缓解**:
- 使用保守估算（宁可低估不高估）
- 提供配置参数允许调整
- 收集实际数据持续优化算法

### 12.3 存储风险

**风险**: 长期数据积累导致数据库膨胀  
**缓解**:
- 添加数据归档机制
- 提供清理脚本
- 使用索引优化查询性能

## 13. 总结

本设计提供了一个全面、可扩展的AI效率指标系统，通过最小侵入的方式集成到PR-Agent现有架构中。系统自动收集多维度指标，持久化到数据库，并通过Prometheus暴露供监控使用。

核心优势：
- **自动化**: 无需人工干预
- **全面性**: 涵盖质量、效率、成本多个维度
- **可观测性**: 实时Prometheus指标
- **可扩展性**: 易于添加新指标和算法
- **低侵入**: 使用context manager模式最小化代码修改
