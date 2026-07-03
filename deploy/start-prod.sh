#!/bin/bash
# ============================================================
# 团队管理平台 - 生产环境部署脚本 (Linux / macOS)
# 用法: bash start-prod.sh
# ============================================================
set -e

cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}================ 团队管理平台 · 生产环境部署 ================${NC}"

# 1. 准备生产环境变量文件
if [ ! -f env/backend.prod.env ]; then
    echo -e "${YELLOW}>> 未发现 env/backend.prod.env，从模板创建...${NC}"
    cp env/backend.prod.env.example env/backend.prod.env
    echo -e "${RED}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!${NC}"
    echo -e "${RED}!! 警告: 已自动生成 env/backend.prod.env             !!${NC}"
    echo -e "${RED}!! 请务必修改以下敏感项后再用于生产:                  !!${NC}"
    echo -e "${RED}!!   - DJANGO_SECRET_KEY                              !!${NC}"
    echo -e "${RED}!!   - DB_PASSWORD (须与 docker-compose.prod.yml 一致)!!${NC}"
    echo -e "${RED}!!   - FIELD_ENCRYPTION_KEY                           !!${NC}"
    echo -e "${RED}!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!${NC}"
    echo -e "${YELLOW}>> 是否继续部署？(y/n)${NC}"
    read -r response
    if [ "$response" != "y" ] && [ "$response" != "Y" ]; then
        echo "已取消。请编辑 env/backend.prod.env 后重新运行。"
        exit 0
    fi
fi

# 2. 构建生产镜像
echo -e "${GREEN}>> 构建生产镜像...${NC}"
docker compose -f docker-compose.prod.yml build

# 3. 启动生产服务
echo -e "${GREEN}>> 启动生产服务...${NC}"
docker compose -f docker-compose.prod.yml up -d

echo -e "${GREEN}================ 生产环境已启动 ================${NC}"
echo -e "应用入口: http://localhost"
echo -e "查看日志: docker compose -f docker-compose.prod.yml logs -f"
echo -e "${YELLOW}提示: 启用 Celery: docker compose -f docker-compose.prod.yml --profile celery up -d${NC}"
