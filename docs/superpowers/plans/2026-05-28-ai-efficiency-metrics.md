# AI效率指标系统实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为PR-Agent构建全面的AI效率指标收集、持久化和监控系统

**Architecture:** 使用EfficiencyTracker作为核心组件，通过context manager模式在review过程中自动收集指标。数据持久化到SQLite数据库的efficiency_metrics表，同时通过Prometheus暴露实时指标供监控使用。

**Tech Stack:** Python 3.12+, SQLite, Prometheus Client, pytest

---

## 文件结构

**新建文件:**
- `pr_agent/monitoring/efficiency_tracker.py` - 核心追踪器类
- `pr_agent/monitoring/estimation.py` - 估算算法（时间、复杂度、成本）
- `tests/unittest/test_efficiency_tracker.py` - 追踪器单元测试
- `tests/unittest/test_estimation.py` - 估算算法单元测试
- `tests/unittest/test_efficiency_database.py` - 数据库操作测试

**修改文件:**
- `pr_agent/storage/database.py` - 添加efficiency_metrics表和相关方法
- `pr_agent/monitoring/metrics.py` - 添加AI效率相关的Prometheus指标
- `pr_agent/tools/pr_reviewer.py` - 集成EfficiencyTracker
- `pr_agent/settings/configuration.toml` - 添加efficiency_metrics配置节

---


### Task 1: 数据库Schema和基础方法

**Files:**
- Modify: `pr_agent/storage/database.py:38-115`
- Test: `tests/unittest/test_efficiency_database.py`

- [ ] **Step 1: 编写数据库表创建测试**

```python
# tests/unittest/test_efficiency_database.py
import pytest
import sqlite3
from pr_agent.storage.database import Database


def test_efficiency_metrics_table_exists():
    """测试efficiency_metrics表是否被创建"""
    db = Database(":memory:")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='efficiency_metrics'
    """)
    assert cursor.fetchone() is not None


def test_efficiency_metrics_indexes_exist():
    """测试索引是否被创建"""
    db = Database(":memory:")
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name='idx_efficiency_metrics_pr_review'
    """)
    assert cursor.fetchone() is not None
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name='idx_efficiency_metrics_created_at'
    """)
    assert cursor.fetchone() is not None
```

- [ ] **Step 2: 运行测试验证失败**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_database.py::test_efficiency_metrics_table_exists -v`
Expected: FAIL - 表不存在

- [ ] **Step 3: 在database.py中添加表创建SQL**

```python
# pr_agent/storage/database.py
# 在_create_tables方法中，在现有表创建之后添加：

def _create_tables(self):
    cursor = self.conn.cursor()
    
    # ... 现有表创建代码 ...
    
    # Efficiency metrics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS efficiency_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pr_review_id INTEGER NOT NULL,
            
            issues_found_total INTEGER DEFAULT 0,
            issues_high_severity INTEGER DEFAULT 0,
            issues_medium_severity INTEGER DEFAULT 0,
            issues_low_severity INTEGER DEFAULT 0,
            security_issues_found INTEGER DEFAULT 0,
            code_suggestions_count INTEGER DEFAULT 0,
            
            estimated_review_effort INTEGER,
            review_response_time_seconds REAL,
            review_processing_time_seconds REAL NOT NULL,
            estimated_human_time_saved_minutes REAL,
            
            tokens_prompt INTEGER DEFAULT 0,
            tokens_completion INTEGER DEFAULT 0,
            tokens_total INTEGER DEFAULT 0,
            api_calls_count INTEGER DEFAULT 0,
            api_cost_usd REAL,
            
            pr_size_lines INTEGER DEFAULT 0,
            pr_files_count INTEGER DEFAULT 0,
            pr_languages TEXT,
            pr_complexity_score REAL,
            
            model_used TEXT,
            review_type TEXT,
            agentic_search_iterations INTEGER DEFAULT 0,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            FOREIGN KEY(pr_review_id) REFERENCES pr_reviews(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_efficiency_metrics_pr_review 
        ON efficiency_metrics(pr_review_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_efficiency_metrics_created_at 
        ON efficiency_metrics(created_at)
    """)
    
    self.conn.commit()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_database.py -v`
Expected: PASS - 所有测试通过

- [ ] **Step 5: 编写add_efficiency_metrics方法测试**

```python
# tests/unittest/test_efficiency_database.py

def test_add_efficiency_metrics():
    """测试添加效率指标记录"""
    db = Database(":memory:")
    
    # 先创建一个repository和pr_review
    repo_id = db.add_repository("TEST", "repo")
    review_id = db.add_pr_review(
        repository_id=repo_id,
        pr_id=1,
        pr_title="Test PR",
        pr_author="test_user",
        pr_url="https://test.com/pr/1",
        commands_run=["review"]
    )
    
    # 添加效率指标
    metrics_id = db.add_efficiency_metrics(
        pr_review_id=review_id,
        metrics={
            'issues_found_total': 5,
            'issues_high_severity': 2,
            'pr_size_lines': 100,
            'pr_files_count': 3,
            'tokens_total': 1000,
            'api_cost_usd': 0.05,
            'review_processing_time_seconds': 30.5
        }
    )
    
    assert metrics_id > 0
    
    # 验证数据
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM efficiency_metrics WHERE id = ?", (metrics_id,))
    row = cursor.fetchone()
    assert row is not None
    assert dict(row)['issues_found_total'] == 5
    assert dict(row)['pr_size_lines'] == 100
```

- [ ] **Step 6: 运行测试验证失败**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_database.py::test_add_efficiency_metrics -v`
Expected: FAIL - add_efficiency_metrics方法不存在

- [ ] **Step 7: 实现add_efficiency_metrics方法**

```python
# pr_agent/storage/database.py
# 在Database类中添加方法：

def add_efficiency_metrics(
    self,
    pr_review_id: int,
    metrics: Dict
) -> int:
    """Add efficiency metrics record"""
    cursor = self.conn.cursor()
    
    # 构建字段和值列表
    fields = ['pr_review_id']
    values = [pr_review_id]
    placeholders = ['?']
    
    for key, value in metrics.items():
        fields.append(key)
        values.append(value)
        placeholders.append('?')
    
    query = f"""
        INSERT INTO efficiency_metrics ({', '.join(fields)})
        VALUES ({', '.join(placeholders)})
    """
    
    cursor.execute(query, values)
    self.conn.commit()
    return cursor.lastrowid


def get_efficiency_metrics(
    self,
    pr_review_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """Get efficiency metrics with filters"""
    query = "SELECT * FROM efficiency_metrics WHERE 1=1"
    params = []
    
    if pr_review_id is not None:
        query += " AND pr_review_id = ?"
        params.append(pr_review_id)
    
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    cursor = self.conn.cursor()
    cursor.execute(query, params)
    return [dict(row) for row in cursor.fetchall()]
```

- [ ] **Step 8: 运行测试验证通过**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_database.py -v`
Expected: PASS

- [ ] **Step 9: 提交**

```bash
git add pr_agent/storage/database.py tests/unittest/test_efficiency_database.py
git commit -m "feat: add efficiency_metrics table and database methods"
```


### Task 2: 估算算法实现

**Files:**
- Create: `pr_agent/monitoring/estimation.py`
- Test: `tests/unittest/test_estimation.py`

- [ ] **Step 1: 编写复杂度评分测试**

```python
# tests/unittest/test_estimation.py
import pytest
from pr_agent.monitoring.estimation import (
    calculate_complexity_score,
    estimate_human_review_time,
    calculate_api_cost,
    calculate_dispersion
)


def test_calculate_complexity_score_simple():
    """测试简单PR的复杂度评分"""
    pr_features = {
        'files_count': 2,
        'size_lines': 50,
        'languages': ['Python'],
        'file_paths': ['src/main.py', 'src/utils.py']
    }
    score = calculate_complexity_score(pr_features)
    assert 0 <= score <= 1
    assert score < 0.3  # 简单PR应该得分较低


def test_calculate_complexity_score_complex():
    """测试复杂PR的复杂度评分"""
    pr_features = {
        'files_count': 25,
        'size_lines': 1500,
        'languages': ['Python', 'JavaScript', 'TypeScript', 'Go'],
        'file_paths': [
            'backend/api/users.py',
            'backend/api/auth.py',
            'frontend/components/Login.tsx',
            'frontend/utils/api.ts',
            'services/worker/main.go'
        ]
    }
    score = calculate_complexity_score(pr_features)
    assert 0 <= score <= 1
    assert score > 0.6  # 复杂PR应该得分较高
```

- [ ] **Step 2: 运行测试验证失败**

Run: `PYTHONPATH=. pytest tests/unittest/test_estimation.py::test_calculate_complexity_score_simple -v`
Expected: FAIL - 模块不存在

- [ ] **Step 3: 实现复杂度评分算法**

```python
# pr_agent/monitoring/estimation.py
from typing import Dict, List
from pathlib import Path


def calculate_dispersion(file_paths: List[str]) -> float:
    """
    计算文件修改的分散度（0-1）
    基于文件路径的目录多样性
    """
    if not file_paths:
        return 0.0
    
    # 提取所有唯一的目录
    directories = set()
    for path in file_paths:
        parts = Path(path).parts
        # 添加所有父目录
        for i in range(len(parts)):
            directories.add('/'.join(parts[:i+1]))
    
    # 归一化：目录数量相对于文件数量
    # 如果每个文件在不同目录，分散度高
    dispersion = len(directories) / (len(file_paths) * 2)
    return min(dispersion, 1.0)


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
    
    # 修改分散度评分
    dispersion_score = calculate_dispersion(pr_features.get('file_paths', []))
    
    complexity = (
        file_score * 0.3 +
        line_score * 0.3 +
        language_score * 0.2 +
        dispersion_score * 0.2
    )
    
    return complexity
```

- [ ] **Step 4: 运行测试验证通过**

Run: `PYTHONPATH=. pytest tests/unittest/test_estimation.py::test_calculate_complexity_score_simple -v`
Expected: PASS

Run: `PYTHONPATH=. pytest tests/unittest/test_estimation.py::test_calculate_complexity_score_complex -v`
Expected: PASS

- [ ] **Step 5: 编写时间估算测试**

```python
# tests/unittest/test_estimation.py

def test_estimate_human_review_time_small():
    """测试小型PR的时间估算"""
    pr_features = {
        'files_count': 2,
        'size_lines': 50,
        'languages': ['Python'],
        'complexity_score': 0.2
    }
    time_minutes = estimate_human_review_time(pr_features)
    assert 10 <= time_minutes <= 30


def test_estimate_human_review_time_large():
    """测试大型PR的时间估算"""
    pr_features = {
        'files_count': 20,
        'size_lines': 1000,
        'languages': ['Python', 'JavaScript', 'Go'],
        'complexity_score': 0.8
    }
    time_minutes = estimate_human_review_time(pr_features)
    assert 60 <= time_minutes <= 240


def test_estimate_human_review_time_capped():
    """测试时间估算上限"""
    pr_features = {
        'files_count': 100,
        'size_lines': 10000,
        'languages': ['Python', 'JavaScript', 'Go', 'Rust', 'C++'],
        'complexity_score': 1.0
    }
    time_minutes = estimate_human_review_time(pr_features)
    assert time_minutes == 240  # 上限4小时
```

- [ ] **Step 6: 运行测试验证失败**

Run: `PYTHONPATH=. pytest tests/unittest/test_estimation.py -k "estimate_human" -v`
Expected: FAIL - 函数不存在

- [ ] **Step 7: 实现时间估算算法**

```python
# pr_agent/monitoring/estimation.py

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
    language_time = max(0, (len(pr_features['languages']) - 1) * 3)
    
    total_time = base_time + file_time + line_time + complexity_time + language_time
    
    # 上限：4小时
    return min(total_time, 240)
```

- [ ] **Step 8: 运行测试验证通过**

Run: `PYTHONPATH=. pytest tests/unittest/test_estimation.py -k "estimate_human" -v`
Expected: PASS

- [ ] **Step 9: 编写API成本计算测试**

```python
# tests/unittest/test_estimation.py

def test_calculate_api_cost_gpt4():
    """测试GPT-4成本计算"""
    cost = calculate_api_cost('gpt-4', 1000, 500)
    expected = (1000 / 1000) * 0.03 + (500 / 1000) * 0.06
    assert abs(cost - expected) < 0.001


def test_calculate_api_cost_claude_opus():
    """测试Claude Opus成本计算"""
    cost = calculate_api_cost('claude-opus', 2000, 1000)
    expected = (2000 / 1000) * 0.015 + (1000 / 1000) * 0.075
    assert abs(cost - expected) < 0.001


def test_calculate_api_cost_unknown_model():
    """测试未知模型返回0"""
    cost = calculate_api_cost('unknown-model', 1000, 500)
    assert cost == 0.0
```

- [ ] **Step 10: 运行测试验证失败**

Run: `PYTHONPATH=. pytest tests/unittest/test_estimation.py -k "api_cost" -v`
Expected: FAIL - 函数不存在

- [ ] **Step 11: 实现API成本计算**

```python
# pr_agent/monitoring/estimation.py

def calculate_api_cost(model: str, tokens_prompt: int, tokens_completion: int) -> float:
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

- [ ] **Step 12: 运行测试验证通过**

Run: `PYTHONPATH=. pytest tests/unittest/test_estimation.py -v`
Expected: PASS - 所有测试通过

- [ ] **Step 13: 提交**

```bash
git add pr_agent/monitoring/estimation.py tests/unittest/test_estimation.py
git commit -m "feat: implement estimation algorithms for complexity, time, and cost"
```


### Task 3: EfficiencyTracker核心实现

**Files:**
- Create: `pr_agent/monitoring/efficiency_tracker.py`
- Test: `tests/unittest/test_efficiency_tracker.py`

- [ ] **Step 1: 编写EfficiencyTracker基础测试**

在tests/unittest/test_efficiency_tracker.py中编写测试，验证context manager功能和PR特征收集

- [ ] **Step 2: 运行测试验证失败**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_tracker.py -v`

- [ ] **Step 3: 实现EfficiencyTracker基础结构**

创建pr_agent/monitoring/efficiency_tracker.py，实现__init__, __enter__, __exit__方法和_collect_pr_features方法

- [ ] **Step 4: 运行测试验证通过**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_tracker.py -v`

- [ ] **Step 5: 编写追踪方法测试**

添加track_api_call, track_issues_found, track_code_suggestions等方法的测试

- [ ] **Step 6: 运行测试验证失败**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_tracker.py -k "track" -v`

- [ ] **Step 7: 实现追踪方法**

实现track_api_call, track_issues_found, track_code_suggestions, track_agentic_iteration, set_review_type, set_model等方法

- [ ] **Step 8: 运行测试验证通过**

Run: `PYTHONPATH=. pytest tests/unittest/test_efficiency_tracker.py -v`

- [ ] **Step 9: 提交**

```bash
git add pr_agent/monitoring/efficiency_tracker.py tests/unittest/test_efficiency_tracker.py
git commit -m "feat: implement EfficiencyTracker core functionality"
```


### Task 4: Prometheus指标集成

**Files:**
- Modify: `pr_agent/monitoring/metrics.py:280-350`
- Modify: `pr_agent/monitoring/efficiency_tracker.py:_update_prometheus`

- [ ] **Step 1: 在metrics.py中添加AI效率指标定义**

在PROMETHEUS_AVAILABLE条件块中添加Counter, Histogram, Gauge指标

- [ ] **Step 2: 实现EfficiencyTracker的_update_prometheus方法**

更新所有Prometheus指标：counters累加，histograms记录观测值，gauges设置当前值

- [ ] **Step 3: 手动测试Prometheus指标**

启动应用，执行review，访问/metrics端点验证指标存在

- [ ] **Step 4: 提交**

```bash
git add pr_agent/monitoring/metrics.py pr_agent/monitoring/efficiency_tracker.py
git commit -m "feat: add Prometheus metrics for AI efficiency tracking"
```

### Task 5: 配置系统

**Files:**
- Modify: `pr_agent/settings/configuration.toml`

- [ ] **Step 1: 添加efficiency_metrics配置节**

添加enabled, database_path, prometheus_enabled等配置项，以及estimation和pricing子节

- [ ] **Step 2: 更新estimation.py使用配置**

修改estimate_human_review_time和calculate_api_cost从配置读取参数

- [ ] **Step 3: 测试配置加载**

验证配置正确加载，默认值生效

- [ ] **Step 4: 提交**

```bash
git add pr_agent/settings/configuration.toml pr_agent/monitoring/estimation.py
git commit -m "feat: add configuration system for efficiency metrics"
```

### Task 6: PR Reviewer集成

**Files:**
- Modify: `pr_agent/tools/pr_reviewer.py:run`

- [ ] **Step 1: 在PRReviewer.run中集成EfficiencyTracker**

使用with语句包装review逻辑，设置review_type和model，追踪结果

- [ ] **Step 2: 处理配置开关**

检查efficiency_metrics.enabled配置，禁用时跳过追踪

- [ ] **Step 3: 端到端测试**

运行完整review流程，验证指标被收集和保存

- [ ] **Step 4: 提交**

```bash
git add pr_agent/tools/pr_reviewer.py
git commit -m "feat: integrate EfficiencyTracker into PR reviewer"
```

### Task 7: 文档和最终验证

**Files:**
- Create: `docs/efficiency-metrics.md`

- [ ] **Step 1: 编写使用文档**

说明如何启用/禁用指标收集，如何查询Prometheus，如何自定义配置

- [ ] **Step 2: 运行所有测试**

Run: `PYTHONPATH=. pytest tests/unittest -v`

- [ ] **Step 3: 运行lint检查**

Run: `ruff check .`

- [ ] **Step 4: 端到端验证**

执行完整review，检查数据库记录，验证Prometheus指标

- [ ] **Step 5: 最终提交**

```bash
git add docs/efficiency-metrics.md
git commit -m "docs: add efficiency metrics documentation"
```

---

## 自审检查清单

**规范覆盖:**
- [x] 数据库schema - Task 1
- [x] 估算算法 - Task 2
- [x] EfficiencyTracker - Task 3
- [x] Prometheus集成 - Task 4
- [x] 配置系统 - Task 5
- [x] PR Reviewer集成 - Task 6
- [x] 文档 - Task 7

**占位符扫描:**
- 无TBD或TODO
- 所有步骤都有具体操作

**类型一致性:**
- metrics字典字段名称在所有任务中保持一致
- 方法签名在定义和使用处匹配

