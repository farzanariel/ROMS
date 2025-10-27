# Quick Start Script for Windows Backend
# Run this in PowerShell on Windows Server

Write-Host "🚀 Starting ROMS V2 Backend Setup..." -ForegroundColor Cyan

# Navigate to project
Set-Location C:\ROMS\backend-v2

# Step 1: Create virtual environment
Write-Host "`n📦 Creating virtual environment..." -ForegroundColor Yellow
python -m venv venv

# Step 2: Activate and upgrade pip
Write-Host "`n⚡ Activating environment and upgrading pip..." -ForegroundColor Yellow
& .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# Step 3: Install dependencies
Write-Host "`n📚 Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Step 4: Start backend
Write-Host "`n🎉 Starting backend server..." -ForegroundColor Green
Write-Host "Backend will run on: http://localhost:8001" -ForegroundColor Cyan
Write-Host "Health check: http://localhost:8001/health" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop`n" -ForegroundColor Yellow

python main.py

