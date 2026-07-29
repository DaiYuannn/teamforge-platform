# 小团队版服务器部署指南

本文只适用于 GitHub 分支 `codex/personal-small-team`。

- 仓库：`https://github.com/DaiYuannn/teamforge-platform.git`
- Docker Compose 项目名：`team_management_small`
- 编排文件：仓库根目录 `docker-compose.yml`
- 环境变量：仓库根目录 `.env.docker`

请始终使用同一个 Compose 项目名。更换 `-p team_management_small` 会创建另一套数据卷，看起来像数据丢失。

## 1. 部署前确认

服务器需要安装：

- Git
- Docker Engine
- Docker Compose v2（`docker compose version`）
- `curl`
- `openssl`

根编排占用宿主机端口 `80` 和 `127.0.0.1:6379`。如果同一台服务器已经运行主版或其他服务，仅更换 Compose 项目名不能解决端口冲突；请使用独立服务器，或另外编写 Compose override 和统一反向代理。

不要使用 `deploy/docker-compose.prod.yml` 并行部署小团队版。该文件写死了生产容器名，无法通过 `-p` 完成隔离。

## 2. 首次克隆分支

```bash
sudo install -d -o "$(id -un)" -g "$(id -gn)" /opt/team-management-small

git clone \
  --branch codex/personal-small-team \
  --single-branch \
  https://github.com/DaiYuannn/teamforge-platform.git \
  /opt/team-management-small

cd /opt/team-management-small
git branch --show-current
git log -1 --oneline
```

当前首个完整小团队数据版本的提交为：

```text
89477a3d feat: refresh small-team demo history
```

## 3. 配置生产环境

```bash
cd /opt/team-management-small
cp .env.docker.example .env.docker
chmod 600 .env.docker

# 生成 Django 密钥
openssl rand -base64 48 | tr -d '\n'
echo

# 生成 URL-safe Fernet 密钥
openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n'
echo

nano .env.docker
```

至少修改并核对：

```dotenv
DJANGO_SETTINGS_MODULE=config.settings.prod
DJANGO_SECRET_KEY=刚生成的随机强密钥
DEBUG=False

DB_NAME=team_management
DB_USER=postgres
DB_PASSWORD=新的随机强密码
DB_HOST=db
DB_PORT=5432

ALLOWED_HOSTS=你的域名,服务器IP,127.0.0.1
FRONTEND_URL=http://你的域名或服务器IP
CORS_ALLOWED_ORIGINS=http://你的域名或服务器IP

CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
NOTIFICATION_STREAM_REDIS_URL=redis://redis:6379/2
NOTIFICATION_STREAM_ENABLED=True

SECURE_SSL_REDIRECT=False
FIELD_ENCRYPTION_KEY=刚生成的Fernet密钥
```

`FIELD_ENCRYPTION_KEY` 必须离线备份并永久保持不变；丢失或变更后，已有敏感资料将无法解密。

初次仅通过 HTTP 验收时保持 `SECURE_SSL_REDIRECT=False`。当前版本没有配置 `SECURE_PROXY_SSL_HEADER`，通过外部 TLS 代理部署 HTTPS 时，不要只把该值改为 `True`；应先补充并验证代理协议头配置，避免重定向循环。

## 4. 首次构建、迁移和生成最终模拟数据

先在当前 shell 定义统一命令：

```bash
cd /opt/team-management-small

dc() {
  docker compose --env-file .env.docker -p team_management_small "$@"
}

dc config --quiet
dc build
dc up -d db redis

until dc exec -T db sh -c \
  'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
do
  sleep 2
done

dc exec -T redis redis-cli ping

dc run --rm --no-deps backend python manage.py migrate --noinput
dc run --rm --no-deps backend python manage.py collectstatic --noinput
dc run --rm --no-deps backend python manage.py check

dc run --rm --no-deps backend \
  python manage.py seed_demo_data --clean --force

dc up -d --remove-orphans
```

`seed_demo_data --clean --force` 会精准重建带专用标记的模拟账号、团队、项目、附件和关联数据。它不应删除非演示前缀的真实业务数据，但仍属于重置操作：只在全新小团队实例首次初始化，或明确要重置演示数据且已经完成备份时执行。

后续日常代码更新不要重复运行该种子命令，否则服务器上对演示记录所做的修改会被重置。

## 5. 验证最终数据

```bash
dc exec -T backend python manage.py shell -c "
from django.db.models import Count
from apps.users.models import User
from apps.projects.models import Project
from apps.competitions.models import Competition, CompetitionEvent
from apps.common.team_models import Team, TeamMember
from apps.files.models import FileAsset
from apps.finance.models import FinanceExpense, FinanceIncome
from apps.intellectual_property.models import IntellectualPropertyApplication as IP
from apps.users.management.commands.seed_demo_data import (
    DEMO_ACCOUNT_EMAILS,
    DEMO_IP_PREFIX,
    DEMO_PROJECT_PREFIX,
    DEMO_TEAM_CODE,
)

team = Team.objects.get(code=DEMO_TEAM_CODE)
projects = Project.all_objects.filter(code__startswith=DEMO_PROJECT_PREFIX)
ip = IP.objects.filter(application_code__startswith=DEMO_IP_PREFIX)

result = {
    'demo_accounts': User.objects.filter(email__in=DEMO_ACCOUNT_EMAILS).count(),
    'team_members': TeamMember.objects.filter(team=team).count(),
    'projects': projects.count(),
    'competition_events': CompetitionEvent.objects.filter(organization=team).count(),
    'competition_entries': Competition.objects.filter(project__in=projects).count(),
    'files': FileAsset.objects.filter(project__in=projects).count(),
    'competition_expenses': FinanceExpense.all_objects.filter(
        project__in=projects,
        competition_entry__isnull=False,
    ).count(),
    'competition_incomes': FinanceIncome.objects.filter(
        project__in=projects,
        competition_entry__isnull=False,
    ).count(),
    'ip_total': ip.count(),
    'ip_breakdown': list(
        ip.values('ip_type').annotate(count=Count('id')).order_by('ip_type')
    ),
}

assert result['demo_accounts'] == 47
assert result['team_members'] == 46
assert result['projects'] == 7
assert result['competition_events'] == 33
assert result['competition_entries'] == 109
assert result['files'] == 247
assert result['competition_expenses'] == 14
assert result['competition_incomes'] == 7
assert result['ip_total'] == 72
print(result)
print('small-team seed verified')
"
```

预期核心规模：

- 1 个全操作老师、3 个查看老师、5 个负责人、2 个平行主贡献者、35 个普通成员，另有 1 个技术管理员账号
- 7 个项目，其中 2 个历史获国金/国银后结项、5 个当前项目
- 33 个比赛届次、109 条项目参赛记录
- 247 个项目文件；不同项目、比赛和年份有独立计划书/PPT及版本
- 40 个专利、25 个软著、7 个科技查新
- 14 条关联比赛的模拟支出、7 条关联比赛的奖金收入

完整模拟账号、密码和浏览器验收步骤见 `docs/DEMO_GUIDE.md`。模拟密码是公开固定值，不能把未修改密码的模拟账号直接暴露到公网正式环境。

## 6. 服务健康检查

```bash
dc ps -a
dc exec -T backend python manage.py migrate --check

curl -fsS http://127.0.0.1/api/v1/common/health/ |
  python3 -c \
  "import json,sys; data=json.load(sys.stdin); assert data['data']['status']=='healthy'; print(data['data'])"

curl -fsSI http://127.0.0.1/

dc logs --tail=200 backend nginx celery_worker celery_beat db
```

`frontend` 是一次性构建容器，显示 `Exited (0)` 是正常结果。健康接口在部分依赖降级时仍可能返回 HTTP 200，因此必须检查 JSON 中的 `data.status`，不能只检查 HTTP 状态码。

登录入口：

```text
http://服务器IP/
```

## 7. 已有小团队服务器更新分支

先备份，再拉取代码。工作区存在本地修改时必须停止，不要使用 `git reset --hard` 覆盖服务器文件。

```bash
cd /opt/team-management-small

test -z "$(git status --porcelain)" || {
  echo "服务器仓库存在本地修改，停止更新"
  exit 1
}

OLD_SHA="$(git rev-parse HEAD)"
echo "更新前提交: $OLD_SHA"

git fetch --prune origin

if git show-ref --verify --quiet refs/heads/codex/personal-small-team
then
  git switch codex/personal-small-team
else
  git switch --track origin/codex/personal-small-team
fi

git pull --ff-only origin codex/personal-small-team
git log -1 --oneline
```

随后重建和迁移，但不要自动重置模拟数据：

```bash
dc() {
  docker compose --env-file .env.docker -p team_management_small "$@"
}

dc config --quiet
dc build
dc stop nginx backend celery_worker celery_beat || true
dc up -d db redis

dc run --rm --no-deps backend python manage.py migrate --noinput
dc run --rm --no-deps backend python manage.py collectstatic --noinput
dc run --rm --no-deps backend python manage.py check

dc up -d --remove-orphans
dc exec -T backend python manage.py migrate --check
```

只有明确要把演示数据恢复到该分支的标准初始状态时，才在启动全部服务前额外执行：

```bash
dc run --rm --no-deps backend \
  python manage.py seed_demo_data --clean --force
```

## 8. 更新前备份

根 Compose 生成的容器名带项目名前缀，必须把实际容器 ID 传给备份脚本：

```bash
cd /opt/team-management-small

dc() {
  docker compose --env-file .env.docker -p team_management_small "$@"
}

PG_CONTAINER="$(dc ps -q db)" \
BACKEND_CONTAINER="$(dc ps -q backend)" \
DB_USER=postgres \
DB_NAME=team_management \
BACKUP_DIR=/opt/backups/team-management-small \
bash scripts/backup.sh

find /opt/backups/team-management-small -maxdepth 2 -type f -ls
```

如果修改过 `DB_USER` 或 `DB_NAME`，上面的值必须同步修改。

对生成的最新 SHA-256 清单执行隔离恢复验证：

```bash
bash scripts/verify_backup.sh \
  /opt/backups/team-management-small/manifests/backup_YYYYMMDDTHHMMSSZ.sha256
```

可靠回滚不能只执行 `git switch`：数据库迁移、PostgreSQL 数据、媒体附件和原 `FIELD_ENCRYPTION_KEY` 必须作为同一恢复集合处理。具体灾难恢复原则见 `docs/BACKUP_GUIDE.md`。

## 9. 禁止操作

- 不要执行 `docker compose down -v`，它会删除数据库和附件数据卷。
- 不要随意改变 `-p team_management_small`。
- 不要在未备份时运行 `seed_demo_data --clean --force`。
- 不要使用 `deploy/release/deploy-remote.sh`；它会执行高风险的远程目录、Docker daemon 和旧演示数据操作。
- 不要在公网保留默认演示密码。
