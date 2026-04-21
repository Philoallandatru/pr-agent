#!/bin/bash

# PR-Agent 数据恢复脚本

set -e

if [ -z "$1" ]; then
    echo "用法: $0 <备份文件>"
    echo ""
    echo "可用的备份文件:"
    ls -lh backups/*.tar.gz 2>/dev/null || echo "  (无备份文件)"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "错误: 备份文件不存在: ${BACKUP_FILE}"
    exit 1
fi

echo "=========================================="
echo "PR-Agent 数据恢复"
echo "=========================================="
echo ""
echo "备份文件: ${BACKUP_FILE}"
echo ""

# 确认恢复
read -p "⚠ 警告: 此操作将覆盖现有数据。是否继续？[y/N]: " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "已取消恢复"
    exit 0
fi

# 停止服务
echo "停止服务..."
docker-compose down
echo "✓ 服务已停止"
echo ""

# 解压备份
TEMP_DIR=$(mktemp -d)
echo "解压备份到临时目录..."
tar xzf "${BACKUP_FILE}" -C "${TEMP_DIR}"
BACKUP_NAME=$(basename "${BACKUP_FILE}" .tar.gz)
BACKUP_PATH="${TEMP_DIR}/${BACKUP_NAME}"

# 恢复数据库
if [ -f "${BACKUP_PATH}/pr_agent.db" ]; then
    echo "恢复数据库..."
    docker volume create pr-agent_db-data
    docker run --rm -v pr-agent_db-data:/data -v "${BACKUP_PATH}":/backup alpine sh -c "mkdir -p /data/db && cp /backup/pr_agent.db /data/db/"
    echo "✓ 数据库恢复完成"
else
    echo "⚠ 警告: 备份中未找到数据库文件"
fi

# 恢复配置文件
if [ -f "${BACKUP_PATH}/pr_agent.toml" ]; then
    echo "恢复配置文件..."
    cp "${BACKUP_PATH}/pr_agent.toml" ./
    echo "✓ pr_agent.toml 恢复完成"
fi

if [ -f "${BACKUP_PATH}/.env" ]; then
    cp "${BACKUP_PATH}/.env" ./
    echo "✓ .env 恢复完成"
fi

# 恢复轮询状态
if [ -f "${BACKUP_PATH}/polling_state.json" ]; then
    echo "恢复轮询状态..."
    docker volume create pr-agent_polling-state
    docker run --rm -v pr-agent_polling-state:/data -v "${BACKUP_PATH}":/backup alpine sh -c "mkdir -p /data/state && cp /backup/polling_state.json /data/state/"
    echo "✓ 轮询状态恢复完成"
fi

# 清理临时目录
rm -rf "${TEMP_DIR}"

echo ""
echo "启动服务..."
docker-compose up -d

echo ""
echo "等待服务启动..."
sleep 10

echo ""
echo "=========================================="
echo "恢复完成！"
echo "=========================================="
echo ""
echo "服务状态:"
docker-compose ps
echo ""
