# Database Migrations

PR-Agent 使用版本控制的数据库迁移系统来管理数据库架构变更。

## 概述

迁移系统提供：
- 版本化的数据库架构变更
- 向上迁移（应用变更）
- 向下迁移（回滚变更）
- 迁移状态追踪
- CLI 管理工具

## 迁移管理

### 查看迁移状态

```bash
python -m pr_agent.storage.migration status
```

输出示例：
```
Database: pr_agent.db
Current version: 20260422000001
Applied migrations: 1
Pending migrations: 0

Applied:
  ✓ 20260422000001
```

### 应用迁移

应用所有待处理的迁移：

```bash
python -m pr_agent.storage.migration migrate
```

应用到特定版本：

```bash
python -m pr_agent.storage.migration migrate 20260422000001
```

### 回滚迁移

回滚最后一个迁移：

```bash
python -m pr_agent.storage.migration rollback
```

回滚到特定版本：

```bash
python -m pr_agent.storage.migration rollback 20260422000001
```

## 创建新迁移

### 使用 CLI 创建

```bash
python -m pr_agent.storage.migration create "Add user preferences table"
```

这会创建一个新的迁移文件：
```
pr_agent/storage/migrations/20260422123456_add_user_preferences_table.py
```

### 迁移文件结构

```python
"""
Migration: Add user preferences table
Version: 20260422123456
Created: 2026-04-22T12:34:56
"""

from pr_agent.storage.migration import Migration
import sqlite3


class Migration20260422123456(Migration):
    """
    Add user preferences table
    """

    def __init__(self):
        super().__init__(
            version="20260422123456",
            description="Add user preferences table"
        )

    def up(self, conn: sqlite3.Connection):
        """Apply the migration."""
        conn.execute("""
            CREATE TABLE user_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)
            )
        """)
        
        conn.execute("""
            CREATE INDEX idx_user_preferences_user 
            ON user_preferences(user_id)
        """)

    def down(self, conn: sqlite3.Connection):
        """Rollback the migration."""
        conn.execute("DROP TABLE IF EXISTS user_preferences")
```

## 迁移最佳实践

### 1. 始终提供回滚逻辑

每个 `up()` 方法都应该有对应的 `down()` 方法：

```python
def up(self, conn: sqlite3.Connection):
    conn.execute("CREATE TABLE example (...)")

def down(self, conn: sqlite3.Connection):
    conn.execute("DROP TABLE IF EXISTS example")
```

### 2. 使用事务

迁移在事务中执行，失败会自动回滚：

```python
def up(self, conn: sqlite3.Connection):
    # 所有操作在同一事务中
    conn.execute("CREATE TABLE ...")
    conn.execute("CREATE INDEX ...")
    # 如果任何操作失败，整个迁移回滚
```

### 3. 添加索引

为常用查询字段添加索引：

```python
def up(self, conn: sqlite3.Connection):
    conn.execute("CREATE TABLE users (...)")
    conn.execute("CREATE INDEX idx_users_email ON users(email)")
    conn.execute("CREATE INDEX idx_users_created ON users(created_at)")
```

### 4. 数据迁移

迁移现有数据时要小心：

```python
def up(self, conn: sqlite3.Connection):
    # 添加新列（允许 NULL）
    conn.execute("ALTER TABLE users ADD COLUMN status TEXT")
    
    # 填充默认值
    conn.execute("UPDATE users SET status = 'active' WHERE status IS NULL")
    
    # 可选：添加 NOT NULL 约束（需要重建表）
```

### 5. 版本命名

版本号使用时间戳格式：`YYYYMMDDHHmmss`

- 确保唯一性
- 自然排序
- 包含创建时间信息

### 6. 描述性命名

使用清晰的描述：

```bash
# 好的命名
python -m pr_agent.storage.migration create "Add email verification to users"
python -m pr_agent.storage.migration create "Create audit logs table"

# 避免模糊命名
python -m pr_agent.storage.migration create "Update database"
python -m pr_agent.storage.migration create "Fix stuff"
```

## 常见迁移模式

### 添加新表

```python
def up(self, conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    conn.execute("CREATE INDEX idx_notifications_user ON notifications(user_id)")
    conn.execute("CREATE INDEX idx_notifications_read ON notifications(read)")

def down(self, conn: sqlite3.Connection):
    conn.execute("DROP TABLE IF EXISTS notifications")
```

### 添加列

```python
def up(self, conn: sqlite3.Connection):
    conn.execute("ALTER TABLE users ADD COLUMN phone TEXT")

def down(self, conn: sqlite3.Connection):
    # SQLite 不支持 DROP COLUMN，需要重建表
    conn.execute("""
        CREATE TABLE users_backup AS 
        SELECT id, name, email FROM users
    """)
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_backup RENAME TO users")
```

### 修改列（重建表）

SQLite 不支持直接修改列，需要重建表：

```python
def up(self, conn: sqlite3.Connection):
    # 创建新表
    conn.execute("""
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,  -- 添加 UNIQUE 约束
            name TEXT NOT NULL
        )
    """)
    
    # 复制数据
    conn.execute("INSERT INTO users_new SELECT id, email, name FROM users")
    
    # 删除旧表
    conn.execute("DROP TABLE users")
    
    # 重命名新表
    conn.execute("ALTER TABLE users_new RENAME TO users")

def down(self, conn: sqlite3.Connection):
    # 反向操作
    conn.execute("""
        CREATE TABLE users_old (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)
    conn.execute("INSERT INTO users_old SELECT id, email, name FROM users")
    conn.execute("DROP TABLE users")
    conn.execute("ALTER TABLE users_old RENAME TO users")
```

### 数据转换

```python
def up(self, conn: sqlite3.Connection):
    # 添加新列
    conn.execute("ALTER TABLE pr_reviews ADD COLUMN duration_ms INTEGER")
    
    # 转换数据（秒 -> 毫秒）
    conn.execute("UPDATE pr_reviews SET duration_ms = duration * 1000")

def down(self, conn: sqlite3.Connection):
    # 恢复原始数据
    conn.execute("UPDATE pr_reviews SET duration = duration_ms / 1000")
    
    # 删除新列（需要重建表）
    conn.execute("""
        CREATE TABLE pr_reviews_backup AS 
        SELECT id, repository_id, pr_number, duration 
        FROM pr_reviews
    """)
    conn.execute("DROP TABLE pr_reviews")
    conn.execute("ALTER TABLE pr_reviews_backup RENAME TO pr_reviews")
```

## 在代码中使用

### Python API

```python
from pr_agent.storage.migration import MigrationManager

# 创建管理器
manager = MigrationManager()

# 检查状态
status = manager.status()
print(f"Current version: {status['current_version']}")
print(f"Pending migrations: {status['pending_count']}")

# 应用迁移
manager.migrate()

# 回滚
manager.rollback()
```

### 集成到应用启动

```python
from pr_agent.storage.migration import MigrationManager

def init_database():
    """Initialize database with migrations."""
    manager = MigrationManager()
    
    # 检查待处理的迁移
    pending = manager.get_pending_migrations()
    
    if pending:
        print(f"Applying {len(pending)} pending migrations...")
        manager.migrate()
        print("Database migrations complete")
    else:
        print("Database is up to date")
```

## 部署流程

### 开发环境

```bash
# 1. 创建迁移
python -m pr_agent.storage.migration create "Add new feature"

# 2. 编辑迁移文件
# 编辑 pr_agent/storage/migrations/YYYYMMDDHHMMSS_add_new_feature.py

# 3. 应用迁移
python -m pr_agent.storage.migration migrate

# 4. 测试
# 运行应用并测试新功能

# 5. 提交代码
git add pr_agent/storage/migrations/
git commit -m "feat: add new feature migration"
```

### 生产环境

```bash
# 1. 备份数据库
cp pr_agent.db pr_agent.db.backup

# 2. 查看待处理的迁移
python -m pr_agent.storage.migration status

# 3. 应用迁移
python -m pr_agent.storage.migration migrate

# 4. 验证
python -m pr_agent.storage.migration status

# 5. 如果出错，回滚
python -m pr_agent.storage.migration rollback
# 或恢复备份
cp pr_agent.db.backup pr_agent.db
```

## 故障排查

### 迁移失败

如果迁移失败，系统会自动回滚：

```
Applying migration 20260422000001: Add new table
✗ Migration failed: table already exists
```

解决方法：
1. 检查迁移脚本
2. 修复错误
3. 重新运行迁移

### 迁移冲突

如果多个开发者创建了相同版本号的迁移：

```bash
# 重命名迁移文件，使用新的时间戳
mv 20260422120000_feature_a.py 20260422120001_feature_a.py

# 更新文件中的版本号
# 编辑文件，修改 version="20260422120001"
```

### 数据库损坏

如果数据库损坏：

```bash
# 1. 恢复备份
cp pr_agent.db.backup pr_agent.db

# 2. 重新应用迁移
python -m pr_agent.storage.migration migrate
```

## 初始迁移

系统包含一个初始迁移 `20260422000001_initial_schema.py`，创建基础表：

- `repositories` - 仓库配置
- `pr_reviews` - PR 审查记录
- `prompt_templates` - 提示词模板
- `system_logs` - 系统日志

首次部署时会自动应用此迁移。

## 相关文档

- [数据库设计](database.py) - 数据库层实现
- [部署指南](../docs/DEPLOYMENT.md) - 生产部署流程
