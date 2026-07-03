# syntax=docker/dockerfile:1
# ============================================================
# Vue 3 前端 Dockerfile（多阶段构建）
# 构建上下文: ../frontend
#   - dev    阶段: 开发模式 Vite HMR（docker-compose.yml 使用 target: dev）
#   - build  阶段: 生产构建，生成 dist/（docker-compose.prod.yml 使用 target: build）
#   - serve  阶段: 独立 nginx 托管 SPA（供独立部署/预览使用）
# ============================================================

# ---- Stage 1: dev（开发模式）----
FROM node:20-alpine AS dev
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# ---- Stage 2: build（生产构建）----
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

# ---- Stage 3: serve（独立 nginx 托管 SPA）----
FROM nginx:alpine AS serve
COPY --from=build /app/dist /usr/share/nginx/html
# 内嵌 SPA 路由配置（try_files 支持 Vue Router history 模式）
RUN printf 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    client_max_body_size 100m;\n\
\n\
    location / {\n\
        root /usr/share/nginx/html;\n\
        index index.html;\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
\n\
    gzip on;\n\
    gzip_vary on;\n\
    gzip_min_length 1024;\n\
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;\n\
}\n' > /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
