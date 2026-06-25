@echo off
chcp 65001 >nul
title 归因分析平台 - 初始化

cd /d "%~dp0"

echo.
echo ========================================
echo   初始化项目环境
echo ========================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python，请先安装 Python 3.11+
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/6] 检查 Python 版本...
python --version

REM 创建虚拟环境
echo [2/6] 创建虚拟环境...
if not exist venv (
    python -m venv venv
    echo 虚拟环境创建完成
) else (
    echo [跳过] 虚拟环境已存在
)

REM 激活虚拟环境
echo [3/6] 激活虚拟环境...
call venv\Scripts\activate.bat

REM 升级 pip
echo [4/6] 升级 pip...
python -m pip install --upgrade pip -q

REM 安装依赖
echo [5/6] 安装依赖（可能需要几分钟）...
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [警告] 部分依赖安装失败，尝试安装核心依赖...
    pip install fastapi uvicorn sqlalchemy pymysql pydantic-settings alembic akshare pandas -q
)

REM 初始化数据库
echo [6/6] 初始化数据库...
python scripts\init_db.py

echo.
echo ========================================
echo   初始化完成！
echo ========================================
echo.
echo   下一步：
echo   1. 配置 .env 文件（修改数据库连接）
echo   2. 运行 start.bat 启动服务
echo.
echo   常用命令：
echo   - 启动服务: uvicorn app.main:app --reload
echo   - 采集数据: python scripts\collect_data.py -m single
echo   - 数据库迁移: alembic upgrade head
echo.
echo ========================================
echo.

pause
