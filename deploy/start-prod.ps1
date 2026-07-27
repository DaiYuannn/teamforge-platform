# ============================================================
# 团队管理平台 - 生产环境部署脚本 (Windows PowerShell)
# 用法: .\start-prod.ps1
# ============================================================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host ">> $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host ">> $msg" -ForegroundColor Yellow }

Write-Host "================ 团队管理平台 · 生产环境部署 ================" -ForegroundColor Green

# 1. 准备生产环境变量文件
if (-not (Test-Path "env\backend.prod.env")) {
    Write-Info "未发现 env\backend.prod.env，从模板创建..."
    Copy-Item "env\backend.prod.env.example" "env\backend.prod.env"
    Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    Write-Host "!! 警告: 已自动生成 env\backend.prod.env             !!" -ForegroundColor Red
    Write-Host "!! 请务必修改以下敏感项后再用于生产:                  !!" -ForegroundColor Red
    Write-Host "!!   - DJANGO_SECRET_KEY                              !!" -ForegroundColor Red
    Write-Host "!!   - DB_PASSWORD (须与 docker-compose.prod.yml 一致)!!" -ForegroundColor Red
    Write-Host "!!   - FIELD_ENCRYPTION_KEY                           !!" -ForegroundColor Red
    Write-Host "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" -ForegroundColor Red
    $response = Read-Host ">> 是否继续部署？(y/n)"
    if ($response -ne "y" -and $response -ne "Y") {
        Write-Host "已取消。请编辑 env\backend.prod.env 后重新运行。"
        exit 0
    }
}

$ComposeArgs = @("--env-file", "env/backend.prod.env", "-f", "docker-compose.prod.yml")

# 2. 构建生产镜像
Write-Step "构建生产镜像..."
docker compose @ComposeArgs build
if ($LASTEXITCODE -ne 0) { Write-Host "构建失败" -ForegroundColor Red; exit 1 }

# 3. 启动基础服务与后端
Write-Step "启动 PostgreSQL、Redis 与后端..."
docker compose @ComposeArgs up -d postgres redis backend
if ($LASTEXITCODE -ne 0) { Write-Host "基础服务或后端启动失败" -ForegroundColor Red; exit 1 }

# 4. 初始化数据库与静态资源
Write-Step "执行数据库迁移..."
docker compose @ComposeArgs exec -T backend python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { Write-Host "数据库迁移失败" -ForegroundColor Red; exit 1 }

Write-Step "收集静态资源..."
docker compose @ComposeArgs exec -T backend python manage.py collectstatic --noinput
if ($LASTEXITCODE -ne 0) { Write-Host "静态资源收集失败" -ForegroundColor Red; exit 1 }

# 5. 启动全部生产服务
Write-Step "启动全部生产服务..."
docker compose @ComposeArgs up -d
if ($LASTEXITCODE -ne 0) { Write-Host "生产服务启动失败" -ForegroundColor Red; exit 1 }

Write-Host "================ 生产环境已启动 ================" -ForegroundColor Green
Write-Host "应用入口: http://localhost"
Write-Host "查看日志: docker compose --env-file env/backend.prod.env -f docker-compose.prod.yml logs -f"
Write-Info "Celery Worker/Beat 已随生产服务启动"
