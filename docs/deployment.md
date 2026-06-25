# 部署指南

**版本**：v4.0  
**日期**：2026年6月  
**技术栈**：Vue-ts + Python LangGraph FastAPI + PostgreSQL pgvector + Redis + Docker

---

## 目录

1. [部署架构](#1-部署架构)
2. [Docker 部署](#2-docker-部署)
3. [生产环境配置](#3-生产环境配置)
4. [Nginx 配置](#4-nginx-配置)
5. [监控与日志](#5-监控与日志)
6. [备份与恢复](#6-备份与恢复)
7. [安全配置](#7-安全配置)
8. [故障排查](#8-故障排查)

---

## 1. 部署架构

### 1.1 生产环境架构

```
                         ┌─────────────┐
                         │   Nginx     │
                         │ (反向代理)  │
                         └──────┬──────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
     ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
     │   Frontend    │   │   Backend   │   │   Backend   │
     │  (Vue SPA)   │   │  (Python)   │   │  (Python)   │
     │   Nginx      │   │   Uvicorn   │   │   Worker    │
     │   静态资源   │   │    端口8000  │   │   端口8001   │
     └──────────────┘   └──────┬───────┘   └──────┬───────┘
                                │                   │
              ┌────────────────┴───────────────────┘
              │
              ▼
     ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
     │ PostgreSQL    │   │   pgvector   │   │    Redis     │
     │  (主数据库)   │   │  (向量存储)   │   │    (缓存)    │
     │   端口:5432  │   │   内嵌在 PG    │   │   端口:6379  │
     └──────────────┘   └──────────────┘   └──────────────┘
```

### 1.2 基础设施要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 50 GB | 100 GB SSD |
| PostgreSQL 内存 | 2 GB | 4 GB |

---

## 2. Docker 部署

### 2.1 前置准备

1. 安装 Docker 和 Docker Compose

```bash
# 检查 Docker 版本
docker --version
docker-compose --version
```

2. 克隆项目

```bash
git clone https://github.com/your-org/attribution-analysis.git
cd attribution-analysis
```

### 2.2 开发环境部署

```bash
# 启动所有服务（开发模式）
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 2.3 生产环境变量

创建 `production.env` 文件：

```env
# ============ 应用配置 ============
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=info

# ============ 数据库 (PostgreSQL) ============
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=attribution
DATABASE_USER=postgres
DATABASE_PASSWORD=changeme
DATABASE_SSL=false

# ============ Redis ============
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=changeme

# ============ LLM 配置 ============
LLM_PROVIDER=qianfan
QWEN_API_KEY=sk-xxx
QWEN_MODEL=qwen-plus

# ============ Embedding 配置 ============
EMBEDDING_PROVIDER=qianfan
EMBEDDING_MODEL=text-embedding-v3

# ============ CORS ============
CORS_ORIGINS=https://your-domain.com

# ============ 文件上传 ============
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760

# ============ 速率限制 ============
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### 2.4 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  # PostgreSQL 数据库 + pgvector
  postgres:
    image: pgvector/pgvector:pg16
    container_name: attribution-postgres
    restart: always
    environment:
      POSTGRES_DB: attribution
      POSTGRES_USER: ${DATABASE_USER:-postgres}
      POSTGRES_PASSWORD: ${DATABASE_PASSWORD:-changeme}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: >
      postgres
      -c shared_preload_libraries=vector
      -c 'vector.enabled=true'

  # Redis 缓存
  redis:
    image: redis:7-alpine
    container_name: attribution-redis
    restart: always
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-changeme}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-changeme}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  # 后端服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: attribution-backend
    restart: always
    environment:
      - APP_ENV=production
      - DATABASE_HOST=postgres
      - DATABASE_PORT=5432
      - DATABASE_NAME=attribution
      - DATABASE_USER=${DATABASE_USER:-postgres}
      - DATABASE_PASSWORD=${DATABASE_PASSWORD:-changeme}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - REDIS_PASSWORD=${REDIS_PASSWORD:-changeme}
    env_file:
      - production.env
    volumes:
      - ./uploads:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 前端服务
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: attribution-frontend
    restart: always
    depends_on:
      - backend

  # Nginx 反向代理
  nginx:
    image: nginx:alpine
    container_name: attribution-nginx
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - frontend_dist:/usr/share/nginx/html
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  redis_data:
  frontend_dist:
```

### 2.5 启动服务

```bash
# 构建并启动所有服务
docker-compose -f docker-compose.yml up -d --build

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f backend
```

### 2.6 初始化数据库

```bash
# 等待数据库就绪后，执行迁移
docker exec -it attribution-backend alembic upgrade head

# 启用 pgvector 扩展
docker exec -it attribution-postgres psql -U postgres -d attribution -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

---

## 3. 生产环境配置

### 3.1 后端配置 (production.env)

```env
# 应用
APP_ENV=production
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=info

# 数据库
DATABASE_HOST=postgres
DATABASE_PORT=5432
DATABASE_NAME=attribution
DATABASE_USER=postgres
DATABASE_PASSWORD=strong-password-here
DATABASE_SSL=false

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=strong-password-here

# LLM
LLM_PROVIDER=qianfan
QWEN_API_KEY=sk-xxx
QWEN_MODEL=qwen-plus

# Embedding
EMBEDDING_PROVIDER=qianfan
EMBEDDING_MODEL=text-embedding-v3

# CORS
CORS_ORIGINS=https://your-domain.com

# 速率限制
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

### 3.2 数据库初始化脚本

```bash
# backend/scripts/init_db.sql

-- 创建数据库
CREATE DATABASE attribution;

-- 连接到数据库
\c attribution

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证扩展
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

### 3.3 后端 Dockerfile

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建上传目录
RUN mkdir -p /app/uploads

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 3.4 前端 Dockerfile

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine as build

WORKDIR /app

# 复制依赖文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制源代码
COPY . .

# 构建
RUN npm run build

# 生产镜像
FROM nginx:alpine

# 复制构建产物
COPY --from=build /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## 4. Nginx 配置

### 4.1 Nginx 配置文件

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # 性能优化
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript application/rss+xml application/atom+xml image/svg+xml;

    # 上游服务
    upstream backend {
        server backend:8000;
        keepalive 32;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # 重定向到 HTTPS（生产环境）
        # return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL 证书（生产环境）
        # ssl_certificate /etc/nginx/ssl/fullchain.pem;
        # ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;

        # SSL 安全配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        # HSTS
        add_header Strict-Transport-Security "max-age=63072000" always;

        # 安全头
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # API 代理
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;

            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;

            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 健康检查
        location /health {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
        }

        # 前端静态文件
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            expires 1h;
            add_header Cache-Control "public, immutable";
        }

        # 静态资源缓存
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            root /usr/share/nginx/html;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

### 4.2 速率限制配置

在 `nginx.conf` 的 `http` 块中添加：

```nginx
# 速率限制 zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

---

## 5. 监控与日志

### 5.1 Docker 日志

```bash
# 查看所有日志
docker-compose logs

# 查看特定服务
docker-compose logs backend

# 实时日志
docker-compose logs -f

# 查看最近 100 行
docker-compose logs --tail 100 backend
```

### 5.2 健康检查

```bash
# 后端健康检查
curl http://localhost:8000/health

# 响应示例
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected",
    "pgvector": "connected"
  }
}
```

---

## 6. 备份与恢复

### 6.1 数据库备份

```bash
# 创建备份脚本 backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=./backups
DB_NAME=attribution

# PostgreSQL 备份
docker exec attribution-postgres pg_dump -U postgres -d $DB_NAME | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# 保留最近 30 天的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
```

### 6.2 定时备份 (cron)

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 3 点执行备份
0 3 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

### 6.3 恢复数据

```bash
# 解压并恢复
gunzip < postgres_20240625_030000.sql.gz | docker exec -i attribution-postgres psql -U postgres -d attribution
```

### 6.4 pgvector 索引重建

```bash
# 重建向量索引（如果需要）
docker exec -it attribution-postgres psql -U postgres -d attribution -c "
REINDEX INDEX idx_attribution_vector_hnsw;
"
```

---

## 7. 安全配置

### 7.1 环境变量安全

```bash
# 不要提交 .env 到 Git
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore
echo "production.env" >> .gitignore
```

### 7.2 数据库安全

```sql
-- 创建应用专用用户
CREATE USER app_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE attribution TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- 启用 SSL（生产环境）
ALTER DATABASE attribution SET ssl = on;
```

### 7.3 防火墙配置

```bash
# 只开放必要端口
# 80  (HTTP)
# 443 (HTTPS)
# 22  (SSH)

# 禁止外部访问数据库
# PostgreSQL: 5432
# Redis: 6379
```

### 7.4 定期安全更新

```bash
# 创建更新脚本 security-update.sh
#!/bin/bash
docker-compose pull
docker-compose up -d
docker system prune -f
```

---

## 8. 故障排查

### 8.1 服务启动失败

```bash
# 检查 Docker 日志
docker-compose logs backend

# 检查端口占用
netstat -tlnp | findstr :8000

# 重启服务
docker-compose restart backend
```

### 8.2 数据库连接失败

```bash
# 检查数据库健康
docker exec -it attribution-postgres pg_isready -U postgres

# 测试连接
docker exec -it attribution-backend sh -c "apt-get update && apt-get install -y postgresql-client && psql -h postgres -U postgres -d attribution -c 'SELECT 1;'"
```

### 8.3 pgvector 扩展问题

```bash
# 检查 pgvector 是否启用
docker exec -it attribution-postgres psql -U postgres -d attribution -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

# 启用 pgvector 扩展
docker exec -it attribution-postgres psql -U postgres -d attribution -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 8.4 Redis 连接问题

```bash
# 检查 Redis 健康
docker exec -it attribution-redis redis-cli -a changeme ping

# 测试连接
docker exec -it attribution-backend sh -c "apt-get update && apt-get install -y redis-tools && redis-cli -h redis -a changeme ping"
```

### 8.5 前端 502 错误

```bash
# 检查 Nginx 日志
docker logs attribution-nginx --tail 100

# 检查上游服务
curl http://backend:8000/health
```

---

## 相关文档

- [架构文档](./architecture.md)
- [API 文档](./api.md)
- [快速开始](./getting-started.md)
- [数据源说明](./data-source.md)
