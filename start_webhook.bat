@echo off
REM Bitbucket Server Webhook 服务启动脚本 (Windows)

echo ==================================
echo PR-Agent Bitbucket Server Webhook
echo ==================================
echo.

REM 检查环境变量
echo 检查必需的环境变量...
set ENV_OK=1

if "%BITBUCKET_URL%"=="" (
    echo [错误] 环境变量 BITBUCKET_URL 未设置
    set ENV_OK=0
) else (
    echo [OK] BITBUCKET_URL 已设置
)

if "%BITBUCKET_TOKEN%"=="" (
    echo [错误] 环境变量 BITBUCKET_TOKEN 未设置
    set ENV_OK=0
) else (
    echo [OK] BITBUCKET_TOKEN 已设置
)

if "%OPENAI_API_KEY%"=="" (
    if "%ANTHROPIC_API_KEY%"=="" (
        if "%AZURE_OPENAI_API_KEY%"=="" (
            echo [错误] 至少需要设置一个 AI API key
            echo        OPENAI_API_KEY, ANTHROPIC_API_KEY, 或 AZURE_OPENAI_API_KEY
            set ENV_OK=0
        ) else (
            echo [OK] AI API key 已设置
        )
    ) else (
        echo [OK] AI API key 已设置
    )
) else (
    echo [OK] AI API key 已设置
)

if %ENV_OK%==0 (
    echo.
    echo 提示: 设置环境变量
    echo 示例:
    echo   set BITBUCKET_URL=https://bitbucket.example.com
    echo   set BITBUCKET_TOKEN=your_token_here
    echo   set OPENAI_API_KEY=sk-your-key-here
    echo.
    echo 或者创建 .env 文件并运行: set_env.bat
    pause
    exit /b 1
)

echo.
echo 环境变量检查通过！
echo.

REM 设置默认值
if "%PORT%"=="" set PORT=3000
if "%HOST%"=="" set HOST=0.0.0.0
if "%WORKERS%"=="" set WORKERS=4

REM 检查 Python 依赖
echo 检查 Python 依赖...
python -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    echo [错误] 缺少必需的 Python 包
    echo 请运行: pip install -r requirements.txt
    pause
    exit /b 1
)
echo [OK] Python 依赖已安装
echo.

REM 选择启动模式
echo 选择启动模式:
echo   1) 开发模式 (uvicorn, 单进程, 热重载)
echo   2) 生产模式 (gunicorn, 多进程) - 需要 WSL 或 Linux
echo   3) 后台运行 (使用 start 命令)
echo.
set /p MODE="请选择 [1-3] (默认: 1): "
if "%MODE%"=="" set MODE=1

echo.
echo 启动配置:
echo   地址: %HOST%:%PORT%
echo   工作进程: %WORKERS%
echo.

if "%MODE%"=="1" (
    echo 启动开发模式...
    echo.
    python -m uvicorn pr_agent.servers.bitbucket_server_webhook:app --host %HOST% --port %PORT% --reload
) else if "%MODE%"=="2" (
    echo 启动生产模式...
    echo.
    echo [警告] Windows 不支持 gunicorn
    echo 建议使用 WSL 或 Linux 环境运行生产模式
    echo 或者使用开发模式 (选项 1)
    pause
    exit /b 1
) else if "%MODE%"=="3" (
    echo 启动后台模式...
    echo.
    set LOG_FILE=webhook_server.log

    start "PR-Agent Webhook" /MIN cmd /c "python -m uvicorn pr_agent.servers.bitbucket_server_webhook:app --host %HOST% --port %PORT% > %LOG_FILE% 2>&1"

    echo [OK] 服务已在后台启动
    echo   日志文件: %LOG_FILE%
    echo.
    echo 查看日志: type %LOG_FILE%
    echo 停止服务: 在任务管理器中结束 python.exe 进程
    pause
) else (
    echo [错误] 无效的选择
    pause
    exit /b 1
)
