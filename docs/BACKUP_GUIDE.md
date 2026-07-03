# 备份与恢复文档（Backup & Recovery Guide）

> 本文档说明如何备份和恢复团队管理平台的关键数据，包括数据库、媒体文件和加密密钥。

---

## 目录

1. [备份内容概览](#1-备份内容概览)
2. [备份 PostgreSQL 数据库](#2-备份-postgresql-数据库)
3. [备份 media 文件](#3-备份-media-文件)
4. [备份敏感资料加密密钥](#4-备份敏感资料加密密钥)
5. [定期自动备份](#5-定期自动备份)
6. [恢复到某一天的数据](#6-恢复到某一天的数据)

---

## 1. 备份内容概览

| 备份项 | 重要程度 | 频率 | 存储位置 |
|--------|----------|------|----------|
| PostgreSQL 数据库 | 极高 | 每日 | /opt/backups/db/ |
| media 文件（票据/附件） | 高 | 每日 | /opt/backups/media/ |
| FIELD_ENCRYPTION_KEY | 极高 | 一次性 | 安全离线存储 |
| .env.production | 极高 | 变更时 | 安全离线存储 |
| Docker Compose 配置 | 中 | 变更时 | Git 仓库 |

> 核心原则：数据库和加密密钥必须分开存储。如果攻击者同时获取了两者，敏感资料将被破解。

---

## 2. 备份 PostgreSQL 数据库

### 2.1 手动备份

```bash
# 创建备份目录
mkdir -p /opt/backups/db

# 执行备份（Docker 部署）
docker exec team_postgres_prod pg_dump -U postgres team_management \
  > /opt/backups/db/db_$(date +%Y%m%d_%H%M%S).sql

# 验证备份文件
ls -lh /opt/backups/db/
```

### 2.2 压缩备份

```bash
docker exec team_postgres_prod pg_dump -U postgres team_management | gzip \
  > /opt/backups/db/db_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 2.3 验证备份可用性

```bash
# 查看备份文件内容（前 20 行）
head -20 /opt/backups/db/db_20260701_120000.sql

# 检查是否包含关键表
grep "CREATE TABLE" /opt/backups/db/db_20260701_120000.sql | head -20
```

---

## 3. 备份 media 文件

media 目录包含用户上传的票据图片、项目文件等，必须定期备份。

### 3.1 手动备份

```bash
# 创建备份目录
mkdir -p /opt/backups/media

# 打包备份 media 文件（Docker 部署）
docker exec team_backend_prod tar czf - /app/media \
  > /opt/backups/media/media_$(date +%Y%m%d_%H%M%S).tar.gz

# 或直接从 Docker 卷备份
docker run --rm -v team_management_media_data:/data -v /opt/backups/media:/backup \
  alpine tar czf /backup/media_$(date +%Y%m%d_%H%M%S).tar.gz -C /data .

# 验证
ls -lh /opt/backups/media/
```

### 3.2 增量同步（使用 rsync）

```bash
# 从 Docker 卷同步到备份目录
rsync -avz \
  --exclude='*.tmp' \
  /var/lib/docker/volumes/team_management_media_data/_data/ \
  /opt/backups/media/current/
```

---

## 4. 备份敏感资料加密密钥

`FIELD_ENCRYPTION_KEY` 是整个系统中最敏感的配置项。

> 警告：此密钥一旦丢失，所有已加密的敏感资料（身份证号等）将永远无法解密。
> 警告：此密钥一旦泄露，所有敏感资料将被破解。

### 4.1 导出密钥

```bash
# 从环境变量文件中提取
grep FIELD_ENCRYPTION_KEY /opt/team-management/deploy/env/backend.prod.env
```

### 4.2 安全存储方式

推荐以下存储方式（至少选择两种）：

1. **密码管理器**：存入 1Password / Bitwarden / KeePass 等密码管理器
2. **离线 USB**：写入 USB 存储设备，存放于物理安全位置
3. **加密邮件**：发送到仅自己可访问的加密邮箱
4. **打印纸质**：打印后存放于保险柜

### 4.3 密钥不要存放的地方

- Git 仓库（即使私有仓库）
- 聊天记录（微信/飞书/Slack）
- 共享文档
- 服务器明文文件（除 .env.production 外）

---

## 5. 定期自动备份

### 5.1 创建备份脚本

```bash
sudo nano /opt/team-management/scripts/backup.sh
```

脚本内容：

```bash
#!/bin/bash
# ==========================================
# 团队管理平台 - 自动备份脚本
# ==========================================

BACKUP_DIR="/opt/backups"
DB_DIR="${BACKUP_DIR}/db"
MEDIA_DIR="${BACKUP_DIR}/media"
DATE=$(date +%Y%m%d_%H%M%S)
RETAIN_DAYS=30

# 创建目录
mkdir -p ${DB_DIR} ${MEDIA_DIR}

echo "[$(date)] 开始备份..."

# 1. 备份数据库
echo "  备份数据库..."
docker exec team_postgres_prod pg_dump -U postgres team_management | gzip \
  > ${DB_DIR}/db_${DATE}.sql.gz
echo "  数据库备份完成: ${DB_DIR}/db_${DATE}.sql.gz"

# 2. 备份 media 文件
echo "  备份 media 文件..."
docker exec team_backend_prod tar czf - /app/media 2>/dev/null \
  > ${MEDIA_DIR}/media_${DATE}.tar.gz
echo "  media 备份完成: ${MEDIA_DIR}/media_${DATE}.tar.gz"

# 3. 清理过期备份（保留最近 30 天）
echo "  清理 ${RETAIN_DAYS} 天前的备份..."
find ${DB_DIR} -name "db_*.sql.gz" -mtime +${RETAIN_DAYS} -delete
find ${MEDIA_DIR} -name "media_*.tar.gz" -mtime +${RETAIN_DAYS} -delete

echo "[$(date)] 备份完成"
echo "  数据库备份大小: $(du -sh ${DB_DIR} | cut -f1)"
echo "  media备份大小: $(du -sh ${MEDIA_DIR} | cut -f1)"
```

### 5.2 设置定时任务

```bash
# 赋予执行权限
sudo chmod +x /opt/team-management/scripts/backup.sh

# 编辑 crontab
sudo crontab -e

# 添加定时任务：每天凌晨 3:00 执行备份
0 3 * * * /opt/team-management/scripts/backup.sh >> /opt/backups/backup.log 2>&1

# 每周日凌晨 2:00 执行全量备份（额外保留周备份）
0 2 * * 0 /opt/team-management/scripts/backup.sh >> /opt/backups/backup_weekly.log 2>&1
```

### 5.3 验证定时任务

```bash
# 查看定时任务
sudo crontab -l

# 查看备份日志
cat /opt/backups/backup.log

# 查看备份文件列表
ls -lh /opt/backups/db/
ls -lh /opt/backups/media/
```

---

## 6. 恢复到某一天的数据

### 6.1 恢复数据库

```bash
# 1. 停止后端服务
cd /opt/team-management/deploy
docker compose -f docker-compose.prod.yml stop backend

# 2. 恢复数据库（注意：会覆盖现有数据）
gunzip -c /opt/backups/db/db_20260701_120000.sql.gz | \
  docker exec -i team_postgres_prod psql -U postgres team_management

# 3. 重新启动后端
docker compose -f docker-compose.prod.yml start backend

# 4. 验证数据
docker compose -f docker-compose.prod.yml exec backend python manage.py check
```

### 6.2 恢复 media 文件

```bash
# 1. 停止后端服务
docker compose -f docker-compose.prod.yml stop backend

# 2. 恢复 media 文件
docker exec team_backend_prod tar xzf - -C / < /opt/backups/media/media_20260701_120000.tar.gz

# 或从宿主机恢复到 Docker 卷
docker run --rm -v team_management_media_data:/data -v /opt/backups/media:/backup \
  alpine sh -c "rm -rf /data/* && tar xzf /backup/media_20260701_120000.tar.gz -C /data"

# 3. 重新启动后端
docker compose -f docker-compose.prod.yml start backend
```

### 6.3 恢复加密密钥

如果服务器密钥丢失需要恢复：

```bash
# 1. 编辑环境变量文件
nano /opt/team-management/deploy/env/backend.prod.env

# 2. 将 FIELD_ENCRYPTION_KEY 替换为备份的密钥
FIELD_ENCRYPTION_KEY=你备份的Fernet密钥

# 3. 重启后端
docker compose -f docker-compose.prod.yml restart backend
```

### 6.4 完整恢复流程（数据库 + media + 密钥）

```bash
cd /opt/team-management/deploy

# 1. 停止全部服务
docker compose -f docker-compose.prod.yml down

# 2. 删除数据卷（危险！确保有备份）
docker volume rm team_management_pg_data team_management_media_data

# 3. 重新启动基础设施
docker compose -f docker-compose.prod.yml up -d postgres redis

# 4. 等待数据库就绪
sleep 15

# 5. 恢复数据库
gunzip -c /opt/backups/db/db_20260701_120000.sql.gz | \
  docker exec -i team_postgres_prod psql -U postgres team_management

# 6. 启动全部服务
docker compose -f docker-compose.prod.yml up -d --build

# 7. 恢复 media 文件
docker run --rm -v team_management_media_data:/data -v /opt/backups/media:/backup \
  alpine sh -c "tar xzf /backup/media_20260701_120000.tar.gz -C /data"

# 8. 重启后端以加载恢复的数据
docker compose -f docker-compose.prod.yml restart backend
```

---

## 备份检查清单

| 检查项 | 频率 | 状态 |
|--------|------|------|
| 数据库每日自动备份 | 每天 3:00 | 待启用 |
| media 文件每日备份 | 每天 3:00 | 待启用 |
| 备份文件可成功恢复 | 每月一次 | 待验证 |
| FIELD_ENCRYPTION_KEY 已离线备份 | 一次性 | 待确认 |
| .env.production 已离线备份 | 变更时 | 待确认 |
| 过期备份自动清理（30天） | 自动 | 待启用 |

---

> 文档版本：v1.0
> 维护者：团队管理软件项目组
