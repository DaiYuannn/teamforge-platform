# 2026-07-02 Local Docker Validation Report

## Scope

This run was limited to deployment and Docker validation work. No backend business logic, API fields, permission rules, token structure, sensitive approval workflow, finance visibility rules, V2 seed data, media backup, or frontend beautification changes were made.

## Files Changed

- `.docker-config/config.json`
  - Recreated as plain ASCII JSON `{}` to avoid Docker's UTF-8 BOM parse error.
- `backend/requirements/base.txt`
  - Restored `django==5.0.6` as an active dependency.
  - Confirmed there is no `pip install ...` command in the file.
- `backend/requirements/dev.txt`
  - Restored `-r base.txt`.
- `deploy/dockerfiles/backend.Dockerfile`
  - Restored valid `ENV` instruction.
  - Restored valid `RUN mkdir -p /app/media /app/staticfiles`.
  - Removed corrupted comment text that had swallowed Docker instructions.
- `backend/config/settings/base.py`
  - Restored clean Django settings structure.
  - Restored app registration, middleware, REST Framework, SimpleJWT, Celery, static, and media settings.
- `backend/config/settings/dev.py`
  - Restored local Docker-compatible development settings.
- `backend/config/settings/prod.py`
  - Restored production settings with environment-based secret, host, database, CORS, and security options.

## Compose Config

- Command: `docker compose -p team_management_local config`
- Result: Passed.
- Confirmed project name: `team_management_local`.
- Confirmed services in config:
  - `db`
  - `redis`
  - `backend`
  - `celery_worker`
  - `celery_beat`
  - `frontend`
  - `nginx`
- Confirmed named volumes in config:
  - `team_management_local_docker_pg_data`
  - `team_management_local_docker_redis_data`
  - `team_management_local_docker_media`
  - `team_management_local_docker_static`
  - `team_management_local_docker_frontend_dist`

## Docker Build

- Command attempted: `docker compose -p team_management_local build`
- Result: Failed before build execution.
- Error: `permission denied while trying to connect to the docker API at npipe:////./pipe/docker_engine`
- Escalation request was attempted, but the approval system returned 403 and did not allow daemon access.

## Docker Up

- Not executed.
- Reason: Docker daemon access is blocked, and build did not complete.

## Service Status

- `backend`: Not verified.
- `frontend`: Not verified.
- `nginx`: Not verified.
- `db`: Not verified.
- `redis`: Not verified.
- `celery_worker`: Not verified.
- `celery_beat`: Not verified.

## Django Management Commands

- `migrate`: Not executed.
- `collectstatic --noinput`: Not executed.
- `manage.py check`: Not executed.
- Reason: Containers are not built or running.

## V2 Seed

- `seed_competition_demo --clean --force`: Not executed.
- Reason: Containers are not built or running.

## Data Verification

Not executed because the Docker environment could not be started in this Codex session.

Required checks still pending:
- 6 `DEMO-2026-*` projects.
- 6-8 members per project.
- At least 3 competitions per project.
- All projects joined 小挑 and 大挑.
- Only 2 projects joined 数字中国.
- Tasks, finance, files, contributions, member ordering, intellectual property, sensitive approvals, notifications, and audit logs all have data.

## API Verification

Not executed because the Docker environment could not be started in this Codex session.

Required endpoints still pending:
- `/api/v1/auth/login/`
- `/api/v1/dashboard/`
- `/api/v1/projects/`
- `/api/v1/competitions/`
- `/api/v1/tasks/`
- `/api/v1/finance/expenses/`
- `/api/v1/files/`
- `/api/v1/contributions/`
- `/api/v1/intellectual-property/`
- `/api/v1/sensitive/`
- `/api/v1/notifications/`
- `/api/v1/audit/operation-logs/`

## Screenshot Acceptance

Not executed because the Docker environment could not be started in this Codex session.

Still pending:
- Login page.
- Dashboard.
- Project list and detail.
- Competition list.
- Task list.
- Finance overview and detail.
- Files.
- Contributions.
- Member ordering.
- Intellectual property.
- Sensitive approval.
- Notifications.
- Operation logs.
- Mobile 375px Dashboard, project page, and finance page.

## UI Issue Status

Not verified in Docker:
- `¥NaN`
- `undefined`
- table header colon issue
- vertical title text
- compressed content area
- oversized Dashboard cards
- mobile PC sidebar visibility
- member finance/ticket access
- sensitive data masking and approval-limited access
- sensitive view audit logging

## Server Preview Readiness

Not ready for server preview yet. Docker build/up, migrations, seed import, API verification, and screenshot acceptance remain blocked by local Docker daemon access.

## Freeze Recommendation

Do not freeze `v0.8.2-ui-recovery` yet. Freeze only after Docker build/up, V2 seed, API checks, and screenshot acceptance pass.

## Next 5 Actions

1. Confirm `docker ps` works in a normal user PowerShell outside Codex.
2. Allow Codex to access Docker daemon for `docker compose -p team_management_local build`.
3. Run `docker compose -p team_management_local up -d` and verify all service logs.
4. Run `migrate`, `collectstatic --noinput`, `manage.py check`, and V2 seed import.
5. Complete data counts, API checks, and browser screenshot acceptance before server preview.
