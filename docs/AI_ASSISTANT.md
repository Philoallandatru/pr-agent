# AI Assistant System

AI助手系统为代码审查提供智能对话和分析能力。

## 功能特性

### 1. 对话式交互
- 自然语言对话
- 上下文理解
- 多轮对话支持
- 会话历史管理

### 2. 代码解释
- 代码功能说明
- 关键概念提取
- 复杂度分析
- 潜在问题识别
- 改进建议

### 3. 审查建议
- 自动生成审查要点
- 代码质量检查
- 最佳实践建议
- 安全问题检测

### 4. 评论优化
- 改善评论语气
- 提高评论清晰度
- 增强建设性
- 专业化表达

## 快速开始

### 创建AI助手实例

```python
from pr_agent.ai_assistant import AIAssistant

assistant = AIAssistant()
```

### 对话交互

```python
# 开始对话
response = assistant.chat(
    conversation_id="conv-123",
    message="这段代码有什么问题？",
    context={"file": "main.py", "line": 42}
)

print(response.content)
print(f"置信度: {response.confidence}")
print(f"建议: {response.suggestions}")
```

### 代码解释

```python
code = """
def calculate_total(items):
    total = 0
    for item in items:
        total += item['price'] * item['quantity']
    return total
"""

explanation = assistant.explain_code(code, language="python")

print(f"说明: {explanation.explanation}")
print(f"关键概念: {explanation.key_concepts}")
print(f"复杂度: {explanation.complexity_analysis}")
print(f"潜在问题: {explanation.potential_issues}")
```

### 审查建议

```python
code = """
def process_user_data(data):
    user_id = data['id']
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return execute_query(query)
"""

suggestions = assistant.suggest_review_points(
    code=code,
    file_path="api/users.py"
)

for suggestion in suggestions:
    print(f"- {suggestion['point']}")
    print(f"  严重性: {suggestion['severity']}")
    print(f"  原因: {suggestion['reason']}")
```

### 评论优化

```python
comment = "这代码写的太烂了，完全不能用！"

optimization = assistant.optimize_review_comment(comment)

print(f"原始评论: {optimization.original_comment}")
print(f"优化后: {optimization.optimized_comment}")
print(f"改进点: {optimization.improvements}")
print(f"语气分数: {optimization.tone_score}")
print(f"清晰度: {optimization.clarity_score}")
```

## REST API

### 对话接口

**POST** `/api/assistant/chat`

请求体：
```json
{
  "conversation_id": "conv-123",
  "message": "这段代码有什么问题？",
  "context": {
    "file": "main.py",
    "line": 42
  }
}
```

响应：
```json
{
  "content": "这段代码存在以下问题...",
  "confidence": "high",
  "suggestions": [
    "建议添加错误处理",
    "考虑使用类型注解"
  ],
  "code_snippets": [
    {
      "language": "python",
      "code": "try:\n    ...\nexcept Exception as e:\n    ..."
    }
  ]
}
```

### 代码解释

**POST** `/api/assistant/explain`

请求体：
```json
{
  "code": "def calculate_total(items):\n    ...",
  "language": "python",
  "context": {}
}
```

响应：
```json
{
  "explanation": "这个函数计算商品总价...",
  "key_concepts": ["循环", "累加", "字典访问"],
  "complexity_analysis": {
    "cyclomatic_complexity": 2,
    "cognitive_complexity": 3,
    "lines_of_code": 5
  },
  "potential_issues": [
    {
      "type": "error_handling",
      "description": "缺少错误处理",
      "severity": "medium"
    }
  ],
  "improvement_suggestions": [
    "添加类型注解",
    "使用列表推导式"
  ]
}
```

### 评论优化

**POST** `/api/assistant/optimize`

请求体：
```json
{
  "comment": "这代码写的太烂了",
  "context": {}
}
```

响应：
```json
{
  "original_comment": "这代码写的太烂了",
  "optimized_comment": "建议改进代码结构，提高可读性和可维护性",
  "improvements": [
    "使用更专业的表达",
    "提供具体的改进建议",
    "保持建设性语气"
  ],
  "tone_score": 0.85,
  "clarity_score": 0.90
}
```

### 审查建议

**POST** `/api/assistant/suggest`

请求体：
```json
{
  "code": "def process_data(data): ...",
  "file_path": "api/processor.py",
  "context": {}
}
```

响应：
```json
{
  "suggestions": [
    {
      "point": "添加输入验证",
      "severity": "high",
      "reason": "缺少对输入数据的验证",
      "suggestion": "使用 isinstance() 检查数据类型"
    },
    {
      "point": "改进错误处理",
      "severity": "medium",
      "reason": "异常处理不够完善",
      "suggestion": "捕获特定异常类型"
    }
  ]
}
```

### 会话历史

**GET** `/api/assistant/conversations/{conversation_id}/history?limit=10`

响应：
```json
{
  "conversation_id": "conv-123",
  "messages": [
    {
      "role": "user",
      "content": "这段代码有什么问题？",
      "timestamp": "2024-01-15T10:30:00Z",
      "metadata": {}
    },
    {
      "role": "assistant",
      "content": "这段代码存在以下问题...",
      "timestamp": "2024-01-15T10:30:05Z",
      "metadata": {
        "confidence": "high"
      }
    }
  ]
}
```

### 清除会话

**DELETE** `/api/assistant/conversations/{conversation_id}`

响应：
```json
{
  "message": "Conversation cleared successfully"
}
```

## 配置选项

```toml
[ai_assistant]
# 最大对话历史长度
max_conversation_history = 50

# 代码复杂度阈值
complexity_threshold_low = 5
complexity_threshold_medium = 10
complexity_threshold_high = 20

# 评论优化阈值
min_tone_score = 0.7
min_clarity_score = 0.8

# 置信度阈值
confidence_threshold_high = 0.8
confidence_threshold_medium = 0.5
```

## 数据模型

### ConversationMessage
```python
@dataclass
class ConversationMessage:
    role: MessageRole  # USER, ASSISTANT, SYSTEM
    content: str
    timestamp: datetime
    metadata: Dict[str, Any]
```

### AssistantResponse
```python
@dataclass
class AssistantResponse:
    content: str
    confidence: ConfidenceLevel  # HIGH, MEDIUM, LOW
    suggestions: List[str]
    code_snippets: List[Dict[str, str]]
    metadata: Dict[str, Any]
```

### CodeExplanation
```python
@dataclass
class CodeExplanation:
    explanation: str
    key_concepts: List[str]
    complexity_analysis: Dict[str, Any]
    potential_issues: List[Dict[str, Any]]
    improvement_suggestions: List[str]
```

### CommentOptimization
```python
@dataclass
class CommentOptimization:
    original_comment: str
    optimized_comment: str
    improvements: List[str]
    tone_score: float  # 0.0 - 1.0
    clarity_score: float  # 0.0 - 1.0
```

## 最佳实践

### 1. 对话管理
- 为每个审查会话创建独立的conversation_id
- 定期清理长时间未使用的会话
- 限制会话历史长度避免内存溢出

### 2. 代码解释
- 提供足够的上下文信息
- 对大型代码块进行分段解释
- 关注关键逻辑和复杂部分

### 3. 审查建议
- 结合项目规范和最佳实践
- 优先关注高严重性问题
- 提供可操作的改进建议

### 4. 评论优化
- 保持专业和建设性
- 避免主观评价
- 提供具体的改进方向

## 扩展开发

### 自定义分析器

```python
from pr_agent.ai_assistant import AIAssistant

class CustomAssistant(AIAssistant):
    def analyze_security(self, code: str) -> List[Dict]:
        """自定义安全分析"""
        issues = []
        
        # 检查SQL注入
        if "execute(" in code and "+" in code:
            issues.append({
                "type": "sql_injection",
                "severity": "critical",
                "description": "可能存在SQL注入风险"
            })
        
        # 检查硬编码密钥
        if "password" in code.lower() and "=" in code:
            issues.append({
                "type": "hardcoded_secret",
                "severity": "high",
                "description": "检测到硬编码密钥"
            })
        
        return issues
```

### 集成外部AI服务

```python
import openai

class OpenAIAssistant(AIAssistant):
    def __init__(self, api_key: str):
        super().__init__()
        self.client = openai.OpenAI(api_key=api_key)
    
    def chat(self, conversation_id: str, message: str, 
             context: Optional[Dict] = None) -> AssistantResponse:
        """使用OpenAI API进行对话"""
        messages = self._get_conversation_messages(conversation_id)
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": m.role.value, "content": m.content}
                for m in messages
            ] + [{"role": "user", "content": message}]
        )
        
        content = response.choices[0].message.content
        
        return AssistantResponse(
            content=content,
            confidence=ConfidenceLevel.HIGH,
            suggestions=[],
            code_snippets=[],
            metadata={"model": "gpt-4"}
        )
```

## 性能优化

### 缓存策略
```python
from pr_agent.performance import MemoryCache

# 缓存代码解释结果
cache = MemoryCache(max_size=1000, strategy="lru")

@cache.cached(ttl=3600)
def explain_code_cached(code: str, language: str):
    return assistant.explain_code(code, language)
```

### 批处理
```python
# 批量处理审查建议
codes = [...]
suggestions_batch = []

for code in codes:
    suggestions = assistant.suggest_review_points(code, "file.py")
    suggestions_batch.append(suggestions)
```

## 故障排查

### 常见问题

1. **对话历史过长**
   - 症状：内存占用高，响应变慢
   - 解决：定期清理会话或限制历史长度

2. **代码解释不准确**
   - 症状：解释结果与实际不符
   - 解决：提供更多上下文信息，检查代码语法

3. **评论优化效果不佳**
   - 症状：优化后的评论仍不够专业
   - 解决：调整tone_score和clarity_score阈值

## 监控指标

- 对话响应时间
- 代码解释准确率
- 评论优化满意度
- API调用频率
- 错误率

## 安全考虑

- 不要在代码中包含敏感信息
- 限制单个会话的消息数量
- 实施速率限制防止滥用
- 定期审计AI助手的建议质量

## 相关文档

- [代码审查规则引擎](RULES_ENGINE.md)
- [质量评分系统](QUALITY_SCORING.md)
- [审查机器人](REVIEWER_BOT.md)
- [性能优化](PERFORMANCE_OPTIMIZATION.md)
