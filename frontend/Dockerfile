# ====================================================
# Stage 1: 构建前端静态文件
# ====================================================
FROM node:20-alpine AS builder

WORKDIR /build

COPY package.json package-lock.json* ./
RUN npm ci --registry=https://registry.npmmirror.com

COPY . .
# 跳过 vue-tsc 类型检查（CI 中单独做），只构建产物
RUN npx vite build

# ====================================================
# Stage 2: nginx 静态服务 + API 反代
# ====================================================
FROM nginx:1.27-alpine AS runtime

ENV TZ=Asia/Shanghai

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# 复制构建产物
COPY --from=builder /build/dist /usr/share/nginx/html

# 复制 nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
