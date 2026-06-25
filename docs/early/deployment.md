# 部署指南

**版本**：v2.0  
**日期**：2026年6月

---

## 目录

1. [部署架构](#1-部署架构)
2. [Docker 部署](#2-docker-部署)
3. [手动部署](#3-手动部署)
4. [生产环境配置](#4-生产环境配置)
5. [Nginx 配置](#5-nginx-配置)
6. [监控与日志](#6-监控与日志)
7. [备份与恢复](#7-备份与恢复)
8. [安全配置](#8-安全配置)

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
     │   Frontend   │   │   Backend   │   │   Backend    │
     │  (Vue SPA)   │   │  (Node.js)  │   │  (Node.js)   │
     └──────────────┘   └──────┬───────┘   └──────┬───────┘
                               │                   │
              ┌────────────────┴───────────────────┘
              │
              ▼
     ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
     │ PostgreSQL   │   │   Qdrant     │   │    Redis     │
     │  (主数据库)   │   │ (向量数据库)  │   │   (缓存)     │
     └──────────────┘   └──────────────┘   └──────────────┘
```

### 1.2 基础设施要求

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 4 GB | 8 GB |
| 磁盘 | 50 GB | 100 GB SSD |
| 数据库 | 2 GB | 4 GB |

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

### 2.2 生产环境变量

创建 `production.env` 文件：

```env
# ============ 应用配置 ============
NODE_ENV=production
PORT=3000
LOG_LEVEL=info

# ============ 数据库 ============
DATABASE_URL=postgresql://user:password@postgres:5432/attribution
DATABASE_SSL=true

# ============ 向量数据库 ============
VECTOR_DB_URL=http://qdrant:6333
VECTOR_DB_COLLECTION=experiences

# ============ Redis ============
REDIS_URL=redis://redis:6379

# ============ LLM 配置 ============
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1

# ============ JWT ============
JWT_SECRET=your-production-jwt-secret-min-32-chars
JWT_EXPIRES_IN=7d

# ============ CORS ============
CORS_ORIGIN=https://your-domain.com

# ============ 文件上传 ============
UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE=10485760

# ============ 速率限制 ============
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
```

### 2.3 Docker Compose 配置

创建 `docker-compose.prod.yml`：

```yaml
version: '3.8'

services:
  # PostgreSQL 数据库
  postgres:
    image: postgres:16-alpine
    container_name: attribution-postgres
    restart: always
    environment:
      POSTGRES_DB: attribution
      POSTGRES_USER: ${DB_USER:-postgres}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-changeme}
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

  # Qdrant 向量数据库
  qdrant:
    image: qdrant/qdrant:latest
    container_name: attribution-qdrant
    restart: always
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/readyz"]
      interval: 10s
      timeout: 5s
      retries: 3

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

  # 后端服务
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: attribution-backend
    restart: always
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://${DB_USER:-postgres}:${DB_PASSWORD:-changeme}@postgres:5432/attribution
      - VECTOR_DB_URL=http://qdrant:6333
      - REDIS_URL=redis://:${REDIS_PASSWORD:-changeme}@redis:6379
    env_file:
      - production.env
    volumes:
      - uploads_data:/app/uploads
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
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
    env_file:
      - production.env
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
      - static_data:/var/www/html
    depends_on:
      - backend
      - frontend

volumes:
  postgres_data:
  qdrant_data:
  redis_data:
  uploads_data:
  static_data:
```

### 2.4 启动服务

```bash
# 构建并启动所有服务
docker-compose -f docker-compose.prod.yml up -d --build

# 查看服务状态
docker-compose -f docker-compose.prod.yml ps

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f backend
```

### 2.5 初始化数据库

```bash
# 等待数据库就绪后，执行迁移
docker exec -it attribution-backend pnpm prisma migrate deploy

# 创建管理员用户
docker exec -it attribution-backend pnpm prisma db seed
```

---

## 3. 手动部署

### 3.1 服务器环境

```bash
# 安装 Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 安装 PostgreSQL 16
sudo apt-get install -y postgresql-16

# 安装 Redis
sudo apt-get install -y redis-server

# 安装 PM2
sudo npm install -g pm2
```

### 3.2 构建应用

```bash
# 后端
cd backend
pnpm install --production
pnpm build

# 前端
cd ../frontend
pnpm install --production
pnpm build
```

### 3.3 配置 PM2

创建 `ecosystem.config.js`：

```javascript
// backend/ecosystem.config.js
module.exports = {
  apps: [{
    name: 'attribution-backend',
    script: 'dist/index.js',
    instances: 'max',
    exec_mode: 'cluster',
    env_production: {
      NODE_ENV: 'production'
    },
    env_file: '.env.production',
    max_memory_restart: '1G',
    restart_delay: 4000,
    error_file: './logs/error.log',
    out_file: './logs/out.log',
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
  }]
};
```

### 3.4 启动服务

```bash
cd backend

# 初始化数据库
pnpm prisma generate
pnpm prisma migrate deploy

# 启动
pm2 start ecosystem.config.js --env production

# 保存 PM2 配置
pm2 save

# 设置开机自启
pm2 startup
```

---

## 4. 生产环境配置

### 4.1 后端配置 (backend/.env.production)

```env
# 应用
NODE_ENV=production
PORT=3000
LOG_LEVEL=info

# 数据库
DATABASE_URL=postgresql://user:password@prod-db:5432/attribution?sslmode=require

# 向量数据库
VECTOR_DB_URL=http://qdrant:6333

# Redis
REDIS_URL=redis://:password@prod-redis:6379

# LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxx
OPENAI_MODEL=gpt-4o-mini

# JWT
JWT_SECRET=your-production-jwt-secret-min-32-chars
JWT_EXPIRES_IN=7d

# CORS
CORS_ORIGIN=https://your-domain.com

# 速率限制
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
```

### 4.2 前端配置 (frontend/.env.production)

```env
VITE_API_BASE_URL=https://api.your-domain.com
VITE_APP_TITLE=智能金融归因分析平台
VITE_GA_ID=G-XXXXXXXXXX
```

### 4.3 Prisma 生产配置

```prisma
// backend/prisma/schema.prisma
generator client {
  provider        = "prisma-client-js"
  previewFeatures = ["fullTextSearch"]
}

datasource db {
  provider   = "postgresql"
  url        = env("DATABASE_URL")
  ssl       = true
}
```

---

## 5. Nginx 配置

### 5.1 Nginx 配置文件

创建 `nginx/nginx.conf`：

```nginx
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
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

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
        server backend:3000;
        keepalive 32;
    }

    upstream frontend {
        server frontend:80;
        keepalive 16;
    }

    server {
        listen 80;
        server_name your-domain.com;

        # 重定向到 HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name your-domain.com;

        # SSL 证书
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;

        # SSL 安全配置
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;

        # HSTS
        add_header Strict-Transport-Security "max-age=63072000" always;

        # 安全头
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;

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

        # 前端静态文件
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;

            # 静态文件缓存
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
                proxy_pass http://frontend;
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }

        # 健康检查
        location /health {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
        }

        # 指标接口
        location /metrics {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;

            # 限制访问
            allow 10.0.0.0/8;
            deny all;
        }
    }
}
```

### 5.2 速率限制配置

在 `nginx.conf` 的 `http` 块中添加：

```nginx
# 速率限制 zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

---

## 6. 监控与日志

### 6.1 PM2 日志

```bash
# 查看日志
pm2 logs attribution-backend

# 实时监控
pm2 monit

# 查看进程状态
pm2 list
pm2 info attribution-backend
```

### 6.2 Docker 日志

```bash
# 查看所有日志
docker-compose -f docker-compose.prod.yml logs

# 查看特定服务
docker-compose -f docker-compose.prod.yml logs backend

# 实时日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 6.3 健康检查

```bash
# 后端健康检查
curl https://api.your-domain.com/api/health

# 响应示例
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "vectorDb": "connected",
    "llm": "available"
  }
}
```

### 6.4 Prometheus 指标

```bash
# 访问指标
curl https://api.your-domain.com/metrics
```

---

## 7. 备份与恢复

### 7.1 数据库备份

```bash
# 创建备份脚本
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR=/backups
DB_NAME=attribution

# PostgreSQL 备份
pg_dump -h localhost -U postgres -d $DB_NAME | gzip > $BACKUP_DIR/postgres_$DATE.sql.gz

# 保留最近 30 天的备份
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x backup.sh
```

### 7.2 定时备份 (cron)

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 3 点执行备份
0 3 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

### 7.3 恢复数据

```bash
# 解压并恢复
gunzip < postgres_20240625_030000.sql.gz | psql -h localhost -U postgres -d attribution
```

### 7.4 向量数据库备份

```bash
# Qdrant 数据备份
docker exec attribution-qdrant sh -c "tar -czf /backup/qdrant_$(date +%Y%m%d).tar.gz /qdrant/storage"

# 恢复
docker exec -i attribution-qdrant sh -c "tar -xzf - -C /" < qdrant_backup.tar.gz
```

---

## 8. 安全配置

### 8.1 环境变量安全

```bash
# 不要提交 .env 到 Git
echo ".env" >> .gitignore
echo ".env.*" >> .gitignore

# 生产环境使用 Docker Secret 或 Vault
```

### 8.2 数据库安全

```sql
-- 创建应用专用用户
CREATE USER app_user WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE attribution TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- 启用 SSL
ALTER DATABASE attribution SET ssl = on;
```

### 8.3 防火墙配置

```bash
# 只开放必要端口
sudo ufw allow 22   # SSH
sudo ufw allow 80   # HTTP
sudo ufw allow 443  # HTTPS

# 禁止外部访问数据库
sudo ufw deny 5432
sudo ufw deny 6379
```

### 8.4 定期安全更新

```bash
# 创建更新脚本
cat > security-update.sh << 'EOF'
#!/bin/bash
apt-get update && apt-get upgrade -y
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d
EOF

# 每周执行
crontab -e
0 4 * * 0 /path/to/security-update.sh
```

---

## 9. 故障排查

### 9.1 服务启动失败

```bash
# 检查 Docker 日志
docker-compose -f docker-compose.prod.yml logs backend

# 检查端口占用
netstat -tlnp | grep 3000

# 检查依赖
docker exec -it attribution-backend pnpm prisma --version
```

### 9.2 数据库连接失败

```bash
# 检查数据库健康
docker exec -it attribution-postgres pg_isready

# 测试连接
docker exec -it attribution-backend sh -c "nc -zv postgres 5432"
```

### 9.3 前端 502 错误

```bash
# 检查 Nginx 日志
docker logs attribution-nginx --tail 100

# 检查上游服务
curl http://backend:3000/api/health
```

---

## 相关文档

- [架构文档](./architecture.md)
- [API 文档](./api.md)
- [快速开始](./getting-started.md)
