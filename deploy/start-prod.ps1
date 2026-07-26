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

# 2. 构建生产镜像
Write-Step "构建生产镜像..."
docker compose -f docker-compose.prod.yml build
if ($LASTEXITCODE -ne 0) { Write-Host "构建失败" -ForegroundColor Red; exit 1 }

# 3. 启动生产服务
Write-Step "启动生产服务..."
docker compose -f docker-compose.prod.yml up -d
if ($LASTEXITCODE -ne 0) { Write-Host "启动失败" -ForegroundColor Red; exit 1 }

Write-Host "================ 生产环境已启动 ================" -ForegroundColor Green
Write-Host "应用入口: http://localhost"
Write-Host "查看日志: docker compose -f docker-compose.prod.yml logs -f"
Write-Info "Celery Worker/Beat 已随生产服务启动"
