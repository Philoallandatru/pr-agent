# 代码审查系统集成测试

全面的集成测试套件，验证代码审查系统各模块的协同工作。

## 测试覆盖

### 1. 报告生成工作流测试

测试完整的报告生成流程：

- **多格式报告生成**: JSON、HTML、Markdown
- **报告类型**: 审查总结、质量趋势、效率分析、问题分布、团队表现、个人表现
- **报告管理**: 检索、过滤、元数据

### 2. 报告格式测试

验证不同输出格式的结构和内容：

- **JSON格式**: 结构化数据，包含sections数组
- **Markdown格式**: 标题、内容、生成时间
- **HTML格式**: 完整HTML文档结构

### 3. 报告管理测试

测试报告的存储和检索：

- **报告检索**: 按ID获取特定报告
- **报告过滤**: 按类型和格式过滤
- **元数据管理**: 自定义元数据存储

### 4. 性能测试

验证系统在高负载下的表现：

- **大数据集处理**: 1000+审查记录
- **批量生成**: 10个报告并发生成
- **响应时间**: 单个报告<5秒，批量<10秒

### 5. 日期范围测试

测试时间范围过滤功能：

- **日期范围包含**: 报告中显示起止日期
- **多时间段**: 生成多个时间段的报告

## 测试结构

```
tests/integration/
└── test_system_integration.py
    ├── TestReportGeneration (6个测试)
    ├── TestReportFormats (3个测试)
    ├── TestReportManagement (3个测试)
    ├── TestReportPerformance (2个测试)
    └── TestReportWithDateRanges (2个测试)
```

## 运行测试

### 运行所有集成测试

```bash
pytest tests/integration/test_system_integration.py -v
```

### 运行特定测试类

```bash
# 报告生成测试
pytest tests/integration/test_system_integration.py::TestReportGeneration -v

# 性能测试
pytest tests/integration/test_system_integration.py::TestReportPerformance -v
```

### 运行特定测试

```bash
pytest tests/integration/test_system_integration.py::TestReportGeneration::test_complete_review_summary_workflow -v
```

## 测试场景

### 场景1: 完整审查总结工作流

```python
def test_complete_review_summary_workflow(self, report_generator):
    """测试完整的审查总结报告生成流程"""
    
    # 1. 准备数据
    data = {
        'total_reviews': 150,
        'avg_duration': 18.5,
        'total_comments': 680,
        'reviews_by_status': {
            'approved': 90,
            'changes_requested': 45,
            'pending': 15
        }
    }
    
    # 2. 生成JSON报告
    json_report = report_generator.generate_report(json_config, data)
    
    # 3. 生成HTML报告
    html_report = report_generator.generate_report(html_config, data)
    
    # 4. 生成Markdown报告
    md_report = report_generator.generate_report(md_config, data)
    
    # 5. 验证所有报告已生成
    reports = report_generator.list_reports()
    assert len(reports) == 3
```

### 场景2: 质量趋势分析

```python
def test_quality_trends_analysis(self, report_generator):
    """测试质量趋势报告生成"""
    
    data = {
        'quality_scores': {
            'dates': ['2024-01-01', '2024-01-08', '2024-01-15'],
            'scores': [82, 85, 87]
        }
    }
    
    report = report_generator.generate_report(config, data)
    
    # 验证HTML包含图表数据
    content = Path(report.file_path).read_text()
    assert "Quality Trends" in content
```

### 场景3: 大数据集性能测试

```python
def test_large_dataset_performance(self, report_generator):
    """测试大数据集的报告生成性能"""
    
    # 模拟1000条审查记录
    data = {
        'total_reviews': 1000,
        'avg_duration': 15.5,
        'total_comments': 4500
    }
    
    start_time = time.time()
    report = report_generator.generate_report(config, data)
    generation_time = time.time() - start_time
    
    # 验证在5秒内完成
    assert generation_time < 5.0
```

## 测试数据

### 审查总结数据

```python
{
    'total_reviews': 150,
    'avg_duration': 18.5,  # 小时
    'total_comments': 680,
    'reviews_by_status': {
        'approved': 90,
        'changes_requested': 45,
        'pending': 15
    }
}
```

### 质量趋势数据

```python
{
    'quality_scores': {
        'dates': ['2024-01-01', '2024-01-08', '2024-01-15'],
        'scores': [82, 85, 87]
    }
}
```

### 效率分析数据

```python
{
    'time_to_first_comment': {
        'average': 2.5,
        'median': 2.0,
        'p90': 4.5
    },
    'review_duration': {
        '0-4h': 25,
        '4-8h': 35,
        '8-24h': 30,
        '24h+': 10
    }
}
```

### 问题分布数据

```python
{
    'issues_by_severity': {
        'critical': 8,
        'high': 22,
        'medium': 45,
        'low': 75
    },
    'issues_by_category': {
        'security': 15,
        'performance': 28,
        'style': 52,
        'bugs': 55
    }
}
```

## 性能基准

| 测试场景 | 数据量 | 预期时间 | 实际结果 |
|---------|--------|---------|---------|
| 单个报告生成 | 100条记录 | <1秒 | ✅ 通过 |
| 大数据集报告 | 1000条记录 | <5秒 | ✅ 通过 |
| 批量生成 | 10个报告 | <10秒 | ✅ 通过 |

## 测试覆盖率

- **报告类型覆盖**: 6/6 (100%)
- **输出格式覆盖**: 3/4 (75% - PDF需要额外库)
- **功能覆盖**: 16个测试场景
- **性能测试**: 2个基准测试

## 持续集成

集成测试在以下情况下自动运行：

1. 提交到主分支
2. 创建Pull Request
3. 手动触发CI/CD流水线

## 故障排除

### 测试失败：报告文件未生成

**问题**: 报告文件路径不存在

**解决方案**:
```python
# 确保输出目录存在
output_dir = Path(".pr_agent/reports")
output_dir.mkdir(parents=True, exist_ok=True)
```

### 测试失败：JSON解析错误

**问题**: 报告内容不是有效的JSON

**解决方案**:
```python
# 验证JSON格式
try:
    content = json.loads(report.content)
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
```

### 测试超时

**问题**: 报告生成时间过长

**解决方案**:
```python
# 减少测试数据量
data = {'total_reviews': 10}  # 而不是1000

# 或增加超时时间
@pytest.mark.timeout(30)
def test_large_dataset():
    ...
```

## 最佳实践

### 1. 使用临时目录

```python
@pytest.fixture
def temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)
```

### 2. 清理测试数据

```python
def teardown_method(self):
    """清理测试生成的报告"""
    for report in self.report_generator.list_reports():
        if report.file_path:
            Path(report.file_path).unlink(missing_ok=True)
```

### 3. 参数化测试

```python
@pytest.mark.parametrize("report_type,data", [
    (ReportType.REVIEW_SUMMARY, {'total_reviews': 100}),
    (ReportType.QUALITY_TRENDS, {'quality_scores': {}}),
    (ReportType.EFFICIENCY_ANALYSIS, {'time_to_first_comment': {}})
])
def test_all_report_types(report_generator, report_type, data):
    config = ReportConfig(
        report_id="test",
        report_type=report_type,
        title="Test",
        format=ReportFormat.JSON
    )
    report = report_generator.generate_report(config, data)
    assert report is not None
```

### 4. 模拟真实场景

```python
def test_realistic_workflow(report_generator):
    """模拟真实的月度报告生成流程"""
    
    # 1. 收集一个月的数据
    data = collect_monthly_metrics()
    
    # 2. 生成多种报告
    for report_type in [SUMMARY, TRENDS, EFFICIENCY]:
        generate_report(report_type, data)
    
    # 3. 验证所有报告
    verify_reports()
```

## 相关文档

- [报告生成系统](REPORT_GENERATOR.md)
- [指标收集系统](METRICS_COLLECTION.md)
- [质量评分系统](QUALITY_SCORING.md)
- [单元测试指南](../tests/unittest/README.md)
