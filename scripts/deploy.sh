#!/bin/bash

# PR-Agent 快速部署脚本
# 用于快速部署 PR-Agent 自动审查系统

set -e

echo "=========================================="
echo "PR-Agent 自动审查系统 - 快速部署"
echo "=========================================="
echo ""

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "错误: 未安装 Docker"
    echo "请访问 https://docs.docker.com/get-docker/ 安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: 未安装 Docker Compose"
    echo "请访问 https://docs.docker.com/compose/install/ 安装 Docker Compose"
    exit 1
fi

echo "✓ Docker 和 Docker Compose 已安装"
echo ""

# 检查是否存在 .env 文件
if [ ! -f .env ]; then
    echo "创建 .env 文件..."
    cp .env.example .env

    # 生成随机 JWT 密钥
    if command -v openssl &> /dev/null; then
        JWT_SECRET=$(openssl rand -hex 32)
        sed -i "s/change-this-to-a-secure-random-string/$JWT_SECRET/" .env
        echo "✓ 已生成随机 JWT 密钥"
    else
        echo "⚠ 警告: 未安装 openssl，请手动修改 .env 中的 JWT_SECRET_KEY"
    fi

    echo ""
    echo "⚠ 重要: 请编辑 .env 文件，配置以下必需项："
    echo "  - BITBUCKET_SERVER_URL"
    echo "  - BITBUCKET_BEARER_TOKEN"
    echo ""
    read -p "按 Enter 继续编辑 .env 文件..."
    ${EDITOR:-nano} .env
fi

# 检查是否存在 pr_agent.toml
if [ ! -f pr_agent.toml ]; then
    echo "⚠ 警告: 未找到 pr_agent.toml 配置文件"
    echo "请创建配置文件或从模板复制"
    exit 1
fi

echo "配置文件检查完成"
echo ""

# 询问是否需要预下载 tokenizer
read -p "是否需要预下载 tokenizer？(内网部署必需) [y/N]: " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "下载 tokenizer..."
    docker-compose run --rm backend python -m pr_agent.algo.tokenizer_manager download --models gpt-4o
    echo "✓ Tokenizer 下载完成"
    echo ""
fi

# 构建镜像
echo "构建 Docker 镜像..."
docker-compose build

echo ""
echo "✓ 镜像构建完成"
echo ""

# 启动服务
echo "启动服务..."
docker-compose up -d

echo ""
echo "等待服务启动..."
sleep 10

# 检查服务状态
echo ""
echo "服务状态:"
docker-compose ps

echo ""
echo "=========================================="
echo "部署完成！"
echo "=========================================="
echo ""
echo "Web 界面: http://localhost"
echo "API 端点: http://localhost:8000/api"
echo "健康检查: http://localhost:8000/api/health"
echo "Metrics: http://localhost:8000/metrics"
echo ""
echo "默认登录凭据:"
echo "  用户名: admin"
echo "  密码: admin123"
echo ""
echo "⚠ 重要: 首次登录后请立即修改密码！"
echo ""
echo "查看日志: docker-compose logs -f"
echo "停止服务: docker-compose down"
echo ""
