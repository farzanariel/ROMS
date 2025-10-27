# ROMS V2 - Windows Server Setup Script
# Run this on your Windows Server with Administrator privileges

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ROMS V2 - Windows Server Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$installPath = "C:\ROMS"
$backendPath = "$installPath\backend-v2"

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Running as Administrator" -ForegroundColor Green
Write-Host ""

# Step 1: Check Python Installation
Write-Host "Step 1: Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found!" -ForegroundColor Red
    Write-Host "Please install Python 3.9+ from https://www.python.org/downloads/windows/" -ForegroundColor Yellow
    Write-Host "IMPORTANT: Check 'Add Python to PATH' during installation!" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 2: Check if project exists
Write-Host "Step 2: Checking project location..." -ForegroundColor Yellow
if (Test-Path $backendPath) {
    Write-Host "✓ Project found at: $backendPath" -ForegroundColor Green
} else {
    Write-Host "✗ Project not found at: $backendPath" -ForegroundColor Red
    Write-Host "Please transfer your backend-v2 folder to this location first!" -ForegroundColor Yellow
    exit 1
}
Write-Host ""

# Step 3: Create Virtual Environment
Write-Host "Step 3: Setting up Python virtual environment..." -ForegroundColor Yellow
Set-Location $backendPath

if (Test-Path ".\venv") {
    Write-Host "  Virtual environment already exists, skipping..." -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}
Write-Host ""

# Step 4: Install Dependencies
Write-Host "Step 4: Installing Python dependencies..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
pip install --upgrade pip
pip install -r requirements.txt
Write-Host "✓ Dependencies installed" -ForegroundColor Green
Write-Host ""

# Step 5: Setup Environment File
Write-Host "Step 5: Setting up environment configuration..." -ForegroundColor Yellow
if (Test-Path ".\.env") {
    Write-Host "  .env file already exists, skipping..." -ForegroundColor Gray
} else {
    if (Test-Path ".\.env.production") {
        Copy-Item ".\.env.production" ".\.env"
        Write-Host "✓ Created .env from .env.production template" -ForegroundColor Green
        Write-Host "  IMPORTANT: Edit .env and update with your domain and secrets!" -ForegroundColor Yellow
    } else {
        Write-Host "✗ .env.production template not found!" -ForegroundColor Red
    }
}
Write-Host ""

# Step 6: Test Backend
Write-Host "Step 6: Testing backend..." -ForegroundColor Yellow
Write-Host "  Starting backend for 5 seconds to verify it works..." -ForegroundColor Gray

$job = Start-Job -ScriptBlock {
    Set-Location $using:backendPath
    & ".\venv\Scripts\Activate.ps1"
    python main.py
}

Start-Sleep -Seconds 5

# Check if backend is responding
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Backend is working correctly!" -ForegroundColor Green
    }
} catch {
    Write-Host "✗ Backend health check failed!" -ForegroundColor Red
    Write-Host "  This might be normal if backend takes longer to start" -ForegroundColor Gray
}

Stop-Job -Job $job
Remove-Job -Job $job
Write-Host ""

# Step 7: Check IIS
Write-Host "Step 7: Checking IIS installation..." -ForegroundColor Yellow
$iis = Get-Service -Name "W3SVC" -ErrorAction SilentlyContinue
if ($iis) {
    Write-Host "✓ IIS is installed" -ForegroundColor Green
} else {
    Write-Host "✗ IIS not found!" -ForegroundColor Red
    Write-Host "  Install IIS from Server Manager > Add Roles and Features" -ForegroundColor Yellow
}
Write-Host ""

# Step 8: Check if NSSM is installed
Write-Host "Step 8: Checking NSSM (Windows Service Manager)..." -ForegroundColor Yellow
try {
    $nssmVersion = nssm --version 2>&1
    Write-Host "✓ NSSM is installed" -ForegroundColor Green
} catch {
    Write-Host "✗ NSSM not found!" -ForegroundColor Red
    Write-Host "  Install with: choco install nssm" -ForegroundColor Yellow
    Write-Host "  Or download from: https://nssm.cc/download" -ForegroundColor Yellow
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Setup Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend Location: $backendPath" -ForegroundColor White
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Edit .env file with your domain and secret keys" -ForegroundColor White
Write-Host "  2. Configure IIS reverse proxy (see PRODUCTION_DEPLOYMENT.md)" -ForegroundColor White
Write-Host "  3. Set up DNS to point your domain to this server" -ForegroundColor White
Write-Host "  4. Install SSL certificate (win-acme for Let`'s Encrypt)" -ForegroundColor White
Write-Host "  5. Create Windows service with NSSM" -ForegroundColor White
Write-Host ""
Write-Host "Test Locally:" -ForegroundColor Yellow
Write-Host "  cd $backendPath" -ForegroundColor Gray
Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Gray
Write-Host "  python main.py" -ForegroundColor Gray
Write-Host "  # Visit: http://localhost:8001/health" -ForegroundColor Gray
Write-Host ""
Write-Host "✓ Setup complete! See PRODUCTION_DEPLOYMENT.md for next steps." -ForegroundColor Green
Write-Host ""

