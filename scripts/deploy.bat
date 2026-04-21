@echo off
REM PR-Agent 快速部署脚本 (Windows)
REM 用于快速部署 PR-Agent 自动审查系统

echo ==========================================
echo PR-Agent 自动审查系统 - 快速部署
echo ==========================================
echo.

REM 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装 Docker
    echo 请访问 https://docs.docker.com/desktop/windows/install/ 安装 Docker Desktop
    exit /b 1
)

REM 检查 Docker Compose
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未安装 Docker Compose
    exit /b 1
)

echo [OK] Docker 和 Docker Compose 已安装
echo.

REM 检查 .env 文件
if not exist .env (
    echo 创建 .env 文件...
    copy .env.example .env
    echo.
    echo [!] 重要: 请编辑 .env 文件，配置以下必需项：
    echo   - JWT_SECRET_KEY ^(使用随机字符串^)
    echo   - BITBUCKET_SERVER_URL
    echo   - BITBUCKET_BEARER_TOKEN
    echo.
    pause
    notepad .env
)

REM 检查配置文件
if not exist pr_agent.toml (
    echo [!] 警告: 未找到 pr_agent.toml 配置文件
    echo 请创建配置文件或从模板复制
    exit /b 1
)

echo 配置文件检查完成
echo.

REM 询问是否下载 tokenizer
set /p DOWNLOAD_TOKENIZER="是否需要预下载 tokenizer？(内网部署必需) [y/N]: "
if /i "%DOWNLOAD_TOKENIZER%"=="y" (
    echo 下载 tokenizer...
    docker-compose run --rm backend python -m pr_agent.algo.tokenizer_manager download --models gpt-4o
    echo [OK] Tokenizer 下载完成
    echo.
)

REM 构建镜像
echo 构建 Docker 镜像...
docker-compose build

echo.
echo [OK] 镜像构建完成
echo.

REM 启动服务
echo 启动服务...
docker-compose up -d

echo.
echo 等待服务启动...
timeout /t 10 /nobreak >nul

REM 检查服务状态
echo.
echo 服务状态:
docker-compose ps

echo.
echo ==========================================
echo 部署完成！
echo ==========================================
echo.
echo Web 界面: http://localhost
echo API 端点: http://localhost:8000/api
echo 健康检查: http://localhost:8000/api/health
echo Metrics: http://localhost:8000/metrics
echo.
echo 默认登录凭据:
echo   用户名: admin
echo   密码: admin123
echo.
echo [!] 重要: 首次登录后请立即修改密码！
echo.
echo 查看日志: docker-compose logs -f
echo 停止服务: docker-compose down
echo.
pause
