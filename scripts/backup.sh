#!/bin/bash
# ==========================================
# 团队管理平台 - 自动备份脚本
# 用法: ./scripts/backup.sh
# 定时任务: 0 3 * * * /opt/team-management/scripts/backup.sh >> /opt/backups/backup.log 2>&1
# ==========================================

set -e

BACKUP_DIR="/opt/backups"
DB_DIR="${BACKUP_DIR}/db"
MEDIA_DIR="${BACKUP_DIR}/media"
DATE=$(date +%Y%m%d_%H%M%S)
RETAIN_DAYS=30

# 容器名称（与 docker-compose.prod.yml 中一致）
PG_CONTAINER="team_postgres_prod"
BACKEND_CONTAINER="team_backend_prod"

# 创建目录
mkdir -p ${DB_DIR} ${MEDIA_DIR}

echo "========================================"
echo "[$(date)] 开始备份..."
echo "========================================"

# 1. 备份数据库
echo "[1/3] 备份 PostgreSQL 数据库..."
docker exec ${PG_CONTAINER} pg_dump -U postgres team_management | gzip \
  > ${DB_DIR}/db_${DATE}.sql.gz
DB_SIZE=$(du -h "${DB_DIR}/db_${DATE}.sql.gz" | cut -f1)
echo "  完成: ${DB_DIR}/db_${DATE}.sql.gz (${DB_SIZE})"

# 2. 备份 media 文件
echo "[2/3] 备份 media 文件..."
docker exec ${BACKEND_CONTAINER} tar czf - /app/media 2>/dev/null \
  > ${MEDIA_DIR}/media_${DATE}.tar.gz
MEDIA_SIZE=$(du -h "${MEDIA_DIR}/media_${DATE}.tar.gz" | cut -f1)
echo "  完成: ${MEDIA_DIR}/media_${DATE}.tar.gz (${MEDIA_SIZE})"

# 3. 清理过期备份
echo "[3/3] 清理 ${RETAIN_DAYS} 天前的旧备份..."
find ${DB_DIR} -name "db_*.sql.gz" -mtime +${RETAIN_DAYS} -delete
find ${MEDIA_DIR} -name "media_*.tar.gz" -mtime +${RETAIN_DAYS} -delete
echo "  清理完成"

echo "========================================"
echo "[$(date)] 备份全部完成"
echo "  数据库备份: ${DB_SIZE}"
echo "  media备份: ${MEDIA_SIZE}"
echo "  总备份大小: $(du -sh ${BACKUP_DIR} | cut -f1)"
echo "========================================"
