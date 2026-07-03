#!/bin/bash
# ============================================================
# 团队管理平台 - 开发环境启动脚本 (Linux / macOS / Git Bash)
# 用法: bash start-dev.sh
# ============================================================
set -e

cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}================ 团队管理平台 · 开发环境 ================${NC}"

# 1. 准备环境变量文件
if [ ! -f env/backend.env ]; then
    echo -e "${YELLOW}>> 复制 backend.env.example -> backend.env${NC}"
    cp env/backend.env.example env/backend.env
fi
if [ ! -f env/frontend.env ]; then
    echo -e "${YELLOW}>> 复制 frontend.env.example -> frontend.env${NC}"
    cp env/frontend.env.example env/frontend.env
fi

# 2. 构建镜像
echo -e "${GREEN}>> 构建镜像...${NC}"
docker compose build

# 3. 启动服务
echo -e "${GREEN}>> 启动服务...${NC}"
docker compose up -d

# 4. 等待 PostgreSQL 就绪
echo -e "${YELLOW}>> 等待 PostgreSQL 就绪...${NC}"
READY=false
for i in $(seq 1 30); do
    if docker compose exec -T postgres pg_isready -U postgres -d team_management >/dev/null 2>&1; then
        echo -e "${GREEN}>> PostgreSQL 已就绪${NC}"
        READY=true
        break
    fi
    sleep 2
done
if [ "$READY" = "false" ]; then
    echo -e "${RED}>> PostgreSQL 未就绪，请检查日志: docker compose logs postgres${NC}"
fi

# 5. 执行数据库迁移
echo -e "${GREEN}>> 执行数据库迁移...${NC}"
docker compose exec -T backend python manage.py migrate --noinput

# 6. 创建超级用户
echo -e "${YELLOW}>> 是否创建超级用户？(y/n)${NC}"
read -r response
if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
    docker compose exec -it backend python manage.py createsuperuser
fi

echo -e "${GREEN}================ 开发环境已启动 ================${NC}"
echo -e "前端(Nginx):  http://localhost"
echo -e "前端(Vite):   http://localhost:3000"
echo -e "后端 API:     http://localhost:8000/api/v1/"
echo -e "Django Admin: http://localhost:8000/admin/"
echo -e "查看日志:     docker compose logs -f"
