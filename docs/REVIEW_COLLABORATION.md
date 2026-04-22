# 代码审查协作系统

代码审查协作系统提供团队协作功能，支持实时评论、任务管理、决策投票等功能。

## 功能特性

### 1. 审查会话管理
- 创建和管理审查会话
- 会话状态跟踪
- 参与者管理
- 会话统计

### 2. 评论系统
- 多种评论类型（问题、建议、讨论、表扬等）
- 线程化讨论
- 评论状态管理
- 表情反应

### 3. 任务管理
- 创建和分配任务
- 任务状态跟踪
- 优先级管理
- 截止日期提醒

### 4. 决策投票
- 提出决策
- 投票机制
- 自动决策确认
- 决策历史记录

### 5. 事件系统
- 实时事件通知
- 自定义事件处理器
- 事件历史记录

## 核心概念

### 审查会话 (ReviewSession)

审查会话是协作的基本单位，包含：
- 会话ID和PR信息
- 参与者列表
- 评论集合
- 任务列表
- 决策记录

### 参与者角色 (ParticipantRole)

- **AUTHOR**: 代码作者
- **REVIEWER**: 审查者
- **OBSERVER**: 观察者
- **MODERATOR**: 主持人

### 评论类型 (CommentType)

- **QUESTION**: 问题
- **SUGGESTION**: 建议
- **ISSUE**: 问题
- **PRAISE**: 表扬
- **DISCUSSION**: 讨论

### 评论状态 (CommentStatus)

- **OPEN**: 未解决
- **RESOLVED**: 已解决
- **WONT_FIX**: 不修复
- **DEFERRED**: 延期

### 任务状态 (TaskStatus)

- **TODO**: 待办
- **IN_PROGRESS**: 进行中
- **BLOCKED**: 阻塞
- **COMPLETED**: 已完成
- **CANCELLED**: 已取消

### 决策状态 (DecisionStatus)

- **PROPOSED**: 已提出
- **DISCUSSING**: 讨论中
- **APPROVED**: 已批准
- **REJECTED**: 已拒绝
- **DEFERRED**: 延期

## 使用示例

### Python API

```python
from pr_agent.review_collaboration import (
    get_collaboration_system,
    ParticipantRole,
    CommentType,
    TaskStatus,
)

# 获取协作系统实例
system = get_collaboration_system()

# 创建审查会话
session = system.create_session(
    session_id="session-1",
    pr_id="PR-123",
    repository="myorg/myrepo",
    title="Review PR-123: Add new feature",
    description="Reviewing the new authentication feature",
    creator_id="alice",
    creator_name="Alice"
)

# 添加参与者
system.add_participant(
    session_id="session-1",
    user_id="bob",
    username="Bob",
    role=ParticipantRole.REVIEWER
)

# 添加评论
comment = system.add_comment(
    session_id="session-1",
    comment_id="c1",
    author_id="bob",
    content="This function needs better error handling",
    comment_type=CommentType.SUGGESTION,
    file_path="auth.py",
    line_number=42
)

# 回复评论
reply = system.add_comment(
    session_id="session-1",
    comment_id="c2",
    author_id="alice",
    content="Good point, I'll add try-catch blocks",
    comment_type=CommentType.DISCUSSION,
    parent_id="c1"
)

# 添加表情反应
system.add_reaction("session-1", "c1", "charlie", "👍")

# 创建任务
task = system.create_task(
    session_id="session-1",
    task_id="t1",
    title="Add error handling",
    description="Add try-catch blocks to auth function",
    created_by="bob",
    assignee_id="alice",
    priority="high"
)

# 更新任务状态
system.update_task_status("session-1", "t1", TaskStatus.IN_PROGRESS)

# 提出决策
decision = system.propose_decision(
    session_id="session-1",
    decision_id="d1",
    title="Merge PR after fixes",
    description="Should we merge after error handling is added?",
    proposed_by="bob",
    required_approvals=2
)

# 投票
system.vote_decision("session-1", "d1", "alice", approve=True)
system.vote_decision("session-1", "d1", "charlie", approve=True)

# 获取会话统计
stats = system.get_session_stats("session-1")
print(f"Participants: {stats['participants']}")
print(f"Open comments: {stats['open_comments']}")
print(f"Pending tasks: {stats['pending_tasks']}")

# 获取评论线程
thread = system.get_comment_thread("session-1", "c1")
for comment in thread:
    print(f"{comment.author_id}: {comment.content}")
```

### REST API

#### 创建审查会话

```bash
POST /api/review-collaboration/sessions
Content-Type: application/json

{
  "session_id": "session-1",
  "pr_id": "PR-123",
  "repository": "myorg/myrepo",
  "title": "Review PR-123",
  "description": "Reviewing new feature"
}
```

#### 添加参与者

```bash
POST /api/review-collaboration/sessions/session-1/participants
Content-Type: application/json

{
  "user_id": "bob",
  "username": "Bob",
  "role": "REVIEWER"
}
```

#### 添加评论

```bash
POST /api/review-collaboration/sessions/session-1/comments
Content-Type: application/json

{
  "comment_id": "c1",
  "author_id": "bob",
  "content": "This needs improvement",
  "comment_type": "SUGGESTION",
  "file_path": "auth.py",
  "line_number": 42
}
```

#### 解决评论

```bash
POST /api/review-collaboration/sessions/session-1/comments/c1/resolve
Content-Type: application/json

{
  "resolved_by": "alice"
}
```

#### 添加表情反应

```bash
POST /api/review-collaboration/sessions/session-1/comments/c1/reactions
Content-Type: application/json

{
  "user_id": "charlie",
  "emoji": "👍"
}
```

#### 创建任务

```bash
POST /api/review-collaboration/sessions/session-1/tasks
Content-Type: application/json

{
  "task_id": "t1",
  "title": "Add error handling",
  "description": "Add try-catch blocks",
  "created_by": "bob",
  "assignee_id": "alice",
  "priority": "high"
}
```

#### 更新任务状态

```bash
PUT /api/review-collaboration/sessions/session-1/tasks/t1
Content-Type: application/json

{
  "status": "IN_PROGRESS"
}
```

#### 提出决策

```bash
POST /api/review-collaboration/sessions/session-1/decisions
Content-Type: application/json

{
  "decision_id": "d1",
  "title": "Merge PR",
  "description": "Should we merge?",
  "proposed_by": "bob",
  "required_approvals": 2
}
```

#### 投票决策

```bash
POST /api/review-collaboration/sessions/session-1/decisions/d1/vote
Content-Type: application/json

{
  "user_id": "alice",
  "approve": true
}
```

#### 获取会话统计

```bash
GET /api/review-collaboration/sessions/session-1/stats
```

响应：
```json
{
  "session_id": "session-1",
  "participants": 3,
  "online_participants": 2,
  "total_comments": 5,
  "open_comments": 2,
  "resolved_comments": 3,
  "total_tasks": 3,
  "pending_tasks": 1,
  "completed_tasks": 2,
  "total_decisions": 1,
  "pending_decisions": 0,
  "is_active": true
}
```

## 事件处理

### 注册事件处理器

```python
def on_comment_added(session, comment):
    print(f"New comment in {session.session_id}: {comment.content}")

def on_task_completed(session, task):
    print(f"Task completed: {task.title}")

system = get_collaboration_system()
system.on_event("comment_added", on_comment_added)
system.on_event("task_completed", on_task_completed)
```

### 可用事件类型

- `session_created`: 会话创建
- `participant_joined`: 参与者加入
- `comment_added`: 评论添加
- `comment_resolved`: 评论解决
- `task_created`: 任务创建
- `task_completed`: 任务完成
- `decision_proposed`: 决策提出
- `decision_finalized`: 决策确认

## 数据持久化

会话数据自动保存到本地存储：

```
~/.pr_agent/collaboration/
  ├── session-1.json
  ├── session-2.json
  └── ...
```

### 加载已保存的会话

```python
system = get_collaboration_system()
session = system.load_session("session-1")
```

## 最佳实践

### 1. 会话管理

- 为每个PR创建独立的审查会话
- 使用有意义的会话ID（如 `pr-123-review`）
- 及时结束已完成的会话

### 2. 评论组织

- 使用合适的评论类型
- 利用线程化讨论保持上下文
- 及时解决已处理的评论

### 3. 任务跟踪

- 为重要的修改创建任务
- 设置合理的优先级
- 指定明确的负责人

### 4. 决策管理

- 对重要决策使用投票机制
- 设置合理的批准人数
- 记录决策理由

### 5. 团队协作

- 明确参与者角色
- 保持活跃参与
- 使用表情反应快速反馈

## 配置

在 `configuration.toml` 中配置协作系统：

```toml
[review_collaboration]
# 存储路径
storage_path = "~/.pr_agent/collaboration"

# 会话设置
max_participants = 20
auto_save = true

# 评论设置
max_thread_depth = 10
enable_reactions = true

# 任务设置
default_priority = "normal"
enable_due_dates = true

# 决策设置
default_required_approvals = 1
enable_anonymous_voting = false
```

## 故障排除

### 会话未找到

确保会话ID正确，并且会话已创建：

```python
session = system.sessions.get(session_id)
if not session:
    session = system.load_session(session_id)
```

### 评论线程不完整

检查父评论ID是否正确：

```python
thread = system.get_comment_thread(session_id, comment_id)
print(f"Thread has {len(thread)} comments")
```

### 决策未自动确认

检查投票数是否达到要求：

```python
decision = session.decisions[decision_id]
approvals = sum(1 for v in decision.votes.values() if v)
print(f"Approvals: {approvals}/{decision.required_approvals}")
```

## 性能优化

### 大型会话

对于评论和任务较多的会话：

- 使用分页加载评论
- 按状态过滤任务
- 定期归档已完成的会话

### 实时更新

使用事件处理器实现实时更新：

```python
def on_any_event(*args):
    # 通知前端更新
    notify_frontend()

for event_type in system.event_handlers.keys():
    system.on_event(event_type, on_any_event)
```

## 安全考虑

- 验证用户权限
- 限制会话访问
- 审计重要操作
- 防止恶意评论

## 集成示例

### 与Bitbucket集成

```python
# 监听PR事件
def on_pr_created(pr_data):
    system = get_collaboration_system()
    session = system.create_session(
        session_id=f"pr-{pr_data['id']}",
        pr_id=pr_data['id'],
        repository=pr_data['repository'],
        title=f"Review {pr_data['title']}"
    )
```

### 与Slack集成

```python
# 发送通知到Slack
def on_comment_added(session, comment):
    send_slack_message(
        channel="#code-reviews",
        text=f"New comment in {session.title}: {comment.content}"
    )

system.on_event("comment_added", on_comment_added)
```

## 相关文档

- [实时协作系统](COLLABORATION.md)
- [通知系统](WEBHOOK_NOTIFICATIONS.md)
- [审查工作流](WORKFLOW.md)
