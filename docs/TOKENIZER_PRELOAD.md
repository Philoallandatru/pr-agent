# Tokenizer 预加载指南

## 问题背景

在多进程 polling 服务中，如果多个进程同时尝试下载 modelscope tokenizer，会出现锁竞争问题：

```
Still waiting to acquire lock on /homessd/.cache/modelscope/hub/.lock
```

这会导致服务启动缓慢，甚至超时失败。

## 解决方案

在启动 polling 服务之前，预先下载好 tokenizer 到本地缓存，避免运行时的锁竞争。

## 使用方法

### 方法 1：使用启动脚本（推荐）

使用提供的启动脚本，自动检查并下载 tokenizer：

```bash
# 使用默认配置
./scripts/start_polling_service.sh

# 或自定义配置
TOKENIZER_CACHE_DIR=/custom/path \
MODELSCOPE_MODEL_ID=Qwen/Qwen3.6-35B-A3B-FP8 \
./scripts/start_polling_service.sh
```

脚本会：
1. 检查 tokenizer 是否已缓存
2. 如果未缓存，自动下载
3. 显示缓存信息
4. 启动 polling 服务

### 方法 2：手动预下载

如果需要手动控制下载过程：

```bash
# 下载到配置的缓存目录（默认：~/.cache/pr-agent/tokenizers）
python -m pr_agent.algo.tokenizer_manager download \
  --modelscope-model-id "Qwen/Qwen3.6-35B-A3B-FP8" \
  --cache-dir "$HOME/.cache/pr-agent/tokenizers"

# 验证下载
python -m pr_agent.algo.tokenizer_manager list \
  --cache-dir "$HOME/.cache/pr-agent/tokenizers"

# 查看缓存信息
python -m pr_agent.algo.tokenizer_manager info \
  --cache-dir "$HOME/.cache/pr-agent/tokenizers"
```

### 方法 3：使用 modelscope 直接下载

如果需要下载到 modelscope 默认缓存目录：

```bash
python -c "
from modelscope import snapshot_download
import os
from pathlib import Path

cache_dir = Path.home() / '.cache' / 'modelscope' / 'hub'
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ['MODELSCOPE_CACHE'] = str(cache_dir)

print(f'Downloading to {cache_dir}...')
snapshot_download(
    'Qwen/Qwen3.6-35B-A3B-FP8',
    cache_dir=str(cache_dir)
)
print('✓ Tokenizer downloaded successfully')
"
```

## 配置说明

在 `.pr_agent.toml` 或 `configuration.toml` 中配置：

```toml
[tokenizer]
# ModelScope 模型 ID
modelscope_model_id = "Qwen/Qwen3.6-35B-A3B-FP8"

# 本地缓存目录（支持 ~ 扩展为用户目录）
local_cache_dir = "~/.cache/pr-agent/tokenizers"
```

## Docker 部署

在 Dockerfile 中添加预下载步骤：

```dockerfile
# 安装依赖
RUN pip install -r requirements.txt

# 预下载 tokenizer（使用容器内用户目录）
RUN python -m pr_agent.algo.tokenizer_manager download \
    --modelscope-model-id "Qwen/Qwen3.6-35B-A3B-FP8" \
    --cache-dir "/home/appuser/.cache/pr-agent/tokenizers"

# 启动服务
CMD ["./scripts/start_polling_service.sh"]
```

## Kubernetes 部署

使用 init container 预下载：

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pr-agent-polling
spec:
  initContainers:
  - name: download-tokenizer
    image: pr-agent:latest
    command:
    - python
    - -m
    - pr_agent.algo.tokenizer_manager
    - download
    - --modelscope-model-id
    - Qwen/Qwen3.6-35B-A3B-FP8
    - --cache-dir
    - /home/appuser/.cache/pr-agent/tokenizers
    volumeMounts:
    - name: tokenizer-cache
      mountPath: /home/appuser/.cache/pr-agent/tokenizers
  containers:
  - name: polling-service
    image: pr-agent:latest
    command: ["./scripts/start_polling_service.sh"]
    volumeMounts:
    - name: tokenizer-cache
      mountPath: /home/appuser/.cache/pr-agent/tokenizers
  volumes:
  - name: tokenizer-cache
    persistentVolumeClaim:
      claimName: tokenizer-cache-pvc
```

## 缓存管理

### 查看缓存状态

```bash
python -m pr_agent.algo.tokenizer_manager info --cache-dir "$HOME/.cache/pr-agent/tokenizers"
```

输出示例：
```
Cache Information:
  Directory: /home/user/.cache/pr-agent/tokenizers
  Exists: True
  Cached Models: 1
  Total Size: 145.32 MB

  Models:
    - modelscope:Qwen/Qwen3.6-35B-A3B-FP8
```

### 清理缓存

```bash
# 清理特定模型
python -m pr_agent.algo.tokenizer_manager clear \
  --cache-dir "$HOME/.cache/pr-agent/tokenizers" \
  --models "modelscope:Qwen/Qwen3.6-35B-A3B-FP8"

# 清理所有缓存
python -m pr_agent.algo.tokenizer_manager clear \
  --cache-dir "$HOME/.cache/pr-agent/tokenizers"
```

### 验证缓存完整性

```bash
python -m pr_agent.algo.tokenizer_manager validate --cache-dir "$HOME/.cache/pr-agent/tokenizers"
```

## 故障排查

### 问题：仍然出现锁等待

**原因**：可能有多个缓存目录配置不一致

**解决**：
1. 检查环境变量 `MODELSCOPE_CACHE`
2. 检查配置文件中的 `tokenizer.local_cache_dir`
3. 确保所有进程使用相同的缓存目录

```bash
# 检查实际使用的缓存目录
python -c "
from pr_agent.config_loader import get_settings
print(get_settings().get('tokenizer.local_cache_dir'))
"
```

### 问题：下载失败

**原因**：网络问题或 modelscope 服务不可用

**解决**：
1. 检查网络连接
2. 使用代理：`export HF_ENDPOINT=https://hf-mirror.com`
3. 手动下载后放置到缓存目录

### 问题：权限错误

**原因**：缓存目录权限不足

**解决**：
```bash
# 使用用户目录（推荐，无需 sudo）
mkdir -p ~/.cache/pr-agent/tokenizers

# 或者使用系统目录（需要 sudo）
sudo mkdir -p /opt/pr-agent/tokenizers
sudo chown -R $(whoami):$(whoami) /opt/pr-agent/tokenizers
chmod 755 /opt/pr-agent/tokenizers
```

## 性能优化

### 使用共享缓存

在多实例部署中，使用共享存储（NFS、EFS）作为缓存目录：

```toml
[tokenizer]
local_cache_dir = "/mnt/shared/pr-agent/tokenizers"
```

### 预热多个模型

如果使用多个模型，可以批量预下载：

```bash
CACHE_DIR="$HOME/.cache/pr-agent/tokenizers"
for model_id in "Qwen/Qwen3.6-35B-A3B-FP8" "gpt-4" "gpt-4o"; do
    python -m pr_agent.algo.tokenizer_manager download \
        --modelscope-model-id "$model_id" \
        --cache-dir "$CACHE_DIR"
done
```

## 相关文档

- [POLLING_FIXES.md](POLLING_FIXES.md) - Polling 服务修复报告
- [BITBUCKET_POLLING.md](BITBUCKET_POLLING.md) - Polling 服务配置
- [TokenizerManager API](../pr_agent/algo/tokenizer_manager.py) - Tokenizer 管理器源码
