# ROMS - Quick Update Script for Windows Server
# Pulls latest changes from GitHub and restarts service

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ROMS - Quick Update from GitHub" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "WARNING: Not running as Administrator." -ForegroundColor Yellow
    Write-Host "Some operations may fail if service needs to be restarted." -ForegroundColor Yellow
    Write-Host ""
}

# Configuration
$projectPath = "C:\ROMS"

# Navigate to project
cd $projectPath

# Check if service exists
$serviceExists = Get-Service -Name "ROMS-V2-Backend" -ErrorAction SilentlyContinue

# Stop service if running
if ($serviceExists) {
    Write-Host "Stopping ROMS-V2-Backend service..." -ForegroundColor Yellow
    nssm stop ROMS-V2-Backend
    Start-Sleep -Seconds 2
    Write-Host "✓ Service stopped" -ForegroundColor Green
    Write-Host ""
}

# Pull latest changes
Write-Host "Pulling latest changes from GitHub..." -ForegroundColor Yellow
git pull
Write-Host "✓ Code updated" -ForegroundColor Green
Write-Host ""

# Update backend dependencies if changed
$requirementsChanged = git diff HEAD@{1} HEAD --name-only | Select-String "backend-v2/requirements.txt"
if ($requirementsChanged) {
    Write-Host "Dependencies changed, updating..." -ForegroundColor Yellow
    cd backend-v2
    .\venv\Scripts\Activate.ps1
    pip install -r requirements.txt --upgrade --quiet
    Write-Host "✓ Dependencies updated" -ForegroundColor Green
    Write-Host ""
    cd ..
}

# Update frontend dependencies if changed
$frontendDepsChanged = git diff HEAD@{1} HEAD --name-only | Select-String "frontend-v2/package"
if ($frontendDepsChanged) {
    Write-Host "Frontend dependencies changed, updating..." -ForegroundColor Yellow
    cd frontend-v2
    npm install
    Write-Host "✓ Frontend dependencies updated" -ForegroundColor Green
    Write-Host ""
    cd ..
}

# Start service if it exists
if ($serviceExists) {
    Write-Host "Starting ROMS-V2-Backend service..." -ForegroundColor Yellow
    nssm start ROMS-V2-Backend
    Start-Sleep -Seconds 3
    
    $status = nssm status ROMS-V2-Backend
    if ($status -eq "SERVICE_RUNNING") {
        Write-Host "✓ Service started successfully" -ForegroundColor Green
        
        # Test health endpoint
        Start-Sleep -Seconds 2
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-Host "✓ Health check passed" -ForegroundColor Green
            }
        } catch {
            Write-Host "⚠ Health check failed - service may still be starting" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✗ Service failed to start: $status" -ForegroundColor Red
        Write-Host "Check logs at: C:\ROMS\backend-v2\logs\" -ForegroundColor Yellow
    }
} else {
    Write-Host "No service found. Backend not running as service." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✓ Update Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

