# Bitbucket Server 内网部署：BM25 RAG + PR Review 全流程

这份文档提供一条可直接落地的路径：

1. 在内网 Bitbucket Server / Data Center 部署 PR-Agent
2. 启用轻量 BM25 RAG（本地索引，不依赖外部向量库）
3. 执行 Bitbucket Pull Request 的 `/review`

## 1. 适用场景

- 你主要使用 Bitbucket Server / Data Center
- 内网环境希望减少外网依赖
- 希望 review 不只看 diff，还能参考仓库内 `docs/prd/spec` 文档

## 2. 环境准备

推荐 Python 3.12：

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
python -m pip install -r requirements-dev.txt
```

## 3. 配置 Bitbucket Server

在 `pr_agent/settings/.secrets.toml` 中配置：

```toml
[bitbucket_server]
url = "https://git.your-company.local"
bearer_token = "YOUR_BITBUCKET_SERVER_TOKEN"
```

在仓库级配置（如 `.pr_agent.toml`）中指定 provider：

```toml
[config]
git_provider = "bitbucket_server"
```

## 4. 配置 BM25 RAG

在 `.pr_agent.toml` 添加：

```toml
[pr_rag]
enabled = true
backend = "bm25"
cache_dir = ".pr_agent_cache/rag"
code_chunk_lines = 80
doc_chunk_lines = 60
chunk_overlap_lines = 12
top_k_code = 4
top_k_docs = 3
max_context_chars = 12000
doc_paths = ["docs", "prd", "spec"]
force_refresh = false
```

关键参数说明：

- `enabled`: 是否开启 RAG
- `backend`: 当前使用 `bm25`
- `cache_dir`: 本地索引目录
- `top_k_code/top_k_docs`: 代码与文档召回配额
- `doc_paths`: 文档目录白名单
- `force_refresh`: 临时强制重建索引（排障用）

## 5.（推荐）配置离线 Tokenizer

如果你在内网运行，建议启用：

```toml
[tokenizer]
offline_only = true
cache_dir = "/opt/pr-agent/tiktoken_cache"
required_encodings = ["o200k_base", "cl100k_base"]
fallback_to_estimation = true
```

说明：

- `offline_only=true`：只使用本地缓存
- `fallback_to_estimation=true`：缓存缺失时降级估算，不阻断 review

## 6. 执行 Bitbucket PR Review

### 方式 A：CLI 单次执行（最简单）

```powershell
python cli.py --pr_url https://git.your-company.local/projects/PROJ/repos/REPO/pull-requests/123 review
```

执行逻辑：

1. 拉取 PR diff
2. 触发 BM25 检索（代码 + 文档）
3. 注入上下文到 review prompt
4. 输出 review（检索异常时自动回退 diff-only）

### 方式 B：Webhook 自动执行

```bash
docker build . -t pr-agent:bitbucket_server_webhook --target bitbucket_server_webhook -f docker/Dockerfile
docker run -d --name pr-agent -p 3000:3000 pr-agent:bitbucket_server_webhook
```

在 Bitbucket Server 中配置 webhook 到：

- `https://<your-domain>/webhook`

建议先勾选 `Pull Request Opened` 与 `Pull Request Updated` 验证链路。

## 7. 快速自检

1. 先关闭 RAG 执行一次 `review`，确认基础链路正常
2. 打开 `pr_rag.enabled=true`，确认输出出现上下文片段
3. 修改 `doc_paths` 下文档后再 review，确认文档可被召回
4. 删除索引目录后重跑，确认可自动重建或回退

## 8. 常见问题

### Q1：开启 RAG 但没召回文档

- 检查文档是否在 `doc_paths`
- 检查文档内容是否有可检索关键词
- 临时设置 `force_refresh=true` 重建索引

### Q2：内网 tokenizer 报错

- 检查 `tokenizer.cache_dir` 是否可读
- 确认 `required_encodings` 已预热
- 先开启 `fallback_to_estimation=true` 保证不中断

### Q3：只想走 diff review

```toml
[pr_rag]
enabled = false
```

## 9. 最小可用配置（可直接复制）

```toml
[config]
git_provider = "bitbucket_server"

[pr_rag]
enabled = true
backend = "bm25"
cache_dir = ".pr_agent_cache/rag"
doc_paths = ["docs", "prd", "spec"]

[tokenizer]
offline_only = true
required_encodings = ["o200k_base", "cl100k_base"]
fallback_to_estimation = true
```

```toml
[bitbucket_server]
url = "https://git.your-company.local"
bearer_token = "YOUR_BITBUCKET_SERVER_TOKEN"
```

## 10. 生产参数模板（按仓库规模）

建议先用“中仓模板”，再按效果和耗时调整。

### 模板 A：小仓（< 2k 文件）

```toml
[pr_rag]
enabled = true
backend = "bm25"
cache_dir = ".pr_agent_cache/rag"
code_chunk_lines = 100
doc_chunk_lines = 80
chunk_overlap_lines = 16
top_k_code = 5
top_k_docs = 4
max_context_chars = 15000
doc_paths = ["docs", "prd", "spec"]
force_refresh = false

[tokenizer]
offline_only = true
required_encodings = ["o200k_base", "cl100k_base"]
fallback_to_estimation = true
```

### 模板 B：中仓（2k - 20k 文件，推荐默认）

```toml
[pr_rag]
enabled = true
backend = "bm25"
cache_dir = ".pr_agent_cache/rag"
code_chunk_lines = 80
doc_chunk_lines = 60
chunk_overlap_lines = 12
top_k_code = 4
top_k_docs = 3
max_context_chars = 12000
doc_paths = ["docs", "prd", "spec"]
force_refresh = false

[tokenizer]
offline_only = true
required_encodings = ["o200k_base", "cl100k_base"]
fallback_to_estimation = true
```

### 模板 C：大仓（> 20k 文件）

```toml
[pr_rag]
enabled = true
backend = "bm25"
cache_dir = ".pr_agent_cache/rag"
code_chunk_lines = 60
doc_chunk_lines = 50
chunk_overlap_lines = 8
top_k_code = 3
top_k_docs = 2
max_context_chars = 9000
doc_paths = ["docs", "prd", "spec"]
force_refresh = false

[tokenizer]
offline_only = true
required_encodings = ["o200k_base", "cl100k_base"]
fallback_to_estimation = true
```

### 上线建议

1. 先跑 diff-only（`pr_rag.enabled=false`）确认基础稳定
2. 切到中仓模板并开启 RAG
3. 观察 1 周：响应时间、命中质量、告警
4. 要更强覆盖：向小仓模板调；要更稳更快：向大仓模板调
