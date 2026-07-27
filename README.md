# TeamForge Platform v2.1.0

> 发布日期：2026-07-27

团队项目管理平台，面向竞赛项目、团队协作、任务、经费、文件资料、贡献记录、知识产权流程、敏感资料审批、数据分析与平台治理的一体化管理场景。

## 功能概览

- 项目与成员管理
- 多赛事/竞赛项目管理
- 任务检查清单、依赖、评论与项目协作工作台
- 经费预算、报销与票据管理
- 文件夹、标签、版本、分享、回收站与 Office 只读预览
- 贡献记录与成员排序
- 知识产权申请流程
- 敏感资料脱敏、审批与限时查看
- 通知中心与操作日志
- 账户级主色、浅色/深色/跟随系统/定时夜间模式、语言、布局与通知偏好
- 票据 OCR、定时报表与实时 SSE 通知
- 自定义看板、报表生成与智能周报
- 角色授权、审批流、自定义表单、外部平台与 Git 仓库管理
- 真实请求性能采样、标准 OpenAPI 契约与 axe-core 无障碍门禁
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

v2.1.0 升级包含用户明暗模式迁移 `users.0007_userpreference_schedule_end_and_more` 和语言偏好迁移 `users.0008_userpreference_language`；已有环境启动前必须执行 `python manage.py migrate`。

密码重置邮件中的链接由 `FRONTEND_URL` 生成。部署环境必须配置该变量及 `EMAIL_HOST`、`EMAIL_HOST_USER`、`EMAIL_HOST_PASSWORD`，否则用户无法收到可访问的重置链接。

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

工程质量检查：

```powershell
cd backend
python -m flake8 .
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py spectacular --file openapi.yml --validate
python -m pytest

cd ..\frontend
npm audit --audit-level=high
npm run lint
npm run type-check
npm run test
npm run build
npm run test:e2e
```

管理员可在 `/admin/engineering` 查看实时性能采样、版本化接口索引和质量门禁；标准 OpenAPI JSON 位于 `/api/v1/common/openapi/schema/`。

以上是本地发布验收入口，不代表远程 CI 或生产环境已执行。当前版本的最终通过数量和浏览器验收结论以 `CHANGELOG.md` 与 `VERSION.md` 的 v2.1.0 发布记录为准。

## Docker 部署

复制并填写环境变量文件：

```powershell
Copy-Item .env.docker.example .env.docker
```

构建并启动：

```powershell
docker compose --env-file .env.docker -p team_management_local build
docker compose --env-file .env.docker -p team_management_local up -d
```

初始化：

```powershell
docker compose --env-file .env.docker -p team_management_local exec backend python manage.py migrate
docker compose --env-file .env.docker -p team_management_local exec backend python manage.py collectstatic --noinput
docker compose --env-file .env.docker -p team_management_local exec backend python manage.py check
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
