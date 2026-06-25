@echo off
chcp 65001 >nul
title 归因分析平台后端

cd /d "%~dp0"

echo.
echo ========================================
echo   归因分析平台后端启动
echo ========================================
echo.

REM 激活虚拟环境
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo [错误] 虚拟环境不存在，请先运行 init.bat
    pause
    exit /b 1
)

echo [检查] Python 环境...
python --version

echo.
echo [启动] FastAPI 服务...
echo.
echo   访问地址：
echo   - API 文档: http://localhost:8000/docs
echo   - ReDoc:    http://localhost:8000/redoc
echo   - 健康检查: http://localhost:8000/health
echo.
echo   按 Ctrl+C 停止服务
echo.

REM 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause
