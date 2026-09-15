# 🚀 数据库服务部署指南

> 目标服务器：`8.148.204.54`（Linux）
> 部署方式：Docker Compose（原生命令）
> 部署路径：`/home/project/attribution/`
> 运行用户：root（调试阶段）
> 包含服务：PostgreSQL 16 + Redis 7
>
> **当前阶段**：仅部署数据库到服务器，本地后端直连服务器数据库。Backend 暂不部署。

---

## 📋 服务器需安装

| 软件 | 版本 | 用途 |
|------|------|------|
| Docker | 24.0+ | 容器运行时 |
| Docker Compose | v2.0+ | 容器编排（`docker compose` 子命令） |

---

## 🔧 部署步骤

### 1. SSH 登录服务器

```bash
ssh root@8.148.204.54
```

### 2. 安装 Docker

阿里云 ECS 在国内，直接用 `get.docker.com` 可能连接被重置。用阿里云镜像：

```bash
# Ubuntu/Debian 一键安装（阿里云镜像）
curl -fsSL https://get.docker.com | bash -s -- --mirror Aliyun
systemctl enable --now docker

# 配置镜像加速器（国内拉 postgres/redis 镜像必备）
mkdir -p /etc/docker
tee /etc/docker/daemon.json <<-'EOF'
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me"
  ]
}
EOF
systemctl restart docker

# 验证
docker --version
docker compose version
```

### 3. 创建部署目录

```bash
mkdir -p /home/project/attribution
cd /home/project/attribution
```

### 4. 上传部署文件

只需要上传 **2 项**（compose 文件 + postgres 目录）：

```bash
# 在本地项目根目录下执行
scp backend/docker-compose.yml \
    root@8.148.204.54:/home/project/attribution/

scp -r backend/postgres \
    root@8.148.204.54:/home/project/attribution/
```

上传完后服务器目录结构：

```
/home/project/attribution/
├── docker-compose.yml         # 部署文件
└── postgres/                  # PG 初始化脚本和配置
    ├── initdb/01-init.sql
    └── conf/postgresql.conf
```

> ⚠️ **不要上传 backend/ 下的 `.env`**！那是本地后端配置，服务器不需要。

### 5. 启动数据库服务

```bash
ssh root@8.148.204.54
cd /home/project/attribution

# 直接启动 - 账户密码已写在 docker-compose.yml 里
docker compose up -d
```

输出示例：

```
[+] Running 3/3
 ✔ Network attribution-net        Created
 ✔ Volume attribution-postgres-data  Created
 ✔ Container attribution-postgres  Started
 ✔ Container attribution-redis     Started
```

### 6. 验证服务

```bash
# 查看运行状态（应该都是 "healthy"）
docker compose ps
# NAME                  STATUS
# attribution-postgres  Up X minutes (healthy)
# attribution-redis     Up X minutes (healthy)

# 测试 PG 连接
docker exec -it attribution-postgres psql -U zhouch -d attribution

# 测试 Redis 连接
docker exec -it attribution-redis redis-cli -a zhouchenhui ping
# (输出) PONG
```

> 🔑 账户密码：PG 用 `zhouch / zhouchenhui`，Redis 密码也是 `zhouchenhui`
> 已与本地 `backend/.env` 中的 `DATABASE_URL` / `REDIS_URL` 保持一致。

### 7. 开放阿里云安全组端口

数据库端口必须能从公网访问（本地后端要连）。去阿里云控制台：

**ECS → 安全组 → 入方向规则 → 手动添加**：

| 端口 | 协议 | 来源 | 用途 |
|------|------|------|------|
| 5432 | TCP | `0.0.0.0/0`（或你的本地公网 IP） | PostgreSQL |
| 6379 | TCP | `0.0.0.0/0`（或你的本地公网 IP） | Redis |

> 💡 更安全：把来源限制为你本地公网 IP。查询地址：<https://ip.sb>

### 8. 常用运维命令

---

## 📦 数据卷（Volume）说明

使用 Docker **命名卷**（named volume），无需手动管理路径：

| 卷名 | 容器内路径 | 物理位置 | 内容 |
|------|-----------|---------|------|
| `attribution-postgres-data` | `/var/lib/postgresql/data` | `/var/lib/docker/volumes/attribution-postgres-data/_data` | PG 数据库文件 |
| `attribution-redis-data` | `/data` | `/var/lib/docker/volumes/attribution-redis-data/_data` | RDB + AOF |

**优势**：

- ✅ Docker 自动处理权限
- ✅ 卷与部署路径解耦（项目目录删了数据还在）
- ✅ 备份迁移方便

**查看卷信息**：

```bash
docker volume inspect attribution-postgres-data
docker volume ls
```

**重置数据（⚠️ 会删全部数据）**：

```bash
docker compose down
docker volume rm attribution-postgres-data attribution-redis-data
docker compose up -d
```

---

## 🔁 常用运维命令

```bash
cd /home/project/attribution

# 启动（后台）
docker compose up -d

# 停止
docker compose stop

# 停止并移除容器（保留数据卷）
docker compose down

# 重启
docker compose restart

# 查看状态
docker compose ps

# 实时日志
docker compose logs -f

# 单服务日志
docker compose logs -f postgres

# 进入 PostgreSQL 命令行
docker exec -it attribution-postgres psql -U postgres -d attribution

# 进入 Redis 命令行
docker exec -it attribution-redis redis-cli -a "$REDIS_PASSWORD"
```

---

## 💾 备份与还原

### 手动备份 PostgreSQL

```bash
# 在服务器上
docker exec attribution-postgres pg_dump \
    -U postgres \
    -d attribution \
    --no-owner --clean --if-exists \
    > /home/project/attribution/backup-$(date +%Y%m%d-%H%M%S).sql

# 查看备份
ls -lh /home/project/attribution/backup-*.sql
```

### 自动备份（cron）

```bash
crontab -e

# 每天凌晨 3 点备份（保留 7 天）
0 3 * * * cd /home/project/attribution && \
    /usr/bin/docker exec attribution-postgres pg_dump \
        -U postgres -d attribution --no-owner --clean --if-exists \
        > /home/project/attribution/backup-$(date +\%Y\%m\%d).sql && \
    find /home/project/attribution/backup-*.sql -mtime +7 -delete
```

### 还原备份

```bash
cat /home/project/attribution/backup-20260915.sql | \
    docker exec -i attribution-postgres psql -U postgres -d attribution
```

### 备份整个数据卷（更彻底）

```bash
# 备份 PG 卷
docker run --rm \
    -v attribution-postgres-data:/source:ro \
    -v /home/project/attribution:/backup \
    alpine tar czf /backup/postgres-volume-$(date +%Y%m%d).tar.gz -C /source .

# 还原 PG 卷
docker run --rm \
    -v attribution-postgres-data:/target \
    -v /home/project/attribution:/backup \
    alpine sh -c "tar xzf /backup/postgres-volume-20260915.tar.gz -C /target"
```

---

## 🔌 本地后端连接

`backend/.env` 已经预设好服务器连接信息：

```env
DATABASE_URL=postgresql+asyncpg://zhouch:zhouchenhui@8.148.204.54:5432/attribution
REDIS_URL=redis://:zhouchenhui@8.148.204.54:6379/0
```

> ✅ 账户密码已与服务器 `docker-compose.yml` 保持一致，**无需手动改 .env**。

**测试连通性**：

```bash
# 测试 PG
psql "postgresql://zhouch:zhouchenhui@8.148.204.54:5432/attribution" -c "SELECT version();"

# 测试 Redis
redis-cli -h 8.148.204.54 -p 6379 -a zhouchenhui ping
# (输出) PONG
```

**启动本地后端**：

```bash
cd /home/dustp/codes/Attribution_Analysis/backend
source .venv/bin/activate  # 或你用的虚拟环境
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🔒 安全建议

1. **限制来源 IP** - 阿里云安全组把 5432/6379 限制为**只允许你的本地公网 IP**
2. **不要提交含真实账户密码的 `docker-compose.yml`** - 部署到服务器后，那个文件里有真实账户 `zhouch`。如果要提交到 git，**先把这些账户密码删掉再 commit**
3. **定期备份** - 用上面的 cron 自动备份

---

## 🐛 故障排查

### 本地连不上服务器数据库

```bash
# 1. 服务器上端口监听正常吗？
ssh root@8.148.204.54 "nc -zv localhost 5432"
# → Connection to localhost 5432 port [tcp/postgresql] succeeded!

# 2. 本地测试连通性
nc -zv 8.148.204.54 5432
# 成功: Connection to 8.148.204.54 5432 port [tcp/postgresql] succeeded!
# 失败: Connection timed out  ← 安全组没放行

# 3. 服务器上能否本地连上 PG？
ssh root@8.148.204.54 \
    "docker exec attribution-postgres psql -U postgres -c 'SELECT version();'"

# 4. 密码是否匹配？
# 确认服务器 docker-compose.yml 里的密码 = 本地 backend/.env 里的密码
```

### 容器无法启动

```bash
cd /home/project/attribution
docker compose ps                      # 查看状态
docker compose logs postgres           # PG 日志
docker compose logs redis              # Redis 日志
```

常见原因：
- 5432/6379 端口被占用 → 检查服务器端口占用：`netstat -tlnp | grep -E '5432|6379'`
- 卷已存在但初始化失败 → `docker volume rm attribution-postgres-data`（⚠️ 删数据）

### 镜像拉取失败

```bash
# 检查加速器是否配置
cat /etc/docker/daemon.json

# 手动测试拉取
docker pull postgres:16-alpine
```

---

## 🚀 后续：部署 Backend

当需要把 Backend 也部署到服务器时，往 `docker-compose.yml` 里加 `backend` 服务即可。当前结构已为此预留。
