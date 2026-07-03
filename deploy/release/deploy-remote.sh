#!/bin/bash
# ============================================================
# 团队管理平台 - 服务器一键部署脚本
# 服务器: 139.196.192.169 (Ubuntu 22.04)
# 使用方式: bash deploy-remote.sh
# ============================================================
set -e

DEPLOY_DIR="/opt/team-management"
COMPOSE_FILE="deploy/docker-compose.prod.yml"
PROJECT_NAME="team_management_prod"

echo "================================================"
echo "  团队管理平台 - 服务器部署"
echo "================================================"

# 1. 检查 Docker
echo ">> [1/9] 检查 Docker 环境..."
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi
if ! docker compose version &> /dev/null; then
    echo "错误: Docker Compose 未安装"
    exit 1
fi
echo "   Docker: $(docker --version)"
echo "   Compose: $(docker compose version)"

# 2. 清理旧部署（避免残留冲突）
echo ">> [2/9] 清理旧部署..."
COMPOSE_FILE="deploy/docker-compose.prod.yml"
cd $DEPLOY_DIR 2>/dev/null || true
docker compose -p $PROJECT_NAME -f $COMPOSE_FILE --env-file deploy/env/backend.prod.env down --remove-orphans 2>/dev/null || true
rm -rf $DEPLOY_DIR/*
echo "   旧部署已清理"

# 3. 解压代码
echo ">> [3/9] 解压项目代码..."
mkdir -p $DEPLOY_DIR
tar -xzf /tmp/team_management_deploy.tar.gz -C $DEPLOY_DIR
echo "   代码已解压到 $DEPLOY_DIR"

# 4. 检查环境变量文件
echo ">> [4/9] 检查生产环境变量..."
cd $DEPLOY_DIR
if [ ! -f "deploy/env/backend.prod.env" ]; then
    echo "错误: deploy/env/backend.prod.env 不存在"
    exit 1
fi
# 提取 DB_PASSWORD 供 docker compose 变量插值使用（env_file 中的值不会参与 compose 变量替换）
export DB_PASSWORD=$(grep '^DB_PASSWORD=' deploy/env/backend.prod.env | sed 's/^DB_PASSWORD=//; s/^"//; s/"$//')
export DB_NAME=$(grep '^DB_NAME=' deploy/env/backend.prod.env | sed 's/^DB_NAME=//; s/^"//; s/"$//')
export DB_USER=$(grep '^DB_USER=' deploy/env/backend.prod.env | sed 's/^DB_USER=//; s/^"//; s/"$//')
echo "   环境变量文件就绪 (DB_PASSWORD=${DB_PASSWORD:0:3}***)"

# 定义 compose 公共参数
COMPOSE_CMD="docker compose -p $PROJECT_NAME -f $COMPOSE_FILE --env-file deploy/env/backend.prod.env"

# 5. 强制更新 Docker 镜像加速器
echo ">> [5/9] 配置 Docker 镜像加速..."
cat > /etc/docker/daemon.json << 'MIRROR'
{
  "registry-mirrors": [
    "https://docker.xuanyuan.me",
    "https://docker.m.daocloud.io"
  ]
}
MIRROR
systemctl daemon-reload
systemctl restart docker
sleep 3
echo "   镜像加速已配置并重启 Docker"

# 6. 构建镜像
echo ">> [6/9] 构建镜像（可能需要 5-10 分钟）..."
export DOCKER_BUILDKIT=1
$COMPOSE_CMD build
echo "   镜像构建完成"

# 7. 启动服务
echo ">> [7/9] 启动服务..."
$COMPOSE_CMD up -d
echo "   等待数据库就绪..."
sleep 20

# 8. 初始化数据库
echo ">> [8/9] 初始化数据库..."
$COMPOSE_CMD exec -T backend python manage.py migrate --noinput
$COMPOSE_CMD exec -T backend python manage.py collectstatic --noinput
$COMPOSE_CMD exec -T backend python manage.py seed_competition_demo --clean --force
echo "   数据库初始化完成"

# 9. 验证服务
echo ">> [9/9] 验证服务状态..."
$COMPOSE_CMD ps

echo ""
echo "================================================"
echo "  部署完成！"
echo "================================================"
echo ""
echo "访问地址:  http://139.196.192.169/"
echo "API 地址:  http://139.196.192.169/api/v1/"
echo "Admin:    http://139.196.192.169/admin/"
echo ""
echo "测试账号:"
echo "  管理员:     admin@demo.com / admin123456"
echo "  指导老师1:  teacher1@demo.com / teacher123456"
echo "  指导老师2:  teacher2@demo.com / teacher123456"
echo "  敏感审批人: approver@demo.com / approver123456"
echo "  项目负责人: leader1~leader6@demo.com / leader123456"
echo "  普通成员:   member1~member8@demo.com / member123456"
echo ""
echo "常用命令:"
echo "  查看日志: docker compose -p $PROJECT_NAME -f $COMPOSE_FILE logs -f backend"
echo "  重启服务: docker compose -p $PROJECT_NAME -f $COMPOSE_FILE restart"
echo "  停止服务: docker compose -p $PROJECT_NAME -f $COMPOSE_FILE down"
echo ""
