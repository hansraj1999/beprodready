# Start Postgres (Docker), migrate backend, run API + Vite locally.
# Usage: from repo root  .\scripts\dev-local.ps1
#        Skip Docker DB:  .\scripts\dev-local.ps1 -SkipPostgres

param(
    [switch]$SkipPostgres
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $RepoRoot

function Require-Command {
    param([string]$Name, [string]$Hint)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Error "Missing '$Name' in PATH. $Hint"
    }
}

Require-Command "python" "Install Python 3.12+ and add it to PATH."
Require-Command "npm" "Install Node.js 22+ (includes npm)."
if (-not $SkipPostgres) {
    Require-Command "docker" "Install Docker Desktop, or run with -SkipPostgres if Postgres is already running."
}

if (-not $SkipPostgres) {
    Write-Host "==> Starting PostgreSQL (docker compose)..." -ForegroundColor Cyan
    docker compose up -d postgres

    Write-Host "==> Waiting for Postgres..." -ForegroundColor Cyan
    $ready = $false
    for ($i = 0; $i -lt 45; $i++) {
        docker compose exec -T postgres pg_isready -U archai -d archai 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            $ready = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $ready) {
        Write-Error "Postgres did not become ready in time. Check: docker compose logs postgres"
    }
    Write-Host "    Postgres is up." -ForegroundColor Green
}
else {
    Write-Host "==> Skipping Docker Postgres (-SkipPostgres). Ensure DATABASE_URL in backend/.env is correct." -ForegroundColor Yellow
}

$backendEnv = Join-Path $RepoRoot "backend\.env"
if (-not (Test-Path $backendEnv)) {
    Copy-Item (Join-Path $RepoRoot "backend\.env.example") $backendEnv
    Write-Host "==> Created backend\.env from .env.example" -ForegroundColor Green
}

$frontendEnv = Join-Path $RepoRoot "frontend\.env"
if (-not (Test-Path $frontendEnv)) {
    Copy-Item (Join-Path $RepoRoot "frontend\.env.example") $frontendEnv
    Write-Host "==> Created frontend\.env from .env.example" -ForegroundColor Green
}

$backend = Join-Path $RepoRoot "backend"
Push-Location $backend

if (-not (Test-Path ".venv")) {
    Write-Host "==> Creating Python venv..." -ForegroundColor Cyan
    python -m venv .venv
}

Write-Host "==> Installing backend dependencies..." -ForegroundColor Cyan
& .\.venv\Scripts\pip.exe install -r requirements.txt

Write-Host "==> Running migrations..." -ForegroundColor Cyan
& .\.venv\Scripts\alembic.exe upgrade head

Pop-Location

$venvPython = Join-Path $RepoRoot "backend\.venv\Scripts\python.exe"
Write-Host "==> Starting API in a new window (http://127.0.0.1:8000)..." -ForegroundColor Cyan
Start-Process powershell -WorkingDirectory $backend -ArgumentList @(
    "-NoExit",
    "-Command",
    "Write-Host 'Archai backend — close this window to stop the API' -ForegroundColor Cyan; & '$venvPython' -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
)

Start-Sleep -Seconds 2

$frontend = Join-Path $RepoRoot "frontend"
Push-Location $frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "==> npm install (frontend)..." -ForegroundColor Cyan
    npm install
}

Write-Host "==> Starting Vite (http://localhost:5173) — Ctrl+C here stops only the frontend." -ForegroundColor Cyan
Write-Host "    API docs: http://127.0.0.1:8000/docs" -ForegroundColor DarkGray
npm run dev

Pop-Location
