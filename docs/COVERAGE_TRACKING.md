# 代码覆盖率追踪系统

代码覆盖率追踪系统集成 coverage.py 和 pytest-cov，提供自动化的测试覆盖率分析、趋势追踪和可视化报告。

## 功能特性

### 核心功能

1. **覆盖率测量**
   - 行覆盖率（Line Coverage）
   - 分支覆盖率（Branch Coverage）
   - 文件级别覆盖率详情
   - 缺失行号追踪

2. **趋势分析**
   - 历史覆盖率追踪
   - 7天/30天变化趋势
   - 覆盖率改进/下降检测
   - 时间序列数据存储

3. **质量评估**
   - 自动状态分级（Excellent/Good/Fair/Poor）
   - 低覆盖率文件识别
   - 覆盖率阈值检查
   - 质量门禁集成

4. **报告生成**
   - XML/JSON/HTML 格式支持
   - 覆盖率摘要统计
   - 文件级别详细报告
   - 缺失行号列表

## 覆盖率状态分级

| 状态 | 覆盖率范围 | 描述 |
|------|-----------|------|
| Excellent | ≥ 90% | 优秀的测试覆盖 |
| Good | 80% - 89% | 良好的测试覆盖 |
| Fair | 70% - 79% | 一般的测试覆盖 |
| Poor | < 70% | 需要改进的测试覆盖 |

## 使用方法

### Python API

#### 基本使用

```python
from pr_agent.coverage import get_coverage_tracker

# 获取覆盖率追踪器
tracker = get_coverage_tracker("/path/to/project")

# 运行测试并收集覆盖率
report = tracker.run_coverage(
    test_command="pytest tests/",
    source_dirs=["pr_agent"]
)

# 查看覆盖率结果
print(f"Line Coverage: {report.line_coverage_percent:.2f}%")
print(f"Branch Coverage: {report.branch_coverage_percent:.2f}%")
print(f"Status: {report.status.value}")
```

#### 解析现有覆盖率报告

```python
# 解析 coverage.xml 文件
report = tracker.parse_coverage_xml("coverage.xml")

# 访问文件级别覆盖率
for file_path, file_cov in report.files.items():
    print(f"{file_path}: {file_cov.line_coverage_percent:.2f}%")
    if file_cov.missing_lines:
        print(f"  Missing lines: {file_cov.missing_lines}")
```

#### 获取特定文件覆盖率

```python
# 获取单个文件的覆盖率
file_cov = tracker.get_file_coverage("pr_agent/algo/token_handler.py")

if file_cov:
    print(f"Line Coverage: {file_cov.line_coverage_percent:.2f}%")
    print(f"Branch Coverage: {file_cov.branch_coverage_percent:.2f}%")
    print(f"Missing Lines: {file_cov.missing_lines}")
```

#### 趋势分析

```python
# 获取 30 天覆盖率趋势
trend = tracker.get_trend(days=30)

# 查看变化
line_change_7d, branch_change_7d = trend.get_change(7)
print(f"7-day change: {line_change_7d:+.2f}% (line), {branch_change_7d:+.2f}% (branch)")

# 绘制趋势图
import matplotlib.pyplot as plt

plt.plot(trend.timestamps, [r * 100 for r in trend.line_rates], label="Line Coverage")
plt.plot(trend.timestamps, [r * 100 for r in trend.branch_rates], label="Branch Coverage")
plt.xlabel("Time")
plt.ylabel("Coverage %")
plt.legend()
plt.show()
```

#### 识别低覆盖率文件

```python
# 获取覆盖率低于 70% 的文件
low_coverage = tracker.get_low_coverage_files(threshold=70.0)

for file_cov in low_coverage:
    print(f"{file_cov.file_path}: {file_cov.line_coverage_percent:.2f}%")
    print(f"  Missing {len(file_cov.missing_lines)} lines")
```

#### 生成覆盖率摘要

```python
# 生成完整摘要
summary = tracker.generate_summary()

print(f"Status: {summary['status']}")
print(f"Line Coverage: {summary['line_coverage']['percent']:.2f}%")
print(f"7-day Change: {summary['line_coverage']['change_7d']:+.2f}%")
print(f"Low Coverage Files: {summary['files']['low_coverage']}")

# 显示最需要改进的文件
for file_info in summary['low_coverage_files']:
    print(f"  {file_info['path']}: {file_info['coverage']:.2f}%")
```

### 命令行使用

#### 运行覆盖率测试

```bash
# 使用默认配置
python -m pr_agent.coverage.tracker

# 指定测试命令
python -m pr_agent.coverage.tracker --test-command "pytest tests/unit"

# 指定源目录
python -m pr_agent.coverage.tracker --source pr_agent --source tests
```

#### 查看覆盖率报告

```bash
# 生成 HTML 报告
coverage html

# 在浏览器中打开
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### 集成到 CI/CD

#### GitHub Actions

```yaml
name: Coverage

on: [push, pull_request]

jobs:
  coverage:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install coverage pytest pytest-cov
      
      - name: Run coverage
        run: |
          python -c "
          from pr_agent.coverage import get_coverage_tracker
          tracker = get_coverage_tracker('.')
          report = tracker.run_coverage()
          summary = tracker.generate_summary()
          print(f\"Coverage: {summary['line_coverage']['percent']:.2f}%\")
          if summary['line_coverage']['percent'] < 80:
              exit(1)
          "
      
      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          files: .coverage_data/coverage.xml
```

#### 质量门禁集成

```python
from pr_agent.coverage import get_coverage_tracker
from pr_agent.quality import get_quality_gate

# 运行覆盖率
tracker = get_coverage_tracker(".")
report = tracker.run_coverage()

# 集成到质量门禁
quality_gate = get_quality_gate()

# 添加覆盖率检查
if report.line_coverage_percent < 80:
    quality_gate.add_issue(
        check_type="coverage",
        severity="error",
        message=f"Line coverage {report.line_coverage_percent:.2f}% is below 80%",
        file_path="",
        line_number=0
    )

# 检查低覆盖率文件
low_coverage = tracker.get_low_coverage_files(70.0)
for file_cov in low_coverage:
    quality_gate.add_issue(
        check_type="coverage",
        severity="warning",
        message=f"Low coverage: {file_cov.line_coverage_percent:.2f}%",
        file_path=file_cov.file_path,
        line_number=0
    )
```

## 配置

### 配置文件

在 `configuration.toml` 中添加覆盖率配置：

```toml
[coverage]
# 项目根目录
project_root = "."

# 存储目录
storage_dir = ".coverage_data"

# 覆盖率阈值
line_threshold = 80.0
branch_threshold = 75.0

# 测试命令
test_command = "pytest tests/"

# 源目录
source_dirs = ["pr_agent"]

# 排除模式
exclude_patterns = [
    "*/tests/*",
    "*/migrations/*",
    "*/__pycache__/*"
]
```

### .coveragerc 配置

创建 `.coveragerc` 文件配置 coverage.py：

```ini
[run]
source = pr_agent
omit =
    */tests/*
    */migrations/*
    */__pycache__/*
    */venv/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov

[xml]
output = coverage.xml
```

## 数据模型

### FileCoverage

```python
@dataclass
class FileCoverage:
    file_path: str
    line_rate: float  # 0.0 - 1.0
    branch_rate: float  # 0.0 - 1.0
    lines_covered: int
    lines_valid: int
    branches_covered: int
    branches_valid: int
    missing_lines: List[int]
```

### CoverageReport

```python
@dataclass
class CoverageReport:
    timestamp: float
    line_rate: float
    branch_rate: float
    lines_covered: int
    lines_valid: int
    branches_covered: int
    branches_valid: int
    files: Dict[str, FileCoverage]
```

### CoverageTrend

```python
@dataclass
class CoverageTrend:
    timestamps: List[float]
    line_rates: List[float]
    branch_rates: List[float]
```

## 存储格式

### 历史数据

覆盖率历史存储在 `.coverage_data/history.json`：

```json
{
  "timestamps": [1640000000.0, 1640086400.0],
  "line_rates": [0.85, 0.87],
  "branch_rates": [0.75, 0.78]
}
```

### 报告数据

每个报告存储在 `.coverage_data/report_{timestamp}.json`：

```json
{
  "timestamp": 1640000000.0,
  "line_rate": 0.85,
  "branch_rate": 0.75,
  "lines_covered": 850,
  "lines_valid": 1000,
  "branches_covered": 150,
  "branches_valid": 200,
  "files": {
    "pr_agent/algo/token_handler.py": {
      "file_path": "pr_agent/algo/token_handler.py",
      "line_rate": 0.90,
      "branch_rate": 0.80,
      "lines_covered": 90,
      "lines_valid": 100,
      "branches_covered": 16,
      "branches_valid": 20,
      "missing_lines": [42, 55, 78]
    }
  }
}
```

## 最佳实践

### 1. 设置合理的覆盖率目标

```python
# 不同类型代码的推荐覆盖率
COVERAGE_TARGETS = {
    "core_logic": 90,      # 核心业务逻辑
    "api_handlers": 85,    # API 处理器
    "utilities": 80,       # 工具函数
    "ui_components": 70,   # UI 组件
}
```

### 2. 定期监控趋势

```python
# 每周检查覆盖率变化
trend = tracker.get_trend(days=7)
line_change, branch_change = trend.get_change(7)

if line_change < -5:  # 下降超过 5%
    send_alert(f"Coverage dropped by {abs(line_change):.2f}%")
```

### 3. 优先改进低覆盖率文件

```python
# 按覆盖率排序，优先处理最低的
low_coverage = tracker.get_low_coverage_files(80.0)
sorted_files = sorted(low_coverage, key=lambda x: x.line_coverage_percent)

for file_cov in sorted_files[:5]:  # 前 5 个最需要改进的
    print(f"TODO: Add tests for {file_cov.file_path}")
```

### 4. 在 PR 中显示覆盖率变化

```python
# 比较 PR 前后的覆盖率
before_report = tracker._load_report(before_timestamp)
after_report = tracker.run_coverage()

coverage_diff = after_report.line_coverage_percent - before_report.line_coverage_percent

pr_comment = f"""
## Coverage Report

- Line Coverage: {after_report.line_coverage_percent:.2f}% ({coverage_diff:+.2f}%)
- Branch Coverage: {after_report.branch_coverage_percent:.2f}%
- Status: {after_report.status.value}
"""
```

## 故障排除

### 问题：coverage.py 未安装

**解决方案**:
```bash
pip install coverage pytest-cov
```

### 问题：XML 报告解析失败

**解决方案**:
- 确认 coverage.xml 文件存在
- 检查 XML 格式是否正确
- 使用 `coverage xml` 重新生成报告

### 问题：覆盖率数据不准确

**解决方案**:
- 清除旧的 .coverage 文件：`coverage erase`
- 确认源目录配置正确
- 检查 .coveragerc 的 omit 配置

### 问题：趋势数据丢失

**解决方案**:
- 检查 `.coverage_data/` 目录权限
- 确认 history.json 文件未被删除
- 备份覆盖率数据到版本控制之外

## 扩展功能

### 自定义覆盖率检查器

```python
class CustomCoverageChecker:
    def __init__(self, tracker):
        self.tracker = tracker
    
    def check_critical_files(self, critical_files, threshold=95.0):
        """检查关键文件的覆盖率"""
        issues = []
        
        for file_path in critical_files:
            file_cov = self.tracker.get_file_coverage(file_path)
            if file_cov and file_cov.line_coverage_percent < threshold:
                issues.append({
                    "file": file_path,
                    "coverage": file_cov.line_coverage_percent,
                    "threshold": threshold
                })
        
        return issues
```

### 覆盖率徽章生成

```python
def generate_coverage_badge(coverage_percent):
    """生成覆盖率徽章 URL"""
    color = "red"
    if coverage_percent >= 90:
        color = "brightgreen"
    elif coverage_percent >= 80:
        color = "green"
    elif coverage_percent >= 70:
        color = "yellow"
    
    return f"https://img.shields.io/badge/coverage-{coverage_percent:.0f}%25-{color}"
```

## 相关文档

- [质量门禁系统](QUALITY_GATE.md)
- [CI/CD 配置](CI_CD.md)
- [测试最佳实践](../tests/README.md)
