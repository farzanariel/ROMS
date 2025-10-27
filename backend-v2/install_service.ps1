# ROMS V2 - Install as Windows Service
# Run this AFTER setup_windows.ps1 and IIS configuration

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ROMS V2 - Service Installation" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$backendPath = "C:\ROMS\backend-v2"
$serviceName = "ROMS-V2-Backend"
$pythonExe = "$backendPath\venv\Scripts\python.exe"
$mainPy = "$backendPath\main.py"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    exit 1
}

# Check if NSSM is installed
try {
    $nssmPath = (Get-Command nssm).Source
    Write-Host "✓ NSSM found at: $nssmPath" -ForegroundColor Green
} catch {
    Write-Host "✗ NSSM not found!" -ForegroundColor Red
    Write-Host "Install NSSM first:" -ForegroundColor Yellow
    Write-Host "  Option 1: choco install nssm" -ForegroundColor Gray
    Write-Host "  Option 2: Download from https://nssm.cc/download" -ForegroundColor Gray
    exit 1
}
Write-Host ""

# Check if service already exists
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    Write-Host "Service '$serviceName' already exists!" -ForegroundColor Yellow
    $response = Read-Host "Do you want to remove and reinstall? (y/N)"
    if ($response -eq "y" -or $response -eq "Y") {
        Write-Host "Stopping and removing existing service..." -ForegroundColor Yellow
        nssm stop $serviceName
        nssm remove $serviceName confirm
        Write-Host "✓ Existing service removed" -ForegroundColor Green
    } else {
        Write-Host "Installation cancelled." -ForegroundColor Gray
        exit 0
    }
}
Write-Host ""

# Install service
Write-Host "Installing Windows Service..." -ForegroundColor Yellow
Write-Host "  Service Name: $serviceName" -ForegroundColor Gray
Write-Host "  Python: $pythonExe" -ForegroundColor Gray
Write-Host "  Script: $mainPy" -ForegroundColor Gray
Write-Host ""

# Create the service
nssm install $serviceName $pythonExe $mainPy

# Configure service
nssm set $serviceName AppDirectory $backendPath
nssm set $serviceName DisplayName "ROMS V2 Backend"
nssm set $serviceName Description "ROMS V2 Order Management System - Automated Backend"
nssm set $serviceName Start SERVICE_AUTO_START

# Set logging
$logPath = "$backendPath\logs"
if (-not (Test-Path $logPath)) {
    New-Item -ItemType Directory -Path $logPath -Force | Out-Null
}
nssm set $serviceName AppStdout "$logPath\service-output.log"
nssm set $serviceName AppStderr "$logPath\service-error.log"

# Set environment
nssm set $serviceName AppEnvironmentExtra "PYTHONUNBUFFERED=1"

Write-Host "✓ Service installed successfully!" -ForegroundColor Green
Write-Host ""

# Start service
Write-Host "Starting service..." -ForegroundColor Yellow
nssm start $serviceName
Start-Sleep -Seconds 3

# Check service status
$status = nssm status $serviceName
Write-Host "Service Status: $status" -ForegroundColor $(if ($status -eq "SERVICE_RUNNING") { "Green" } else { "Red" })
Write-Host ""

if ($status -eq "SERVICE_RUNNING") {
    Write-Host "✓ Service is running!" -ForegroundColor Green
    Write-Host ""
    
    # Test health endpoint
    Start-Sleep -Seconds 2
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Backend health check passed!" -ForegroundColor Green
            Write-Host "  Response: $($response.Content)" -ForegroundColor Gray
        }
    } catch {
        Write-Host "⚠ Backend might still be starting..." -ForegroundColor Yellow
        Write-Host "  Wait a few seconds and check: http://localhost:8001/health" -ForegroundColor Gray
    }
} else {
    Write-Host "✗ Service failed to start!" -ForegroundColor Red
    Write-Host "Check logs at: $logPath" -ForegroundColor Yellow
}
Write-Host ""

# Show useful commands
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Service Management Commands" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check Status:" -ForegroundColor Yellow
Write-Host "  nssm status $serviceName" -ForegroundColor Gray
Write-Host ""
Write-Host "Start Service:" -ForegroundColor Yellow
Write-Host "  nssm start $serviceName" -ForegroundColor Gray
Write-Host ""
Write-Host "Stop Service:" -ForegroundColor Yellow
Write-Host "  nssm stop $serviceName" -ForegroundColor Gray
Write-Host ""
Write-Host "Restart Service:" -ForegroundColor Yellow
Write-Host "  nssm restart $serviceName" -ForegroundColor Gray
Write-Host ""
Write-Host "View Logs:" -ForegroundColor Yellow
Write-Host "  Get-Content $logPath\service-output.log -Tail 50" -ForegroundColor Gray
Write-Host "  Get-Content $logPath\service-error.log -Tail 50" -ForegroundColor Gray
Write-Host ""
Write-Host "Remove Service (if needed):" -ForegroundColor Yellow
Write-Host "  nssm stop $serviceName" -ForegroundColor Gray
Write-Host "  nssm remove $serviceName confirm" -ForegroundColor Gray
Write-Host ""
Write-Host "✓ Installation complete!" -ForegroundColor Green
Write-Host ""

