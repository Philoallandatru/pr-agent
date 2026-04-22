# 智能代码审查建议系统

智能代码审查建议引擎基于静态代码分析，提供上下文感知的代码改进建议，包括重构、性能优化和可读性改进。

## 功能特性

### 建议类型

1. **重构建议 (Refactoring)**
   - 检测重复代码
   - 识别过长函数
   - 发现深层嵌套
   - 建议代码结构改进

2. **性能优化 (Performance)**
   - 检测低效循环
   - 识别重复计算
   - 建议使用列表推导式
   - 循环不变量提升

3. **可读性改进 (Readability)**
   - 检测魔法数字
   - 识别不清晰的变量名
   - 建议使用命名常量
   - 改进代码命名

4. **最佳实践 (Best Practice)**
   - Python 编码规范
   - 设计模式建议
   - 代码组织优化

5. **安全改进 (Security)**
   - 识别潜在安全问题
   - 建议安全编码实践

### 优先级级别

- **CRITICAL**: 严重问题，需要立即处理
- **HIGH**: 高优先级，应尽快处理
- **MEDIUM**: 中等优先级，建议处理
- **LOW**: 低优先级，可选处理

## 使用方法

### Python API

```python
from pr_agent.suggestions import get_suggestion_engine, SuggestionType

# 获取建议引擎
engine = get_suggestion_engine()

# 分析单个文件
suggestions = engine.analyze_file("path/to/file.py")

# 分析特定类型的建议
suggestions = engine.analyze_file(
    "path/to/file.py",
    suggestion_types=[SuggestionType.PERFORMANCE, SuggestionType.REFACTORING]
)

# 分析整个目录
results = engine.analyze_directory("path/to/directory")

# 生成报告
report = engine.generate_report(results)
print(f"Total suggestions: {report['total_suggestions']}")
print(f"Files analyzed: {report['files_analyzed']}")
```

### REST API

#### 分析代码并生成建议

```bash
POST /api/suggestions/analyze
Authorization: Bearer <token>

{
  "file_paths": [
    "/path/to/file1.py",
    "/path/to/file2.py"
  ],
  "suggestion_types": ["refactoring", "performance"]
}
```

响应：

```json
{
  "total_suggestions": 5,
  "files_analyzed": 2,
  "suggestions": [
    {
      "type": "refactoring",
      "priority": "high",
      "title": "函数过长",
      "description": "函数 process_data 有 65 行代码",
      "file_path": "/path/to/file1.py",
      "line_number": 10,
      "original_code": "def process_data(...): # 65 lines",
      "suggested_code": "将函数拆分为多个小函数，每个函数专注于单一职责",
      "reasoning": "长函数难以理解和维护，建议拆分为多个小函数",
      "tags": ["long-function", "refactoring"]
    }
  ]
}
```

#### 获取可用建议类型

```bash
GET /api/suggestions/types
Authorization: Bearer <token>
```

响应：

```json
{
  "types": [
    {
      "value": "refactoring",
      "name": "REFACTORING",
      "description": "Code refactoring suggestions"
    },
    {
      "value": "performance",
      "name": "PERFORMANCE",
      "description": "Performance optimization suggestions"
    }
  ]
}
```

## 分析器详解

### 重构分析器 (RefactoringAnalyzer)

检测代码结构问题：

- **重复代码检测**: 识别相似度超过 80% 的函数
- **长函数检测**: 标记超过 50 行的函数
- **深层嵌套检测**: 识别嵌套层级超过 4 层的代码

### 性能分析器 (PerformanceAnalyzer)

识别性能瓶颈：

- **低效循环**: 检测可以用列表推导式替代的循环
- **重复计算**: 识别循环中的不变计算
- **算法优化**: 建议更高效的算法实现

### 可读性分析器 (ReadabilityAnalyzer)

改进代码可读性：

- **魔法数字**: 检测未命名的常量
- **不清晰命名**: 识别 x, y, tmp 等不具描述性的变量名
- **代码格式**: 检查代码风格一致性

## 配置示例

### 自定义分析器

```python
from pr_agent.suggestions import SuggestionEngine
from pr_agent.suggestions.engine import RefactoringAnalyzer

# 创建自定义引擎
engine = SuggestionEngine()

# 只使用重构分析器
suggestions = engine.refactoring_analyzer.analyze("file.py")
```

### 过滤建议

```python
# 只获取高优先级建议
high_priority = [
    s for s in suggestions 
    if s.priority == SuggestionPriority.HIGH
]

# 按类型分组
by_type = {}
for suggestion in suggestions:
    type_name = suggestion.type.value
    if type_name not in by_type:
        by_type[type_name] = []
    by_type[type_name].append(suggestion)
```

## 集成到 PR 审查流程

### 自动建议生成

```python
from pr_agent.suggestions import get_suggestion_engine
from pr_agent.git_providers import get_git_provider

# 获取 PR 变更的文件
git_provider = get_git_provider()
changed_files = git_provider.get_diff_files()

# 分析变更文件
engine = get_suggestion_engine()
suggestions = []
for file_path in changed_files:
    if file_path.endswith('.py'):
        file_suggestions = engine.analyze_file(file_path)
        suggestions.extend(file_suggestions)

# 发布建议到 PR 评论
for suggestion in suggestions:
    if suggestion.priority in [SuggestionPriority.HIGH, SuggestionPriority.CRITICAL]:
        git_provider.publish_comment(
            f"**{suggestion.title}** ({suggestion.priority.value})\n\n"
            f"{suggestion.description}\n\n"
            f"```python\n{suggestion.suggested_code}\n```\n\n"
            f"*Reasoning*: {suggestion.reasoning}"
        )
```

## 最佳实践

### 1. 选择性分析

不是所有建议都需要立即处理，根据优先级和项目需求选择：

```python
# 只关注高优先级的重构和性能建议
suggestions = engine.analyze_file(
    "file.py",
    suggestion_types=[SuggestionType.REFACTORING, SuggestionType.PERFORMANCE]
)

critical_suggestions = [
    s for s in suggestions 
    if s.priority in [SuggestionPriority.HIGH, SuggestionPriority.CRITICAL]
]
```

### 2. 批量分析

对于大型项目，使用目录分析：

```python
# 分析整个项目
results = engine.analyze_directory("src/")

# 生成汇总报告
report = engine.generate_report(results)

# 按优先级排序
all_suggestions = []
for file_suggestions in results.values():
    all_suggestions.extend(file_suggestions)

sorted_suggestions = sorted(
    all_suggestions,
    key=lambda s: ["low", "medium", "high", "critical"].index(s.priority.value),
    reverse=True
)
```

### 3. 持续改进

将建议系统集成到 CI/CD 流程：

```yaml
# .github/workflows/code-suggestions.yml
name: Code Suggestions

on: [pull_request]

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Analyze code
        run: |
          python -m pr_agent.suggestions analyze \
            --files $(git diff --name-only origin/main...HEAD | grep '\.py$') \
            --types refactoring performance \
            --min-priority high
```

## 扩展建议引擎

### 添加自定义分析器

```python
from pr_agent.suggestions.engine import CodeSuggestion, SuggestionType, SuggestionPriority
import ast

class CustomAnalyzer:
    """自定义分析器"""
    
    def analyze(self, file_path: str) -> List[CodeSuggestion]:
        suggestions = []
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        
        # 自定义检测逻辑
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # 检测特定模式
                if self._check_pattern(node):
                    suggestions.append(CodeSuggestion(
                        type=SuggestionType.BEST_PRACTICE,
                        priority=SuggestionPriority.MEDIUM,
                        title="自定义建议",
                        description="检测到特定模式",
                        file_path=file_path,
                        line_number=node.lineno,
                        original_code=ast.unparse(node),
                        suggested_code="改进后的代码",
                        reasoning="改进原因",
                        tags=["custom"]
                    ))
        
        return suggestions
    
    def _check_pattern(self, node):
        # 实现自定义检测逻辑
        return False

# 集成到引擎
engine = SuggestionEngine()
engine.custom_analyzer = CustomAnalyzer()
```

## 性能考虑

- **文件大小**: 建议引擎对大文件（>10000 行）可能较慢
- **并行处理**: 目录分析可以并行化以提高性能
- **缓存**: 对于未修改的文件，可以缓存分析结果

## 限制

- 当前仅支持 Python 代码分析
- 基于静态分析，无法检测运行时问题
- 某些复杂模式可能产生误报

## 故障排除

### 问题：分析器返回空结果

**解决方案**:
- 检查文件路径是否正确
- 确认文件是有效的 Python 代码
- 验证文件不为空

### 问题：建议过多

**解决方案**:
- 使用 `suggestion_types` 参数过滤类型
- 只关注高优先级建议
- 调整分析器阈值

### 问题：性能慢

**解决方案**:
- 减少分析的文件数量
- 使用并行处理
- 缓存分析结果

## 相关文档

- [质量门禁系统](QUALITY_GATE.md)
- [代码审查流程](../README.md)
- [API 文档](API_REFERENCE.md)
