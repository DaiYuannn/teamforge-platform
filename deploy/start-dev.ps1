# ============================================================
# 团队管理平台 - 开发环境启动脚本 (Windows PowerShell)
# 用法: .\start-dev.ps1
# ============================================================
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

function Write-Step($msg) { Write-Host ">> $msg" -ForegroundColor Green }
function Write-Info($msg) { Write-Host ">> $msg" -ForegroundColor Yellow }

Write-Host "================ 团队管理平台 · 开发环境 ================" -ForegroundColor Green

# 1. 准备环境变量文件
if (-not (Test-Path "env\backend.env")) {
    Write-Info "复制 backend.env.example -> backend.env"
    Copy-Item "env\backend.env.example" "env\backend.env"
}
if (-not (Test-Path "env\frontend.env")) {
    Write-Info "复制 frontend.env.example -> frontend.env"
    Copy-Item "env\frontend.env.example" "env\frontend.env"
}

# 2. 构建镜像
Write-Step "构建镜像..."
docker compose build
if ($LASTEXITCODE -ne 0) { Write-Host "构建失败" -ForegroundColor Red; exit 1 }

# 3. 启动服务
Write-Step "启动服务..."
docker compose up -d
if ($LASTEXITCODE -ne 0) { Write-Host "启动失败" -ForegroundColor Red; exit 1 }

# 4. 等待 PostgreSQL 就绪
Write-Info "等待 PostgreSQL 就绪..."
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    docker compose exec -T postgres pg_isready -U postgres -d team_management 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if ($ready) {
    Write-Step "PostgreSQL 已就绪"
} else {
    Write-Host ">> PostgreSQL 未就绪，请检查日志: docker compose logs postgres" -ForegroundColor Red
}

# 5. 执行数据库迁移
Write-Step "执行数据库迁移..."
docker compose exec -T backend python manage.py migrate --noinput

# 6. 创建超级用户
$response = Read-Host ">> 是否创建超级用户？(y/n)"
if ($response -eq "y" -or $response -eq "Y") {
    docker compose exec backend python manage.py createsuperuser
}

Write-Host "================ 开发环境已启动 ================" -ForegroundColor Green
Write-Host "前端(Nginx):  http://localhost"
Write-Host "前端(Vite):   http://localhost:3000"
Write-Host "后端 API:     http://localhost:8000/api/v1/"
Write-Host "Django Admin: http://localhost:8000/admin/"
Write-Host "查看日志:     docker compose logs -f"
