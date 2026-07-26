# 服务器部署文档（Deploy Server Guide）

> 本文档指导如何将团队管理平台部署到老师的服务器上，完成从代码上传到系统运行的完整流程。

---

## 目录

1. [服务器最低配置建议](#1-服务器最低配置建议)
2. [Docker / Docker Compose 安装](#2-docker--docker-compose-安装)
3. [上传代码到服务器](#3-上传代码到服务器)
4. [配置生产环境变量](#4-配置生产环境变量)
5. [初始化数据库](#5-初始化数据库)
6. [创建管理员账号](#6-创建管理员账号)
7. [运行数据库迁移](#7-运行数据库迁移)
8. [启动全部服务](#8-启动全部服务)
9. [如何访问系统](#9-如何访问系统)
10. [如何查看日志](#10-如何查看日志)
11. [如何重启服务](#11-如何重启服务)
12. [如何备份数据库](#12-如何备份数据库)
13. [如何恢复数据库](#13-如何恢复数据库)
14. [常见问题](#14-常见问题)

---

## 1. 服务器最低配置建议

| 项目 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 2 核 | 4 核 |
| 内存 | 2 GB | 4 GB |
| 磁盘 | 20 GB | 50 GB SSD |
| 操作系统 | Ubuntu 22.04 / CentOS 8+ | Ubuntu 22.04 LTS |
| 网络 | 有公网 IP，开放 80/443 端口 | 有域名 + SSL 证书 |

> 如果只演示不长期使用，2 核 2GB 的学生云服务器即可。

---

## 2. Docker / Docker Compose 安装

### 2.1 安装 Docker（Ubuntu）

```bash
# 更新包索引
sudo apt update

# 安装必要依赖
sudo apt install -y ca-certificates curl gnupg lsb-release

# 添加 Docker 官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
docker compose version
```

### 2.2 安装 Docker Compose（如果版本不带 plugin）

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

---

## 3. 上传代码到服务器

### 方法一：通过 Git 克隆（推荐）

```bash
# 在服务器上
cd /opt
git clone <你的仓库地址> team-management
cd team-management
```

### 方法二：通过 SCP 上传

```bash
# 在本地机器上执行（将代码打包上传）
scp -r ./团队管理软件 user@server-ip:/opt/team-management
```

### 方法三：通过 rsync 同步（排除不需要的文件）

```bash
rsync -avz --exclude='node_modules' --exclude='__pycache__' \
  --exclude='.git' --exclude='backend/media' \
  ./团队管理软件/ user@server-ip:/opt/team-management/
```

---

## 4. 配置生产环境变量

### 4.1 生成密钥

在服务器上执行以下命令生成所需密钥：

```bash
# 生成 Django SECRET_KEY
python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 生成 Fernet 加密密钥（用于敏感资料加密）
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

> 如果服务器没有安装 Python，可以在本地生成后复制过去。密钥是随机字符串，在哪里生成都可以。

### 4.2 创建生产环境变量文件

```bash
cd /opt/team-management/deploy

# 复制模板
cp env/backend.prod.env.example env/backend.prod.env

# 编辑填写真实值
nano env/backend.prod.env
```

必须修改的项：

```ini
# Django 密钥（上一步生成的 SECRET_KEY）
DJANGO_SECRET_KEY=django-insecure-xxxxxxxxxxxxxxxxxxxxx

# 数据库密码（设一个强密码）
DB_PASSWORD=YourStrongDBPassword2026

# 字段加密密钥（上一步生成的 Fernet key）
FIELD_ENCRYPTION_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 允许访问的域名或 IP
ALLOWED_HOSTS=your-domain.com,123.45.67.89

# CORS 允许的前端来源
CORS_ALLOWED_ORIGINS=http://your-domain.com,http://123.45.67.89

# SSL 部署前设为 False
SECURE_SSL_REDIRECT=False
```

> 警告：`FIELD_ENCRYPTION_KEY` 一旦设置后不可更改，否则所有已加密的敏感资料将无法解密。请额外备份此密钥。

---

## 5. 初始化数据库

PostgreSQL 由 Docker Compose 自动启动并初始化，无需手动创建数据库。

首次启动时，`docker-compose.prod.yml` 中的 postgres 容器会自动：
- 创建 `team_management` 数据库
- 创建 `postgres` 用户并设置密码（从环境变量读取）

如果需要手动初始化（非 Docker 场景）：

```bash
sudo -u postgres psql
CREATE DATABASE team_management;
CREATE USER team_user WITH PASSWORD 'YourStrongPassword';
GRANT ALL PRIVILEGES ON DATABASE team_management TO team_user;
\q
```

---

## 6. 创建管理员账号

在 Docker 容器中创建超级管理员：

```bash
cd /opt/team-management/deploy

# 进入后端容器执行
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# 或创建演示管理员 + 演示数据
docker compose -f docker-compose.prod.yml exec backend python manage.py seed_demo_data --clean --force
```

---

## 7. 运行数据库迁移

数据库迁移由后端容器的 entrypoint 自动执行。如需手动执行：

```bash
cd /opt/team-management/deploy

# 执行迁移
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate

# 收集静态文件
docker compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

---

## 8. 启动全部服务

### 8.1 启动全部服务

```bash
cd /opt/team-management/deploy

# 构建并启动全部服务
docker compose -f docker-compose.prod.yml up -d --build

# 查看服务状态
docker compose -f docker-compose.prod.yml ps
```

启动的服务列表：

| 服务 | 容器名 | 端口 | 说明 |
|------|--------|------|------|
| PostgreSQL | team_postgres_prod | 内部 5432 | 数据库，不暴露到宿主机 |
| Redis | team_redis_prod | 内部 6379 | 缓存/消息队列，不暴露 |
| Backend (gunicorn) | team_backend_prod | 内部 8000 | Django 后端 |
| Celery Worker | team_celery_worker | 无 | 异步任务、邮件与报表执行 |
| Celery Beat | team_celery_beat | 无 | 定时提醒与定时报表调度 |
| Frontend (builder) | team_frontend_builder | 无 | 构建前端 dist 后退出 |
| Nginx | team_nginx_prod | 80, 443 | 反向代理 + SPA 托管 |

### 8.2 检查 Celery

```bash
# Worker 与 Beat 已由生产编排默认启动
docker compose -f docker-compose.prod.yml ps celery-worker celery-beat
```

### 8.3 验证服务健康

```bash
# 检查所有容器状态
docker compose -f docker-compose.prod.yml ps

# 检查后端健康
curl http://localhost/api/v1/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"admin123456"}'
```

---

## 9. 如何访问系统

### 9.1 通过 IP 访问（无域名）

```
http://<服务器IP>/
```

### 9.2 通过域名访问

1. 在域名服务商处添加 A 记录，指向服务器 IP
2. 确保 `env/backend.prod.env` 中 `ALLOWED_HOSTS` 包含域名
3. 确保 `CORS_ALLOWED_ORIGINS` 包含 `http://your-domain.com`
4. 访问 `http://your-domain.com/`

### 9.3 配置 HTTPS（推荐）

```bash
# 1. 获取 SSL 证书（以 Let's Encrypt 为例）
sudo apt install certbot
sudo certbot certonly --standalone -d your-domain.com

# 2. 复制证书到 Nginx 目录
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/nginx/ssl/key.pem

# 3. 编辑 deploy/nginx/default.prod.conf，取消 HTTPS server 块的注释

# 4. 在 env/backend.prod.env 中设置
SECURE_SSL_REDIRECT=True

# 5. 重启 Nginx
docker compose -f docker-compose.prod.yml restart nginx
```

---

## 10. 如何查看日志

```bash
cd /opt/team-management/deploy

# 查看所有服务日志（最近 100 行）
docker compose -f docker-compose.prod.yml logs --tail=100

# 只看后端日志
docker compose -f docker-compose.prod.yml logs --tail=100 backend

# 只看 Nginx 日志
docker compose -f docker-compose.prod.yml logs --tail=100 nginx

# 只看数据库日志
docker compose -f docker-compose.prod.yml logs --tail=100 postgres

# 实时跟踪日志
docker compose -f docker-compose.prod.yml logs -f backend

# 查看 Celery 日志
docker compose -f docker-compose.prod.yml logs -f celery-worker celery-beat
```

---

## 11. 如何重启服务

```bash
cd /opt/team-management/deploy

# 重启单个服务
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart nginx

# 重启全部服务
docker compose -f docker-compose.prod.yml restart

# 停止全部服务
docker compose -f docker-compose.prod.yml down

# 停止并删除数据卷（危险！会丢失数据）
docker compose -f docker-compose.prod.yml down -v
```

### 更新代码后重新部署

```bash
cd /opt/team-management

# 拉取最新代码
git pull origin main

# 重新构建并启动
cd deploy
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 12. 如何备份数据库

生产备份必须同时包含数据库、媒体和 SHA-256 清单。详见
[备份恢复文档](./BACKUP_GUIDE.md)，快速执行：

```bash
cd /opt/team-management
sudo scripts/backup.sh
find /opt/backups/team-management -maxdepth 2 -type f -ls
```

---

## 13. 如何恢复数据库

不要直接覆盖正在运行的生产数据库。先对完整备份集执行隔离恢复演练：

```bash
/opt/team-management/scripts/verify_backup.sh \
  /opt/backups/team-management/manifests/backup_20260726T030000Z.sha256
```

真实灾难恢复采用新数据库实例和新媒体卷，经两人复核后再切换连接，具体步骤见
[备份恢复文档](./BACKUP_GUIDE.md#8-灾难恢复原则)。

---

## 14. 常见问题

### Q1: 访问系统显示 502 Bad Gateway

后端尚未启动完成。检查后端状态：

```bash
docker compose -f docker-compose.prod.yml ps backend
docker compose -f docker-compose.prod.yml logs --tail=50 backend
```

常见原因：环境变量未正确配置（如 SECRET_KEY、DB_PASSWORD 为空）。检查 `env/backend.prod.env` 文件。

### Q2: 前端页面白屏

前端构建可能失败。重新构建前端：

```bash
docker compose -f docker-compose.prod.yml up -d --build frontend
```

### Q3: 上传文件失败（413 Request Entity Too Large）

Nginx 默认限制已在配置中设为 100MB。如仍报错，检查 `deploy/nginx/default.prod.conf` 中 `client_max_body_size` 配置。

### Q4: Celery 定时通知不工作

生产编排默认启动 Celery Worker 与 Beat。先检查 `docker compose -f docker-compose.prod.yml ps celery-worker celery-beat`，再查看两项服务日志；任一服务未运行都会影响定时提醒或定时报表。

### Q5: 磁盘空间不足

```bash
# 清理 Docker 未使用的镜像和容器
docker system prune -a

# 检查磁盘使用
df -h

# 检查 Docker 磁盘使用
docker system df
```

### Q6: 如何修改管理员密码

```bash
docker compose -f docker-compose.prod.yml exec backend python manage.py changepassword admin@demo.com
```

### Q7: 如何更新代码后重新部署

```bash
cd /opt/team-management
git pull origin main
cd deploy
docker compose -f docker-compose.prod.yml up -d --build
# 等待服务健康后执行迁移
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

---

> 文档版本：v1.0
> 维护者：团队管理软件项目组
