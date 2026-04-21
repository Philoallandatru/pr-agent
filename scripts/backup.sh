#!/bin/bash

# PR-Agent 数据备份脚本

set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="pr-agent-backup-${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

echo "=========================================="
echo "PR-Agent 数据备份"
echo "=========================================="
echo ""

# 创建备份目录
mkdir -p "${BACKUP_PATH}"

echo "备份目录: ${BACKUP_PATH}"
echo ""

# 备份数据库
echo "备份数据库..."
docker cp pr-agent-backend:/data/db/pr_agent.db "${BACKUP_PATH}/pr_agent.db"
echo "✓ 数据库备份完成"

# 备份配置文件
echo "备份配置文件..."
cp pr_agent.toml "${BACKUP_PATH}/"
cp .env "${BACKUP_PATH}/"
echo "✓ 配置文件备份完成"

# 备份轮询状态
echo "备份轮询状态..."
docker cp pr-agent-backend:/data/state/polling_state.json "${BACKUP_PATH}/polling_state.json" 2>/dev/null || echo "  (轮询状态文件不存在，跳过)"

# 创建备份信息文件
cat > "${BACKUP_PATH}/backup_info.txt" << EOF
备份时间: $(date)
备份内容:
  - 数据库 (pr_agent.db)
  - 配置文件 (pr_agent.toml, .env)
  - 轮询状态 (polling_state.json)

恢复方法:
  1. 停止服务: docker-compose down
  2. 恢复数据库: docker cp ${BACKUP_NAME}/pr_agent.db pr-agent-backend:/data/db/
  3. 恢复配置: cp ${BACKUP_NAME}/pr_agent.toml ./
  4. 恢复环境变量: cp ${BACKUP_NAME}/.env ./
  5. 启动服务: docker-compose up -d
EOF

# 压缩备份
echo "压缩备份..."
cd "${BACKUP_DIR}"
tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
rm -rf "${BACKUP_NAME}"
cd - > /dev/null

echo "✓ 备份压缩完成"
echo ""

# 清理旧备份（保留最近7天）
echo "清理旧备份（保留最近7天）..."
find "${BACKUP_DIR}" -name "pr-agent-backup-*.tar.gz" -mtime +7 -delete
echo "✓ 清理完成"

echo ""
echo "=========================================="
echo "备份完成！"
echo "=========================================="
echo ""
echo "备份文件: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
echo ""

# 显示备份大小
BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" | cut -f1)
echo "备份大小: ${BACKUP_SIZE}"
echo ""
