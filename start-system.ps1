# VerificAI Code Quality System - Startup Script (Safe Mode)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Starting VerificAI Code Quality System..." -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check Docker
if (!(Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue)) {
    Write-Host "Docker Desktop is not running." -ForegroundColor Yellow
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# 2. Cleanup (docker compose down)
Write-Host "Cleaning up previous state..." -ForegroundColor Gray
docker compose down --remove-orphans

# 3. Start services
Write-Host "Starting services (docker compose up)..." -ForegroundColor Blue
docker compose up -d

# 4. Wait for Healthchecks
Write-Host "Waiting for services to be healthy (Postgres and Redis)..." -ForegroundColor Magenta
$timeout = 60 
$elapsed = 0
$allHealthy = $false

while (($elapsed -lt $timeout) -and (!$allHealthy)) {
    $psOutput = docker compose ps --format json | ConvertFrom-Json
    $healthyCount = 0
    $totalServices = 0

    foreach ($service in $psOutput) {
        $totalServices++
        # Services with healthcheck need to be healthy
        # Frontend just needs to be running
        if ($service.Status -like "*healthy*" -or ($service.Service -eq "frontend" -and $service.State -eq "running")) {
            $healthyCount++
        }
    }

    if ($healthyCount -eq $totalServices) {
        $allHealthy = $true
    } else {
        Write-Host "." -NoNewline -ForegroundColor Gray
        Start-Sleep -Seconds 3
        $elapsed += 3
    }
}

if ($allHealthy) {
    Write-Host "All services are operational!" -ForegroundColor Green
} else {
    Write-Host "Some services timed out. Checking status:" -ForegroundColor Yellow
    docker compose ps
}

# 5. Final API Check
Write-Host "Verifying Backend API connection..." -ForegroundColor Blue
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -ErrorAction Stop
    if ($health.status -eq "healthy") {
        Write-Host "Backend API: Online" -ForegroundColor Green
    } else {
        Write-Host "Backend API: Issue with Database connection" -ForegroundColor Red
    }
} catch {
    Write-Host "Backend API: Connection failed (check localhost:8000/health)" -ForegroundColor Red
}

# 6. Access Info
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "SYSTEM READY" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Frontend:    http://localhost:3011"
Write-Host "Backend API: http://localhost:8000/api/v1/"
Write-Host "Docs API:    http://localhost:8000/api/v1/docs"
Write-Host "Login:       admin / admin"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Read-Host "Press Enter to exit..."
