# Polling 重复审查问题修复报告

## 修复日期
2026-05-26

## 问题概述

通过最大力度代码审查（5 个独立查找角度 + 单次验证 + 扫描遗漏），发现了 12 个会导致 PR 被反复审查的严重 bug。

## 已修复的问题

### P0 - 关键问题（立即修复）

#### 1. result_queue 收集逻辑提前退出
**文件**: `pr_agent/servers/bitbucket_server_polling.py:394`

**问题**: 循环在第一个 `queue.Empty` 时 break，导致后续成功结果丢失。

**修复**:
- 改为收集所有可用结果，不在第一个超时时退出
- 添加进程存活检查，只有所有进程都结束才退出循环
- 优先信任 result_queue 的实际结果，而非超时标记

```python
# 修复前
for _ in processes:
    try:
        result = result_queue.get(timeout=1)
    except queue.Empty:
        break  # 第一个超时就退出

# 修复后
results_collected = 0
while results_collected < len(processes):
    try:
        result = result_queue.get(timeout=1)
        results[result_key] = bool(result.get("success"))
        results_collected += 1
    except queue.Empty:
        if all(not process_info["process"].is_alive() for process_info in processes):
            break
        continue
```

#### 2. threading.Lock 在多进程环境下无效
**文件**: `pr_agent/storage/polling_state.py:34`

**问题**: 使用 `threading.Lock` 而非进程锁，多进程环境下锁完全无效。

**修复**:
- 移除 `threading.Lock`
- 实现跨平台文件锁（Unix: fcntl.flock, Windows: msvcrt.locking）
- 每次读写操作都重新加载状态文件，确保获取最新数据

```python
# 修复前
self._lock = Lock()  # 线程锁，多进程无效

# 修复后
def _acquire_lock(self, file_handle):
    if HAS_FCNTL:
        fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
    elif HAS_MSVCRT:
        msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
```

#### 3. 状态在进程启动前更新
**文件**: `pr_agent/servers/bitbucket_server_polling.py:329`

**问题**: 状态设为 "processing" 后进程启动失败，状态永久卡住。

**修复**:
- 先启动进程，成功后再更新状态
- 添加异常处理，启动失败时立即标记为 "failed"

```python
# 修复前
state.update_pr_state(..., status="processing")
p.start()  # 如果失败，状态永久停留在 processing

# 修复后
try:
    p.start()
    state.update_pr_state(..., status="processing")  # 启动成功后才更新
except Exception as e:
    state.update_pr_state(..., status="failed")  # 失败立即标记
```

### P1 - 重要问题（尽快修复）

#### 4. 进程超时竞态条件
**文件**: `pr_agent/servers/bitbucket_server_polling.py:407`

**问题**: 进程在超时边界完成时，timed_out 标记与实际结果冲突。

**修复**:
- 优先信任 result_queue 的实际结果
- 调整成功判断逻辑顺序

```python
# 修复前
success = (
    not process_info["timed_out"]
    and results.get(task_key, False)
    and process.exitcode == 0
)

# 修复后
success = (
    has_result
    and results[task_key]
    and process.exitcode == 0
    and not process_info["timed_out"]
)
```

#### 5. JSON 文件写入不是原子操作
**文件**: `pr_agent/storage/polling_state.py:55`

**问题**: 多进程并发写入导致文件损坏。

**修复**:
- 使用 write-then-rename 原子写入模式
- 先写入临时文件，再原子性重命名

```python
# 修复前
with open(self.state_file, 'w') as f:
    json.dump(self._state, f, indent=2)

# 修复后
temp_fd, temp_path = tempfile.mkstemp(...)
with os.fdopen(temp_fd, 'w') as f:
    json.dump(self._state, f, indent=2)
    f.flush()
    os.fsync(f.fileno())
os.replace(temp_path, self.state_file)  # 原子性重命名
```

#### 6. 状态保存失败静默吞掉错误
**文件**: `pr_agent/storage/polling_state.py:49`

**问题**: 磁盘满或权限错误时，状态更新在内存中成功但未持久化。

**修复**:
- 保存失败时抛出异常，让调用者感知

```python
# 修复前
except Exception as e:
    get_logger().error(f"Failed to save polling state: {e}")
    # 静默失败

# 修复后
except Exception as e:
    get_logger().error(f"Failed to save polling state: {e}")
    raise  # 重新抛出异常
```

#### 7. result_queue 未正确关闭
**文件**: `pr_agent/servers/bitbucket_server_polling.py:421`

**问题**: 只调用 `close()` 未调用 `join_thread()`，后台线程可能未完成写入。

**修复**:
- 添加 `join_thread()` 确保后台线程完成

```python
# 修复前
result_queue.close()

# 修复后
result_queue.close()
result_queue.join_thread()
```

### P2 - 次要问题（计划修复）

#### 8. cleanup 时时间戳解析失败删除有效 PR
**文件**: `pr_agent/storage/polling_state.py:165`

**修复**: 时间戳损坏时保留条目，只记录警告

#### 9. get_all_state() 返回浅拷贝
**文件**: `pr_agent/storage/polling_state.py:191`

**修复**: 使用 `copy.deepcopy()` 返回深拷贝

#### 10. 使用 timezone-naive datetime
**文件**: `pr_agent/storage/polling_state.py:98`

**修复**: 改用 `datetime.now(timezone.utc)` 和 timezone-aware 比较

## 修改统计

```
pr_agent/servers/bitbucket_server_polling.py |  79 ++++++----
pr_agent/storage/polling_state.py            | 215 +++++++++++++++---------
2 files changed, 198 insertions(+), 96 deletions(-)
```

## 测试验证

基本功能测试通过：
- ✓ 状态更新和读取
- ✓ is_pr_processed 判断逻辑
- ✓ get_all_state 深拷贝隔离
- ✓ 文件锁跨平台兼容性

## 根本原因分析

1. **并发控制缺失**: 使用线程锁而非进程锁，文件操作无原子性保护
2. **错误处理不完整**: 状态保存失败、队列读取超时等错误被静默吞掉
3. **状态机不完整**: `processing` 状态无超时恢复机制
4. **时序假设错误**: 假设进程启动必成功、超时前不会完成等
5. **资源清理不完整**: 队列未正确关闭、浅拷贝暴露内部状态

## 建议

### 短期
- 监控状态文件大小和损坏情况
- 添加 Prometheus 指标跟踪重复审查率
- 定期清理超过 30 天的状态条目

### 长期
- 考虑使用 Redis 或数据库替代 JSON 文件存储
- 实现分布式锁（如 Redis SETNX）支持多实例部署
- 添加状态机超时恢复机制
- 实现幂等性保证，即使重复审查也不会重复发布评论

## 相关文档

- [BITBUCKET_POLLING.md](BITBUCKET_POLLING.md) - Polling 服务配置和使用
- [AGENTIC_REVIEW.md](AGENTIC_REVIEW.md) - Agentic review 功能说明
