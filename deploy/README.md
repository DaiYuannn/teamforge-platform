# 团队管理平台 · Docker 部署配置

基于 **Django + PostgreSQL + Redis + Nginx + Vue 3** 技术栈的容器化部署方案，提供开发与生产两套环境。

---

## 一、目录结构

```
deploy/
├── docker-compose.yml            # 开发环境编排文件
├── docker-compose.prod.yml       # 生产环境编排文件
├── dockerfiles/
│   ├── backend.Dockerfile        # 后端镜像（dev/prod 共用，构建参数区分依赖）
│   └── frontend.Dockerfile       # 前端镜像（多阶段：dev / build / serve）
├── nginx/
│   ├── default.conf              # 开发环境 Nginx 反向代理配置
│   ├── default.prod.conf         # 生产环境 Nginx 配置（SPA + API 代理 + 静态资源）
│   └── ssl/                      # SSL 证书目录（生产启用 HTTPS 时使用）
├── env/
│   ├── backend.env.example       # 后端开发环境变量模板
│   ├── backend.prod.env.example  # 后端生产环境变量模板
│   ├── frontend.env.example      # 前端环境变量模板
│   ├── backend.env               # 后端开发环境变量（自动生成，git 忽略）
│   └── frontend.env              # 前端环境变量（自动生成，git 忽略）
├── start-dev.sh / start-dev.ps1  # 开发环境一键启动脚本
├── start-prod.sh / start-prod.ps1# 生产环境一键部署脚本
├── .gitignore
└── README.md
```

> Dockerfile 的构建上下文分别为上级的 `../backend` 与 `../frontend`，因此目录可独立维护。

---

## 二、环境要求

| 组件 | 版本要求 |
|------|----------|
| Docker | 20.10+（需启用 BuildKit，用于 Dockerfile heredoc 语法）|
| Docker Compose | v2.17+（生产环境使用 `service_completed_successfully` 条件）|
| 操作系统 | Windows / macOS / Linux 均可 |

Windows 用户使用 Docker Desktop 即可。若 BuildKit 未启用，可在 PowerShell 设置：
```powershell
$env:DOCKER_BUILDKIT=1
```

---

## 三、开发环境

### 架构

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | postgres:16-alpine | 5432 | 数据库 |
| redis | redis:7-alpine | 6379 | 缓存 / Celery broker |
| backend | 自构建 (python:3.11-slim) | 8000 | Django runserver 热重载 |
| frontend | 自构建 (node:20-alpine) | 3000 | Vite 开发服务器 HMR |
| nginx | nginx:alpine | 80 | 反向代理统一入口 |

### 启动方式

**方式一：一键脚本（推荐）**

```bash
# Linux / macOS / Git Bash
bash start-dev.sh

# Windows PowerShell
.\start-dev.ps1
```

脚本会自动：复制环境变量文件 → 构建镜像 → 启动服务 → 等待数据库就绪 → 执行迁移 → 询问是否创建超级用户。

**方式二：手动命令**

```bash
cp env/backend.env.example env/backend.env
cp env/frontend.env.example env/frontend.env
docker compose build
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

### 访问地址

| 入口 | 地址 |
|------|------|
| 前端（Nginx 统一入口，推荐） | http://localhost |
| 前端（Vite 直连） | http://localhost:3000 |
| 后端 API | http://localhost:8000/api/v1/ |
| Django Admin | http://localhost:8000/admin/ |

> 开发环境通过 Nginx（80 端口）统一访问，`/api/`、`/admin/`、`/static/`、`/media/` 代理到后端，其余请求代理到前端 Vite（支持 HMR WebSocket）。

---

## 四、生产环境

### 架构

| 服务 | 镜像 | 端口 | 说明 |
|------|------|------|------|
| postgres | postgres:16-alpine | 不暴露 | 数据库 |
| redis | redis:7-alpine | 不暴露 | 缓存 / Celery broker |
| backend | 自构建 | 8000(内部) | gunicorn + migrate + collectstatic |
| celery-worker | 同 backend | - | 架构预留（profile: celery）|
| celery-beat | 同 backend | - | 架构预留（profile: celery）|
| frontend | 自构建 | - | 构建产物输出到共享卷后退出 |
| nginx | nginx:alpine | 80 / 443 | 反向代理 + SPA 托管 |

### 部署方式

**方式一：一键脚本**

```bash
# Linux / macOS / Git Bash
bash start-prod.sh

# Windows PowerShell
.\start-prod.ps1
```

脚本会自动：检查/生成生产环境变量 → 构建镜像 → 启动服务。

**方式二：手动命令**

```bash
cp env/backend.prod.env.example env/backend.prod.env
# ⚠️ 编辑 env/backend.prod.env，修改 DJANGO_SECRET_KEY、DB_PASSWORD、FIELD_ENCRYPTION_KEY
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### 启用 Celery（架构预留）

Celery 依赖尚未加入 `requirements/prod.txt`，启用前需先添加 `celery` 到该文件并重新构建后端镜像：

```bash
# 1. 在 backend/requirements/prod.txt 添加 celery==5.x
# 2. 启用 celery 服务
docker compose -f docker-compose.prod.yml --profile celery up -d
```

### 启用 HTTPS

1. 将证书放入 `nginx/ssl/`（`cert.pem` 与 `key.pem`）
2. 取消 `nginx/default.prod.conf` 中 HTTPS `server` 块的注释
3. 在 `env/backend.prod.env` 中设置 `SECURE_SSL_REDIRECT=True`
4. 重启 nginx：`docker compose -f docker-compose.prod.yml restart nginx`

---

## 五、环境变量说明

### 后端（backend.env / backend.prod.env）

| 变量 | 开发默认 | 生产要求 | 说明 |
|------|----------|----------|------|
| `DJANGO_SETTINGS_MODULE` | config.settings.dev | config.settings.prod | Django 配置模块 |
| `DJANGO_SECRET_KEY` | insecure-dev-key | **必须随机** | Django 密钥 |
| `DEBUG` | True | False | 调试模式 |
| `ALLOWED_HOSTS` | * | 域名列表 | 允许的主机 |
| `DB_NAME` | team_management | team_management | 数据库名 |
| `DB_USER` | postgres | postgres | 数据库用户 |
| `DB_PASSWORD` | postgres | **必须强密码** | 数据库密码（须与 compose 中 postgres 一致）|
| `DB_HOST` | postgres | postgres | 数据库主机（容器名）|
| `DB_PORT` | 5432 | 5432 | 数据库端口 |
| `CELERY_BROKER_URL` | redis://redis:6379/0 | 同左 | Celery broker |
| `CELERY_RESULT_BACKEND` | redis://redis:6379/1 | 同左 | Celery 结果后端 |
| `CORS_ALLOWED_ORIGINS` | localhost 列表 | 域名列表 | CORS 允许来源 |
| `FIELD_ENCRYPTION_KEY` | 留空(自动生成) | **必须固定** | Fernet 加密密钥 |
| `SECURE_SSL_REDIRECT` | - | True/False | HTTPS 重定向（仅生产）|
| `EMAIL_HOST` | smtp.qq.com | 按需 | 邮件主机 |
| `EMAIL_PORT` | 587 | 按需 | 邮件端口 |
| `EMAIL_HOST_USER` | 空 | 按需 | 邮件账号 |
| `EMAIL_HOST_PASSWORD` | 空 | 按需 | 邮件密码 |

> 生成密钥的命令：
> ```bash
> # Django SECRET_KEY
> python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
> # Fernet 加密密钥
> python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
> ```

### 前端（frontend.env）

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_BASE_URL` | /api/v1 | 前端请求 API 的基础前缀（由 Nginx 代理到后端）|

---

## 六、常用 Docker 命令

### 开发环境

```bash
# 启动 / 停止 / 重启
docker compose up -d
docker compose stop
docker compose restart

# 查看日志（实时跟踪）
docker compose logs -f
docker compose logs -f backend

# 进入容器
docker compose exec backend bash
docker compose exec frontend sh

# 执行 Django 管理命令
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py shell

# 重建镜像（修改依赖后）
docker compose build

# 完全清理（含数据卷，谨慎！）
docker compose down -v
```

### 生产环境

```bash
# 启动 / 停止
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml down

# 查看日志
docker compose -f docker-compose.prod.yml logs -f

# 重新构建并更新某个服务
docker compose -f docker-compose.prod.yml build backend
docker compose -f docker-compose.prod.yml up -d backend

# 启用 Celery
docker compose -f docker-compose.prod.yml --profile celery up -d

# 查看服务状态
docker compose -f docker-compose.prod.yml ps
```

---

## 七、关键设计说明

1. **入口点脚本内嵌于 `/usr/local/bin`**：开发模式挂载 `../backend:/app` 会覆盖 `/app` 下的内容，故 entrypoint 放在 `/usr/local/bin/docker-entrypoint.sh` 以避免被覆盖。它在启动前执行 `migrate`，生产模式额外执行 `collectstatic`。

2. **前端构建产物共享**：生产环境中 `frontend` 服务（`target: build` 阶段）将 `dist/` 拷贝到 `frontend_dist` 共享卷后退出，`nginx` 通过 `service_completed_successfully` 依赖条件确保在其完成后启动并托管。

3. **SPA 路由支持**：Nginx 通过 `try_files $uri $uri/ /index.html` 支持 Vue Router history 模式。

4. **文件上传限制**：Nginx 配置 `client_max_body_size 100m`。

5. **环境变量名对齐项目**：本配置中的变量名（`DJANGO_SECRET_KEY`、`FIELD_ENCRYPTION_KEY`、`CELERY_BROKER_URL` 等）与 `backend/config/settings/*.py` 实际读取的名称一致。为支持 Docker 部署，对 `dev.py`（数据库改读环境变量）与 `prod.py`（`SECURE_SSL_REDIRECT` 改读环境变量）做了向后兼容的最小调整——本地开发无环境变量时仍使用原默认值。
