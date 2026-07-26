# 生产备份、校验与恢复演练指南

本指南对应仓库中的：

- `scripts/backup.sh`：生成 PostgreSQL 自定义格式备份、媒体归档和 SHA-256 清单。
- `scripts/verify_backup.sh`：校验完整备份集，并在隔离容器中执行非破坏恢复演练。

演示数据备份页面只用于功能演示，不能替代本指南中的生产备份。

## 1. 备份范围与边界

| 项目 | 备份方式 | 建议频率 |
|---|---|---|
| PostgreSQL | `pg_dump --format=custom` | 每日 |
| `/app/media` 受保护媒体 | `tar.gz` 全量归档 | 每日 |
| `FIELD_ENCRYPTION_KEY` | 独立离线保管，不放入数据备份 | 创建及轮换时 |
| 生产环境变量 | 加密后离线保管 | 每次变更 |
| 恢复演练 | 临时 PostgreSQL 容器 + 临时媒体目录 | 每月 |

数据库和媒体归档不是事务级原子快照。应在低流量时段执行；严格要求一致性时，
在备份窗口暂停上传及写入任务，备份结束后再恢复。

`FIELD_ENCRYPTION_KEY` 必须与数据库分开存放。只有数据库而没有该密钥时，
已加密的敏感资料无法恢复；同时泄露两者则会失去加密保护。

## 2. 前置条件

备份主机需要：

- Docker CLI，且能访问生产 Docker daemon；
- `tar`、`sha256sum`、`find`、`flock`；
- 可选：`gpg`（加密）、`aws`（S3）、`rclone`（其他远端）、`curl`（告警）。

生产容器默认名称：

- PostgreSQL：`team_postgres_prod`
- 后端：`team_backend_prod`

如名称不同，通过环境变量覆盖，不要直接修改脚本。

## 3. 配置

脚本默认读取 `/etc/team-management/backup.env`，也可通过
`BACKUP_CONFIG_FILE` 指定其他文件。配置文件权限应为 `600`。

```bash
sudo install -d -m 700 /etc/team-management
sudo install -m 600 /dev/null /etc/team-management/backup.env
sudo editor /etc/team-management/backup.env
```

示例：

```bash
BACKUP_DIR=/opt/backups/team-management
RETAIN_DAYS=30
PG_CONTAINER=team_postgres_prod
BACKEND_CONTAINER=team_backend_prod
DB_USER=postgres
DB_NAME=team_management

# 留空表示本机备份。支持以下三类根目录：
# file:///mnt/offsite/team-management
# s3://example-backups/team-management
# backup-remote:team-management
BACKUP_REMOTE_URI=

# 可选：失败时接收 JSON POST。
BACKUP_ALERT_WEBHOOK=

# 可选：GPG 公钥的 UID、邮箱或指纹。备份机只需要公钥。
BACKUP_GPG_RECIPIENT=
```

`BACKUP_DIR` 和 `file://` 目标必须是两个互不包含的绝对非根目录。脚本使用
`umask 077`，并在生成备份文件名之前取得进程锁，拒绝并发备份任务。

## 4. 执行备份

```bash
cd /opt/team-management
sudo chmod +x scripts/backup.sh scripts/verify_backup.sh
sudo scripts/backup.sh
```

默认输出结构：

```text
/opt/backups/team-management/
├── db/
│   └── db_20260726T030000Z.dump
├── media/
│   └── media_20260726T030000Z.tar.gz
└── manifests/
    └── backup_20260726T030000Z.sha256
```

启用 GPG 后，两个数据文件分别增加 `.gpg` 后缀。清单始终针对最终文件计算：

```bash
cd /opt/backups/team-management
sha256sum --check manifests/backup_20260726T030000Z.sha256
```

只有清单已经存在且校验通过的时间戳，才算完整备份集。`.partial` 文件不是有效
备份，不得用于恢复。

脚本在本地完成以下检查后才发布清单：

1. 数据库 dump 非空且可被 `pg_restore --list` 读取；
2. 媒体归档非空且可被 `tar -tzf` 读取；
3. 可选的 GPG 文件结构可读取；
4. 最终数据库和媒体文件通过 SHA-256 清单校验。

## 5. 加密、异地存储与告警

### GPG 加密

先将恢复负责人的公钥导入备份主机：

```bash
gpg --import backup-recipient-public.asc
gpg --list-keys recipient@example.com
```

在 `backup.env` 设置：

```bash
BACKUP_GPG_RECIPIENT=recipient@example.com
```

私钥不应存放在生产服务器。恢复演练应在受控验证主机上进行，并导入对应私钥。
备份脚本会先校验未加密 dump 和媒体归档，再生成加密最终文件；失败时不会发布清单。

### 异地副本

远端副本保留相同的 `db/`、`media/`、`manifests/` 结构，清单最后上传，作为
完整性标记：

- `file:///绝对路径`：挂载磁盘或另一台主机的安全挂载点；
- `s3://bucket/prefix`：使用 AWS CLI；
- 其他值：使用 `rclone copyto`，例如 `remote:bucket/prefix`。

建议使用独立账号、服务端加密、对象锁或不可变保留策略，并定期从异地副本执行
恢复演练。脚本只清理本机超过 `RETAIN_DAYS` 的备份，远端生命周期应在存储端配置。

### 失败告警

设置 `BACKUP_ALERT_WEBHOOK` 后，失败时发送：

```json
{
  "event": "backup_failed",
  "host": "backup-host",
  "timestamp": "20260726T030000Z",
  "exit_code": 1
}
```

恢复演练可设置 `VERIFY_ALERT_WEBHOOK`；未设置时复用 `BACKUP_ALERT_WEBHOOK`，
事件名为 `backup_verification_failed`。Webhook 不应包含数据库密码或加密密钥。

## 6. 定时执行

每天 03:00 备份：

```cron
0 3 * * * /opt/team-management/scripts/backup.sh >> /opt/backups/team-management/backup.log 2>&1
```

每月 1 日 05:00 对最新完整清单执行恢复演练。应由一个包装脚本明确选中清单，
不要使用可能匹配 `.partial` 的宽泛通配符：

```bash
latest_manifest="$(
  find /opt/backups/team-management/manifests -maxdepth 1 \
    -type f -name 'backup_*.sha256' -printf '%T@ %p\n' |
  sort -n | tail -1 | cut -d' ' -f2-
)"
test -n "${latest_manifest}"
/opt/team-management/scripts/verify_backup.sh "${latest_manifest}"
```

日志采集系统应同时监控进程退出码和 webhook；不要只检查目录中是否出现文件。

## 7. 非破坏恢复演练

推荐直接传入清单：

```bash
/opt/team-management/scripts/verify_backup.sh \
  /opt/backups/team-management/manifests/backup_20260726T030000Z.sha256
```

也可传入同一备份集的数据库文件，脚本会定位对应清单：

```bash
/opt/team-management/scripts/verify_backup.sh \
  /opt/backups/team-management/db/db_20260726T030000Z.dump
```

演练流程：

1. 校验清单恰好包含同一时间戳的数据库和媒体文件；
2. 校验两个文件的 SHA-256；
3. 必要时解密到权限为 `700/600` 的临时目录；
4. 将媒体解压到临时目录，拒绝绝对路径和 `..` 路径；
5. 启动 `--network none`、无端口、无生产卷的临时 PostgreSQL 容器；
6. 使用 `pg_restore --single-transaction --exit-on-error` 恢复；
7. 查询核心表并输出行数；
8. 删除临时容器和临时目录。

默认验证表：

```text
django_migrations users projects tasks file_assets operation_logs
```

可通过 `VERIFY_TABLES` 增加业务表，但只允许安全的 SQL 标识符。演练容器镜像可由
`RESTORE_DRILL_POSTGRES_IMAGE` 覆盖，等待时间由 `RESTORE_DRILL_TIMEOUT` 控制。

该脚本不会连接、停止、清空或覆盖生产数据库，也不会挂载生产数据库或媒体卷。

## 8. 灾难恢复原则

真实恢复属于破坏性运维，必须由老师或系统负责人明确批准。推荐蓝绿恢复：

1. 记录事件时间和目标恢复点；
2. 对现状再做一份只读保全备份；
3. 在新的 PostgreSQL 容器/实例和新的媒体卷中恢复，不覆盖原实例；
4. 使用本指南的清单、核心表、登录、文件下载和敏感资料解密检查；
5. 确认 `FIELD_ENCRYPTION_KEY` 与目标备份匹配；
6. 经两人复核后切换应用连接；
7. 保留旧实例直至业务验收和回滚窗口结束。

不要在未验证备份的情况下执行 `DROP DATABASE`、删除 Docker volume 或清空
`/app/media`。恢复后应立即执行一次新的完整备份。

## 9. 验收清单

| 检查项 | 频率 |
|---|---|
| 备份任务退出码为 0 | 每日 |
| 本地清单 SHA-256 通过 | 每日自动 |
| 异地目录结构完整且清单最后上传 | 每日 |
| 失败告警能到达负责人 | 每季度演练 |
| 隔离恢复演练通过 | 每月 |
| GPG 私钥可用但不在生产机 | 每季度 |
| `FIELD_ENCRYPTION_KEY` 有两个独立离线副本 | 每次轮换 |
| 异地保留/对象锁策略生效 | 每季度 |

SHA-256 清单用于发现传输或存储损坏，不能防御能够同时替换文件和清单的攻击者；
此类威胁应通过 GPG、只写备份凭据、对象锁和独立账号控制。
