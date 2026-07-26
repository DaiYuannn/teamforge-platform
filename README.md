# TeamForge Platform v2.0

团队项目管理平台，面向竞赛项目、团队协作、任务、经费、文件资料、贡献记录、知识产权流程、敏感资料审批与操作审计的一体化管理场景。

## 功能概览

- 项目与成员管理
- 多赛事/竞赛项目管理
- 任务协作与进度跟踪
- 经费预算、报销与票据管理
- 文件资料归档
- 贡献记录与成员排序
- 知识产权申请流程
- 敏感资料脱敏、审批与限时查看
- 通知中心与操作日志
- 账户级主题、布局与通知偏好
- 票据 OCR、定时报表与实时 SSE 通知
- 带快照、附件和校验清单的演示数据备份恢复
- Docker 本地/线上部署配置

## 技术栈

- Backend: Django 5, Django REST Framework, SimpleJWT, PostgreSQL, Celery
- Frontend: Vue 3, Vite, TypeScript, Pinia, Element Plus, ECharts
- Infrastructure: Docker Compose, PostgreSQL, Redis, Nginx, Gunicorn

## 目录结构

```text
backend/      Django 后端
frontend/     Vue 前端
deploy/       部署配置与 Dockerfile
nginx/        本地 Docker Nginx 配置
scripts/      部署和运维脚本
docs/         项目文档
references/   需求、验证报告、上下文和规划资料
```

## 本地开发

后端：

```powershell
cd backend
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py runserver
```

前端：

```powershell
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://127.0.0.1:3000`，后端默认运行在 `http://127.0.0.1:8000`。完整演示数据使用：

```powershell
cd backend
python manage.py seed_demo_data --clean --force
```

## Docker 部署

复制并填写环境变量文件：

```powershell
Copy-Item .env.production.example .env.docker
```

构建并启动：

```powershell
docker compose -p team_management_local build
docker compose -p team_management_local up -d
```

初始化：

```powershell
docker compose -p team_management_local exec backend python manage.py migrate
docker compose -p team_management_local exec backend python manage.py collectstatic --noinput
docker compose -p team_management_local exec backend python manage.py check
```

## 安全说明

以下文件不会提交到 Git：

- `.env.docker`
- `deploy/env/*.env`
- `backend/media/`
- `backend/test_media/`
- `backend/demo_backups/`
- `backend/*.dump`
- `backend/media.before_v2_seed/`
- `.docker-config/`
- `frontend/node_modules/`
- `frontend/dist/`

请不要把真实数据库、真实 media、生产密钥或 Docker volume 上传到仓库。
