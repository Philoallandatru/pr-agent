#!/bin/bash
# Bitbucket Server Webhook 服务启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================="
echo "PR-Agent Bitbucket Server Webhook"
echo "=================================="
echo ""

# 检查环境变量
check_env_var() {
    if [ -z "${!1}" ]; then
        echo -e "${RED}错误: 环境变量 $1 未设置${NC}"
        return 1
    else
        echo -e "${GREEN}✓${NC} $1 已设置"
        return 0
    fi
}

echo "检查必需的环境变量..."
ENV_OK=true

if ! check_env_var "BITBUCKET_URL"; then ENV_OK=false; fi
if ! check_env_var "BITBUCKET_TOKEN"; then ENV_OK=false; fi

# 检查至少有一个 AI API key
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$AZURE_OPENAI_API_KEY" ]; then
    echo -e "${RED}错误: 至少需要设置一个 AI API key (OPENAI_API_KEY, ANTHROPIC_API_KEY, 或 AZURE_OPENAI_API_KEY)${NC}"
    ENV_OK=false
else
    echo -e "${GREEN}✓${NC} AI API key 已设置"
fi

if [ "$ENV_OK" = false ]; then
    echo ""
    echo -e "${YELLOW}提示: 创建 .env 文件并设置环境变量${NC}"
    echo "示例:"
    echo "  BITBUCKET_URL=https://bitbucket.example.com"
    echo "  BITBUCKET_TOKEN=your_token_here"
    echo "  OPENAI_API_KEY=sk-your-key-here"
    echo ""
    echo "然后运行: source .env 或 export \$(cat .env | xargs)"
    exit 1
fi

echo ""
echo "环境变量检查通过！"
echo ""

# 设置默认值
PORT=${PORT:-3000}
HOST=${HOST:-0.0.0.0}
WORKERS=${WORKERS:-4}

# 检查 Python 依赖
echo "检查 Python 依赖..."
if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
    echo -e "${RED}错误: 缺少必需的 Python 包${NC}"
    echo "请运行: pip install -r requirements.txt"
    exit 1
fi
echo -e "${GREEN}✓${NC} Python 依赖已安装"
echo ""

# 选择启动模式
echo "选择启动模式:"
echo "  1) 开发模式 (uvicorn, 单进程, 热重载)"
echo "  2) 生产模式 (gunicorn, 多进程)"
echo "  3) 后台运行 (nohup)"
echo ""
read -p "请选择 [1-3] (默认: 1): " MODE
MODE=${MODE:-1}

echo ""
echo "启动配置:"
echo "  地址: $HOST:$PORT"
echo "  工作进程: $WORKERS"
echo ""

case $MODE in
    1)
        echo "启动开发模式..."
        echo ""
        python -m uvicorn pr_agent.servers.bitbucket_server_webhook:app \
            --host $HOST \
            --port $PORT \
            --reload
        ;;
    2)
        echo "启动生产模式..."
        echo ""
        if ! command -v gunicorn &> /dev/null; then
            echo -e "${RED}错误: gunicorn 未安装${NC}"
            echo "请运行: pip install gunicorn"
            exit 1
        fi

        gunicorn pr_agent.servers.bitbucket_server_webhook:app \
            --bind $HOST:$PORT \
            --workers $WORKERS \
            --worker-class uvicorn.workers.UvicornWorker \
            --timeout 240 \
            --access-logfile - \
            --error-logfile -
        ;;
    3)
        echo "启动后台模式..."
        echo ""
        LOG_FILE="webhook_server.log"
        PID_FILE="webhook_server.pid"

        if [ -f "$PID_FILE" ]; then
            OLD_PID=$(cat $PID_FILE)
            if ps -p $OLD_PID > /dev/null 2>&1; then
                echo -e "${YELLOW}警告: 服务已在运行 (PID: $OLD_PID)${NC}"
                read -p "是否停止旧进程并重启? [y/N]: " RESTART
                if [ "$RESTART" = "y" ] || [ "$RESTART" = "Y" ]; then
                    kill $OLD_PID
                    sleep 2
                else
                    exit 0
                fi
            fi
        fi

        nohup python -m uvicorn pr_agent.servers.bitbucket_server_webhook:app \
            --host $HOST \
            --port $PORT \
            > $LOG_FILE 2>&1 &

        echo $! > $PID_FILE
        echo -e "${GREEN}✓${NC} 服务已启动 (PID: $(cat $PID_FILE))"
        echo "  日志文件: $LOG_FILE"
        echo "  PID 文件: $PID_FILE"
        echo ""
        echo "查看日志: tail -f $LOG_FILE"
        echo "停止服务: kill \$(cat $PID_FILE)"
        ;;
    *)
        echo -e "${RED}无效的选择${NC}"
        exit 1
        ;;
esac
