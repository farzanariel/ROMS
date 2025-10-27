# ✅ Quick Start Checklist - api.afarzan.com

Print this and check off each step!

---

## ☐ Phase 1: Get Public IP (5 min)

**On Windows Server:**
```powershell
Invoke-RestMethod -Uri "https://api.ipify.org?format=text"
```

**Write IP here:** `_________________`

---

## ☐ Phase 2: Configure IONOS DNS (10 min)

- [ ] Log in to IONOS.com
- [ ] Go to Domains → afarzan.com → DNS Settings
- [ ] Add A Record:
  - Type: A
  - Hostname: `api`
  - Points to: `[Your IP from Phase 1]`
  - TTL: 3600
- [ ] Save
- [ ] Wait 15 minutes
- [ ] Check: https://dnschecker.org (search `api.afarzan.com`)

---

## ☐ Phase 3: Transfer Files (15 min)

- [ ] Connect to Windows Server (Remote Desktop)
- [ ] Create folder: `C:\ROMS`
- [ ] Copy `backend-v2` folder to server
- [ ] Verify files exist at: `C:\ROMS\backend-v2`

---

## ☐ Phase 4: Run Setup Script (5 min)

**As Administrator:**
```powershell
cd C:\ROMS\backend-v2
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```

- [ ] Python found ✓
- [ ] Virtual environment created ✓
- [ ] Dependencies installed ✓
- [ ] .env file created ✓
- [ ] Backend test passed ✓

---

## ☐ Phase 5: Edit .env File (5 min)

```powershell
notepad C:\ROMS\backend-v2\.env
```

**Update:**
- [ ] `CORS_ORIGINS=https://api.afarzan.com,https://afarzan.com`
- [ ] `SECRET_KEY=[random string]`
- [ ] `WEBHOOK_SECRET=[random string]`
- [ ] `WEBHOOK_BASE_URL=https://api.afarzan.com/api/v2/webhooks`

**Save and close**

---

## ☐ Phase 6: Test Backend (2 min)

```powershell
cd C:\ROMS\backend-v2
.\venv\Scripts\Activate.ps1
python main.py
```

- [ ] Backend starts without errors ✓
- [ ] Visit: `http://localhost:8001/health` ✓
- [ ] Press Ctrl+C to stop

---

## ☐ Phase 7: Install IIS (20 min)

**Install components:**
```powershell
Install-WindowsFeature -name Web-Server -IncludeManagementTools
Install-WindowsFeature -name Web-WebSockets
```

**Download & Install:**
- [ ] URL Rewrite Module
- [ ] Application Request Routing (ARR)

**Configure IIS Manager:**
- [ ] Enable ARR Proxy (Server → ARR Cache → Server Proxy Settings → Enable)
- [ ] Create Website "ROMS-V2-API"
  - Physical path: `C:\ROMS\backend-v2`
  - Binding: http, port 80, hostname: `api.afarzan.com`
- [ ] Add URL Rewrite Rule (Reverse Proxy to `127.0.0.1:8001`)

**Firewall:**
```powershell
New-NetFirewallRule -DisplayName "HTTP (Port 80)" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow
New-NetFirewallRule -DisplayName "HTTPS (Port 443)" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

## ☐ Phase 8: Install as Service (5 min)

```powershell
# Install NSSM
choco install nssm -y

# Run service installer
cd C:\ROMS\backend-v2
powershell -ExecutionPolicy Bypass -File install_service.ps1
```

**Verify:**
```powershell
nssm status ROMS-V2-Backend
# Should show: SERVICE_RUNNING
```

---

## ☐ Phase 9: Install SSL Certificate (15 min)

```powershell
# Install win-acme
choco install win-acme -y

# Run win-acme
wacs.exe
```

**Follow prompts:**
- [ ] Create certificate with advanced options
- [ ] Manual input → `api.afarzan.com`
- [ ] http-01 validation
- [ ] Path: `C:\ROMS\backend-v2`
- [ ] Bind to IIS site

**Add HTTPS binding in IIS:**
- [ ] Open IIS Manager
- [ ] Site → Bindings → Add
- [ ] Type: https, Port: 443, Hostname: `api.afarzan.com`
- [ ] Select SSL certificate

---

## ☐ Phase 10: Test Production (5 min)

**On Windows Server:**
```powershell
Invoke-RestMethod -Uri "https://api.afarzan.com/health"
```

**On your Mac:**
```bash
curl https://api.afarzan.com/health
```

**Expected response:**
```json
{"status":"healthy","version":"2.0.0",...}
```

- [ ] HTTPS works ✓
- [ ] Health check passes ✓

---

## ☐ Phase 11: Update Refract (2 min)

- [ ] Log in to Refract
- [ ] Go to Webhook Settings
- [ ] Update Checkout Success URL to:
  ```
  https://api.afarzan.com/api/v2/webhooks/orders
  ```
- [ ] Save

---

## ☐ Phase 12: Send Test Webhook! (1 min)

- [ ] Trigger a checkout in Refract
- [ ] Check Windows Server logs:
  ```powershell
  Get-Content C:\ROMS\backend-v2\backend.log -Tail 20 -Wait
  ```
- [ ] Check orders API:
  ```powershell
  Invoke-RestMethod -Uri "https://api.afarzan.com/api/v2/orders"
  ```
- [ ] Order appears! 🎉

---

## 🎉 SUCCESS!

**Your Production Webhook URL:**
```
https://api.afarzan.com/api/v2/webhooks/orders
```

**Useful URLs:**
- Health: `https://api.afarzan.com/health`
- API Docs: `https://api.afarzan.com/docs`
- Queue Stats: `https://api.afarzan.com/api/v2/webhooks/queue/stats`
- Orders: `https://api.afarzan.com/api/v2/orders`

**Service Management:**
```powershell
nssm status ROMS-V2-Backend   # Check status
nssm restart ROMS-V2-Backend  # Restart
nssm stop ROMS-V2-Backend     # Stop
nssm start ROMS-V2-Backend    # Start
```

---

**🚀 You're live with production webhooks!**

**Estimated Total Time:** 1-2 hours

