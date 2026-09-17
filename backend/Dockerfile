# 多阶段 Dockerfile - 构建小体积生产镜像
# ====================================================
# Stage 1: 构建依赖（使用 builder 镜像编译）
# ====================================================
FROM python:3.12-slim AS builder

WORKDIR /build

# 系统依赖（编译 asyncpg / pandas 等需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制 requirements 并安装到独立目录（便于复制到 runtime）
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ====================================================
# Stage 2: 运行时镜像（精简）
# ====================================================
FROM python:3.12-slim AS runtime

# 时区设置
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 仅安装运行时必要的系统库（不需要 gcc）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

# 复制 builder 阶段安装的 Python 依赖
COPY --from=builder /install /usr/local

# 复制应用代码
COPY src ./src

# 创建非 root 用户运行应用（安全最佳实践）
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 工作目录切到 src，uvicorn 从这里找 main:app
WORKDIR /app/src

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

# 启动命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--proxy-headers"]
