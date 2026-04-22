# 实时协作系统

实时协作系统为 PR 代码审查提供 WebSocket 驱动的多用户协作功能，包括实时光标跟踪、评论、注释和在线状态管理。

## 功能特性

### 核心功能

1. **多用户会话**
   - 创建 PR 专属协作房间
   - 实时用户在线状态
   - 用户加入/离开通知
   - 活跃用户列表

2. **实时光标跟踪**
   - 显示其他用户的光标位置
   - 文件切换同步
   - 光标位置实时更新

3. **协作评论**
   - 添加行级评论
   - 评论回复（嵌套评论）
   - 编辑和删除评论
   - 评论解决状态

4. **代码注释**
   - 高亮代码区域
   - 自定义颜色标记
   - 添加注释标签
   - 实时同步注释

5. **在线状态管理**
   - Active（活跃）
   - Idle（空闲）
   - Away（离开）
   - 自动状态检测

## 架构设计

### 组件结构

```
pr_agent/collaboration/
├── __init__.py          # 模块导出
├── room.py              # 协作房间核心逻辑
└── websocket.py         # WebSocket 处理器
```

### 数据模型

#### User（用户）
```python
@dataclass
class User:
    id: str
    name: str
    email: str
    avatar_url: Optional[str]
    status: UserStatus
    last_seen: float
    current_file: Optional[str]
    cursor_position: Optional[Dict[str, int]]
```

#### Comment（评论）
```python
@dataclass
class Comment:
    id: str
    user_id: str
    file_path: str
    line_number: int
    content: str
    created_at: float
    updated_at: Optional[float]
    resolved: bool
    replies: List[Comment]
```

#### Annotation（注释）
```python
@dataclass
class Annotation:
    id: str
    user_id: str
    file_path: str
    start_line: int
    end_line: int
    start_column: int
    end_column: int
    color: str
    label: Optional[str]
```

## 使用方法

### REST API

#### 创建协作房间

```bash
POST /api/collaboration/rooms
Authorization: Bearer <token>

{
  "pr_number": 123,
  "repository": "owner/repo"
}
```

响应：
```json
{
  "room_id": "owner/repo:123:abc123",
  "pr_number": 123,
  "repository": "owner/repo",
  "created_at": 1640000000.0
}
```

#### 获取房间详情

```bash
GET /api/collaboration/rooms/{room_id}
Authorization: Bearer <token>
```

响应：
```json
{
  "room_id": "owner/repo:123:abc123",
  "pr_number": 123,
  "repository": "owner/repo",
  "created_at": 1640000000.0,
  "active_users": [
    {
      "id": "user1",
      "name": "Alice",
      "email": "alice@example.com",
      "status": "active",
      "current_file": "src/main.py",
      "cursor_position": {"line": 42, "column": 10}
    }
  ],
  "comment_count": 5,
  "annotation_count": 2
}
```

#### 获取房间评论

```bash
GET /api/collaboration/rooms/{room_id}/comments?file_path=src/main.py
Authorization: Bearer <token>
```

### WebSocket API

#### 连接到协作房间

```javascript
const ws = new WebSocket(
  `ws://localhost:8080/ws/collaboration/${roomId}?user_id=${userId}&user_name=${userName}&user_email=${userEmail}`
);

ws.onopen = () => {
  console.log('Connected to collaboration room');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleCollaborationEvent(message);
};
```

#### 发送光标移动

```javascript
ws.send(JSON.stringify({
  type: 'cursor_move',
  file_path: 'src/main.py',
  line: 42,
  column: 10
}));
```

#### 添加评论

```javascript
ws.send(JSON.stringify({
  type: 'add_comment',
  file_path: 'src/main.py',
  line_number: 42,
  content: 'This needs refactoring',
  parent_id: null  // 或父评论 ID
}));
```

#### 添加代码注释

```javascript
ws.send(JSON.stringify({
  type: 'add_annotation',
  file_path: 'src/main.py',
  start_line: 40,
  end_line: 45,
  start_column: 0,
  end_column: 20,
  color: '#ffff00',
  label: 'Review this'
}));
```

#### 更新在线状态

```javascript
ws.send(JSON.stringify({
  type: 'update_presence',
  status: 'away'  // active, idle, away
}));
```

### 事件类型

#### 接收的事件

1. **room_state** - 房间初始状态
   ```json
   {
     "type": "room_state",
     "data": {
       "room_id": "...",
       "users": [...],
       "comments": [...],
       "annotations": [...]
     }
   }
   ```

2. **user_joined** - 用户加入
   ```json
   {
     "type": "user_joined",
     "user_id": "user2",
     "timestamp": 1640000000.0,
     "data": {
       "user": {
         "id": "user2",
         "name": "Bob",
         "email": "bob@example.com",
         "status": "active"
       }
     }
   }
   ```

3. **user_left** - 用户离开
   ```json
   {
     "type": "user_left",
     "user_id": "user2",
     "timestamp": 1640000000.0,
     "data": {"user_id": "user2"}
   }
   ```

4. **cursor_moved** - 光标移动
   ```json
   {
     "type": "cursor_moved",
     "user_id": "user2",
     "timestamp": 1640000000.0,
     "data": {
       "file_path": "src/main.py",
       "line": 42,
       "column": 10
     }
   }
   ```

5. **comment_added** - 评论添加
   ```json
   {
     "type": "comment_added",
     "user_id": "user2",
     "timestamp": 1640000000.0,
     "data": {
       "comment_id": "comment123",
       "file_path": "src/main.py",
       "line_number": 42,
       "content": "Good catch!",
       "parent_id": null
     }
   }
   ```

## Python API

### 创建和管理房间

```python
from pr_agent.collaboration import get_collaboration_manager, User, UserStatus
import asyncio

# 获取协作管理器
manager = get_collaboration_manager()

# 创建房间
room = manager.create_room(pr_number=123, repository="owner/repo")

# 创建用户
user = User(
    id="user1",
    name="Alice",
    email="alice@example.com",
    status=UserStatus.ACTIVE
)

# 加入房间
queue = asyncio.Queue()
await manager.join_room(room.room_id, user, queue)

# 更新光标
await room.update_cursor(user.id, "src/main.py", line=42, column=10)

# 添加评论
comment = await room.add_comment(
    user.id,
    "src/main.py",
    line_number=42,
    content="This needs refactoring"
)

# 添加注释
annotation = await room.add_annotation(
    user.id,
    "src/main.py",
    start_line=40,
    end_line=45,
    start_column=0,
    end_column=20,
    color="#ffff00",
    label="Review this"
)

# 离开房间
await manager.leave_room(room.room_id, user.id)
```

### 监听事件

```python
async def listen_to_events(queue):
    """监听协作事件"""
    while True:
        event = await queue.get()
        print(f"Received event: {event['type']}")
        
        if event['type'] == 'cursor_moved':
            print(f"User {event['user_id']} moved cursor to "
                  f"{event['data']['file_path']}:{event['data']['line']}")
        
        elif event['type'] == 'comment_added':
            print(f"New comment: {event['data']['content']}")
```

## 前端集成示例

### React Hook

```typescript
import { useEffect, useState } from 'react';

interface CollaborationUser {
  id: string;
  name: string;
  email: string;
  status: string;
  current_file?: string;
  cursor_position?: { line: number; column: number };
}

export function useCollaboration(roomId: string, userId: string) {
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [users, setUsers] = useState<CollaborationUser[]>([]);
  const [comments, setComments] = useState<any[]>([]);

  useEffect(() => {
    const websocket = new WebSocket(
      `ws://localhost:8080/ws/collaboration/${roomId}?user_id=${userId}&user_name=User&user_email=user@example.com`
    );

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'room_state':
          setUsers(message.data.users);
          setComments(message.data.comments);
          break;

        case 'user_joined':
          setUsers(prev => [...prev, message.data.user]);
          break;

        case 'user_left':
          setUsers(prev => prev.filter(u => u.id !== message.data.user_id));
          break;

        case 'comment_added':
          setComments(prev => [...prev, message.data]);
          break;
      }
    };

    setWs(websocket);

    return () => {
      websocket.close();
    };
  }, [roomId, userId]);

  const moveCursor = (filePath: string, line: number, column: number) => {
    ws?.send(JSON.stringify({
      type: 'cursor_move',
      file_path: filePath,
      line,
      column
    }));
  };

  const addComment = (filePath: string, lineNumber: number, content: string) => {
    ws?.send(JSON.stringify({
      type: 'add_comment',
      file_path: filePath,
      line_number: lineNumber,
      content
    }));
  };

  return { users, comments, moveCursor, addComment };
}
```

## 性能优化

### 事件节流

对于高频事件（如光标移动），建议使用节流：

```javascript
let cursorMoveTimeout;

function throttledCursorMove(filePath, line, column) {
  clearTimeout(cursorMoveTimeout);
  cursorMoveTimeout = setTimeout(() => {
    ws.send(JSON.stringify({
      type: 'cursor_move',
      file_path: filePath,
      line,
      column
    }));
  }, 100);  // 100ms 节流
}
```

### 事件历史限制

房间默认保留最近 100 个事件，可通过修改 `max_history` 调整：

```python
room.max_history = 200  # 保留 200 个事件
```

### 自动清理空房间

当所有用户离开时，房间会自动清理：

```python
# 在 CollaborationManager.leave_room 中自动执行
if room and not room.users:
    del self.rooms[room_id]
```

## 安全考虑

### 认证

WebSocket 连接需要通过查询参数传递用户信息：

```javascript
const ws = new WebSocket(
  `ws://localhost:8080/ws/collaboration/${roomId}?user_id=${userId}&user_name=${userName}&user_email=${userEmail}`
);
```

生产环境建议使用 JWT token 认证：

```javascript
const ws = new WebSocket(
  `ws://localhost:8080/ws/collaboration/${roomId}?token=${jwtToken}`
);
```

### 权限控制

- 用户只能编辑/删除自己的评论和注释
- 房间访问需要 PR 权限验证
- 管理员可以删除任何评论

### 数据验证

所有输入数据都经过验证：

```python
# 在 room.py 中
if user_id not in self.users:
    return  # 用户不在房间中

if comment.user_id != user_id:
    return None  # 无权限编辑
```

## 故障排除

### 问题：WebSocket 连接失败

**解决方案**:
- 检查 WebSocket URL 是否正确
- 确认用户参数已提供
- 验证房间 ID 存在

### 问题：事件未收到

**解决方案**:
- 检查 WebSocket 连接状态
- 确认用户已加入房间
- 查看服务器日志

### 问题：光标位置不同步

**解决方案**:
- 增加节流延迟
- 检查文件路径是否一致
- 验证坐标计算逻辑

## 扩展功能

### 添加自定义事件类型

```python
# 在 room.py 中添加新事件类型
class EventType(str, Enum):
    # ... 现有类型
    CUSTOM_EVENT = "custom_event"

# 添加处理方法
async def handle_custom_event(self, user_id: str, data: Dict):
    event = CollaborationEvent(
        type=EventType.CUSTOM_EVENT,
        user_id=user_id,
        timestamp=time.time(),
        data=data,
        room_id=self.room_id,
    )
    await self._broadcast_event(event)
```

### 持久化协作数据

```python
# 保存到数据库
async def save_to_database(self):
    db = get_database()
    await db.save_comments(self.comments)
    await db.save_annotations(self.annotations)

# 从数据库加载
async def load_from_database(self, room_id: str):
    db = get_database()
    self.comments = await db.load_comments(room_id)
    self.annotations = await db.load_annotations(room_id)
```

## 相关文档

- [WebSocket API 文档](API_REFERENCE.md#websocket)
- [前端集成指南](../frontend/README.md)
- [安全最佳实践](SECURITY.md)
