# ROMS V2 - Complete Interactive Setup for Windows Server
# This script will set up EVERYTHING for you

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  ROMS V2 - Complete Automated Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "This script will:" -ForegroundColor Yellow
Write-Host "  1. Check and install prerequisites" -ForegroundColor White
Write-Host "  2. Set up Python environment" -ForegroundColor White
Write-Host "  3. Configure environment variables" -ForegroundColor White
Write-Host "  4. Install IIS and required modules" -ForegroundColor White
Write-Host "  5. Configure reverse proxy" -ForegroundColor White
Write-Host "  6. Create Windows service" -ForegroundColor White
Write-Host "  7. Test everything" -ForegroundColor White
Write-Host ""

# Check Admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Running as Administrator" -ForegroundColor Green
Write-Host ""

# Configuration
$backendPath = "C:\ROMS\backend-v2"

# Ask for domain
Write-Host "What is your domain?" -ForegroundColor Yellow
Write-Host "Example: api.afarzan.com" -ForegroundColor Gray
$domain = Read-Host "Enter domain"
Write-Host ""

# Ask for server IP
Write-Host "Getting your public IP address..." -ForegroundColor Yellow
try {
    $publicIP = Invoke-RestMethod -Uri "https://api.ipify.org?format=text" -TimeoutSec 5
    Write-Host "Your public IP: $publicIP" -ForegroundColor Green
} catch {
    Write-Host "Could not auto-detect. Please enter manually." -ForegroundColor Yellow
    $publicIP = Read-Host "Enter your server's public IP"
}
Write-Host ""

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 1: Checking Prerequisites" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  Python NOT found!" -ForegroundColor Red
    Write-Host "  Opening Python download page..." -ForegroundColor Yellow
    Start-Process "https://www.python.org/downloads/windows/"
    Write-Host "  Please install Python 3.9+ and run this script again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Chocolatey
Write-Host "Checking Chocolatey..." -ForegroundColor Yellow
try {
    choco --version | Out-Null
    Write-Host "  Chocolatey found" -ForegroundColor Green
} catch {
    Write-Host "  Installing Chocolatey..." -ForegroundColor Yellow
    Set-ExecutionPolicy Bypass -Scope Process -Force
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    Write-Host "  Chocolatey installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 2: Setting Up Python Environment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $backendPath

if (Test-Path ".\venv") {
    Write-Host "  Virtual environment already exists" -ForegroundColor Gray
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "  Virtual environment created" -ForegroundColor Green
}

Write-Host "Installing dependencies..." -ForegroundColor Yellow
$venvPip = ".\venv\Scripts\pip.exe"
$venvPython = ".\venv\Scripts\python.exe"

if (Test-Path $venvPip) {
    & $venvPip install --upgrade pip --quiet
    & $venvPip install -r requirements.txt --quiet
} else {
    Write-Host "  Using direct python install..." -ForegroundColor Gray
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r requirements.txt --quiet
}
Write-Host "  Dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 3: Configuring Environment" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Create .env file
$envContent = @"
# ROMS V2 - Production Configuration

# Database
DATABASE_URL=sqlite+aiosqlite:///./roms_v2.db

# API Configuration
API_V2_HOST=127.0.0.1
API_V2_PORT=8001
API_V2_RELOAD=false

# Security - CHANGE THESE!
SECRET_KEY=$(-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_}))
WEBHOOK_SECRET=$(-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_}))

# CORS Settings
CORS_ORIGINS=https://$domain,https://www.$domain

# Webhook Configuration
WEBHOOK_BASE_URL=https://$domain/api/v2/webhooks

# Logging
LOG_LEVEL=INFO
LOG_FILE=backend.log
ENABLE_SQL_LOGGING=false

# Feature Flags
ENABLE_WEBHOOKS=true
ENABLE_EMAIL_SCRAPING=false
ENABLE_WEB_SCRAPING=false
ENABLE_REALTIME_WEBSOCKET=true
ENABLE_SCHEDULER=false

# Production Settings
ENVIRONMENT=production
DEBUG=false
"@

$envContent | Out-File -FilePath ".\.env" -Encoding UTF8 -Force
Write-Host "  .env file created with random secret keys" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 4: Installing IIS Components" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installing IIS..." -ForegroundColor Yellow
Install-WindowsFeature -name Web-Server -IncludeManagementTools | Out-Null
Install-WindowsFeature -name Web-WebSockets | Out-Null
Write-Host "  IIS installed" -ForegroundColor Green

Write-Host "Installing URL Rewrite..." -ForegroundColor Yellow
choco install urlrewrite -y --no-progress | Out-Null
Write-Host "  URL Rewrite installed" -ForegroundColor Green

Write-Host "Installing Application Request Routing..." -ForegroundColor Yellow
choco install iis-arr -y --no-progress | Out-Null
Write-Host "  ARR installed" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 5: Configuring IIS Reverse Proxy" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Import IIS module
Import-Module WebAdministration

# Enable ARR Proxy
Write-Host "Enabling ARR proxy..." -ForegroundColor Yellow
$arrConfig = Get-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled"
Set-WebConfigurationProperty -pspath 'MACHINE/WEBROOT/APPHOST' -filter "system.webServer/proxy" -name "enabled" -value "True"
Write-Host "  ARR proxy enabled" -ForegroundColor Green

# Create IIS site
Write-Host "Creating IIS website..." -ForegroundColor Yellow
$siteName = "ROMS-V2-API"

# Remove if exists
if (Get-Website -Name $siteName -ErrorAction SilentlyContinue) {
    Remove-Website -Name $siteName
}

# Create site
New-Website -Name $siteName -PhysicalPath $backendPath -Port 80 -HostHeader $domain -Force | Out-Null
Write-Host "  Website created" -ForegroundColor Green

# Add rewrite rule
Write-Host "Adding reverse proxy rule..." -ForegroundColor Yellow
$ruleName = "ReverseProxyToBackend"
Remove-WebConfigurationProperty -PSPath "IIS:\Sites\$siteName" -Filter "system.webServer/rewrite/rules" -Name "." -AtElement @{name=$ruleName} -ErrorAction SilentlyContinue

Add-WebConfigurationProperty -PSPath "IIS:\Sites\$siteName" -Filter "system.webServer/rewrite/rules" -Name "." -Value @{
    name = $ruleName
    stopProcessing = 'True'
}

Set-WebConfigurationProperty -PSPath "IIS:\Sites\$siteName" -Filter "system.webServer/rewrite/rules/rule[@name='$ruleName']/match" -Name "url" -Value "(.*)"

Add-WebConfigurationProperty -PSPath "IIS:\Sites\$siteName" -Filter "system.webServer/rewrite/rules/rule[@name='$ruleName']/action" -Name "." -Value @{
    type = 'Rewrite'
    url = 'http://127.0.0.1:8001/{R:1}'
}

Write-Host "  Reverse proxy configured" -ForegroundColor Green

# Configure firewall
Write-Host "Configuring firewall..." -ForegroundColor Yellow
New-NetFirewallRule -DisplayName "HTTP (Port 80)" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow -ErrorAction SilentlyContinue | Out-Null
New-NetFirewallRule -DisplayName "HTTPS (Port 443)" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow -ErrorAction SilentlyContinue | Out-Null
Write-Host "  Firewall configured" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 6: Installing NSSM & Creating Service" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Installing NSSM..." -ForegroundColor Yellow
choco install nssm -y --no-progress | Out-Null
Write-Host "  NSSM installed" -ForegroundColor Green

Write-Host "Creating Windows service..." -ForegroundColor Yellow
$serviceName = "ROMS-V2-Backend"
$pythonExe = "$backendPath\venv\Scripts\python.exe"
$mainPy = "$backendPath\main.py"

# Remove if exists
$existingService = Get-Service -Name $serviceName -ErrorAction SilentlyContinue
if ($existingService) {
    nssm stop $serviceName | Out-Null
    nssm remove $serviceName confirm | Out-Null
}

# Install service
nssm install $serviceName $pythonExe $mainPy | Out-Null
nssm set $serviceName AppDirectory $backendPath | Out-Null
nssm set $serviceName DisplayName "ROMS V2 Backend" | Out-Null
nssm set $serviceName Description "ROMS V2 Order Management System" | Out-Null
nssm set $serviceName Start SERVICE_AUTO_START | Out-Null

# Create logs directory
New-Item -ItemType Directory -Path "$backendPath\logs" -Force | Out-Null
nssm set $serviceName AppStdout "$backendPath\logs\service-output.log" | Out-Null
nssm set $serviceName AppStderr "$backendPath\logs\service-error.log" | Out-Null

# Start service
nssm start $serviceName | Out-Null
Start-Sleep -Seconds 5
Write-Host "  Service created and started" -ForegroundColor Green

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "STEP 7: Testing Everything" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Test service
Write-Host "Testing service status..." -ForegroundColor Yellow
$status = nssm status $serviceName
if ($status -eq "SERVICE_RUNNING") {
    Write-Host "  Service is running" -ForegroundColor Green
} else {
    Write-Host "  WARNING: Service status: $status" -ForegroundColor Yellow
}

# Test backend
Write-Host "Testing backend health..." -ForegroundColor Yellow
Start-Sleep -Seconds 3
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 5 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "  Backend is responding" -ForegroundColor Green
    }
} catch {
    Write-Host "  WARNING: Backend health check failed" -ForegroundColor Yellow
    Write-Host "  Check logs: $backendPath\logs\" -ForegroundColor Gray
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "NEXT STEPS:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. UPDATE DNS (IMPORTANT!):" -ForegroundColor White
Write-Host "   Go to IONOS DNS settings for afarzan.com" -ForegroundColor Gray
Write-Host "   Add A Record:" -ForegroundColor Gray
Write-Host "     Type: A" -ForegroundColor Gray
Write-Host "     Hostname: api" -ForegroundColor Gray
Write-Host "     Points to: $publicIP" -ForegroundColor Gray
Write-Host "     TTL: 3600" -ForegroundColor Gray
Write-Host ""
Write-Host "2. INSTALL SSL CERTIFICATE:" -ForegroundColor White
Write-Host "   Run: choco install win-acme -y" -ForegroundColor Gray
Write-Host "   Then: wacs.exe" -ForegroundColor Gray
Write-Host "   Follow prompts to get free SSL certificate" -ForegroundColor Gray
Write-Host ""
Write-Host "3. UPDATE REFRACT:" -ForegroundColor White
Write-Host "   Webhook URL: https://$domain/api/v2/webhooks/orders" -ForegroundColor Gray
Write-Host ""
Write-Host "Your webhook endpoint: https://$domain/api/v2/webhooks/orders" -ForegroundColor Cyan
Write-Host ""
Write-Host "Service Management:" -ForegroundColor White
Write-Host "  Status: nssm status $serviceName" -ForegroundColor Gray
Write-Host "  Restart: nssm restart $serviceName" -ForegroundColor Gray
Write-Host "  Logs: $backendPath\logs\" -ForegroundColor Gray
Write-Host ""

Read-Host "Press Enter to exit"

