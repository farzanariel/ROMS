# ✅ Final Configuration - You're Almost There!

## 🎯 What's Done

✅ **On Mac:**
- Frontend configured to use `https://api.afarzan.com`
- Running at `http://localhost:3001`

✅ **On Windows Server:**
- Backend installed at `C:\ROMS\backend-v2`
- DNS configured: `api.afarzan.com`
- SSL certificate installed
- IIS reverse proxy configured
- Windows service created

---

## 🔧 Final Steps (Windows Server)

### Step 1: Verify Backend is Running

**Open PowerShell on Windows Server:**

```powershell
# Check service
nssm status ROMS-V2-Backend

# If stopped, start it
nssm start ROMS-V2-Backend

# Test health
Invoke-RestMethod -Uri "http://localhost:8001/health"
```

**Should return:** `{"status":"healthy","version":"2.0.0"...}`

---

### Step 2: Configure Refract Webhook

**In Refract (on Windows Server):**

1. Open Refract settings
2. Find **Webhook Configuration** or **Notifications**
3. Set **Checkout Success Webhook URL** to:
   ```
   http://localhost:8001/api/v2/webhooks/orders
   ```
4. **Save**

**Important:** Use `localhost` NOT `api.afarzan.com` because Refract and backend are on the same server!

---

### Step 3: Test Webhook

**Send a test checkout from Refract, then check:**

```powershell
# Check if webhook was received
Invoke-RestMethod -Uri "http://localhost:8001/api/v2/webhooks/queue/stats"

# Check for orders in database
Invoke-RestMethod -Uri "http://localhost:8001/api/v2/orders"
```

**You should see your test order!**

---

## 🖥️ View Orders on Mac

**On your Mac:**

1. Open browser: `http://localhost:3001`
2. You should see the "All Orders" page
3. Orders from Refract will appear automatically!

---

## 🔄 Complete Flow

```
Refract (Windows Server)
    ↓ localhost webhook
Backend (Windows Server)
    ↓ saves to SQLite
Database (Windows Server)
    ↓ API call via https
Frontend (Mac)
    ↓ displays
You see orders! 🎉
```

---

## ✅ Verification Checklist

**On Windows Server:**
- [ ] Service running: `nssm status ROMS-V2-Backend` = `SERVICE_RUNNING`
- [ ] Health check: `http://localhost:8001/health` = `{"status":"healthy"}`
- [ ] Refract webhook configured to: `http://localhost:8001/api/v2/webhooks/orders`

**On Mac:**
- [ ] Frontend running: `http://localhost:3001`
- [ ] Can see "All Orders" page
- [ ] WebSocket shows "Live" indicator

**Test:**
- [ ] Send checkout from Refract
- [ ] Order appears in database (check with PowerShell commands above)
- [ ] Order appears in Mac frontend (might need to refresh)

---

## 🆘 Troubleshooting

### Service Won't Start

```powershell
# Check logs
Get-Content C:\ROMS\backend-v2\logs\service-error.log -Tail 30

# Try running manually to see error
cd C:\ROMS\backend-v2
.\venv\Scripts\python.exe main.py
```

### Webhook Not Received

```powershell
# Check if backend is listening
netstat -ano | findstr :8001

# Check recent logs
Get-Content C:\ROMS\backend-v2\logs\service-output.log -Tail 50
```

### Frontend Can't Connect

**On Mac, check `.env` file:**
```bash
cat /Users/farzan/Documents/Projects/ROMS/frontend-v2/.env
```

Should show:
```
VITE_API_BASE_URL=https://api.afarzan.com
VITE_WS_URL=wss://api.afarzan.com/ws
```

If not, copy from `.env.example`:
```bash
cd /Users/farzan/Documents/Projects/ROMS/frontend-v2
cp .env.example .env
```

Then restart:
```bash
npm run dev
```

---

## 🎯 Quick Test Commands

**Windows Server - Check Everything:**
```powershell
Write-Host "=== System Status ===" -ForegroundColor Cyan
Write-Host "Service:" (nssm status ROMS-V2-Backend)
Write-Host "Health:" (Invoke-RestMethod "http://localhost:8001/health").status
Write-Host "Queue:" (Invoke-RestMethod "http://localhost:8001/api/v2/webhooks/queue/stats").workers_running "workers"
Write-Host "Orders:" (Invoke-RestMethod "http://localhost:8001/api/v2/orders").total "orders"
```

**Mac - Test Connection:**
```bash
curl https://api.afarzan.com/health
```

---

## 🎉 Success Criteria

You'll know everything is working when:

1. ✅ Refract sends checkout
2. ✅ Windows PowerShell shows order in database
3. ✅ Mac frontend shows order in table
4. ✅ WebSocket indicator says "Live"

---

## 📞 Command Reference

**Windows Server:**
```powershell
# Start service
nssm start ROMS-V2-Backend

# Stop service
nssm stop ROMS-V2-Backend

# Restart service
nssm restart ROMS-V2-Backend

# View logs
Get-Content C:\ROMS\backend-v2\backend.log -Tail 50 -Wait

# Test health
Invoke-RestMethod "http://localhost:8001/health"

# Check orders
Invoke-RestMethod "http://localhost:8001/api/v2/orders" | ConvertTo-Json
```

**Mac:**
```bash
# Start frontend
cd /Users/farzan/Documents/Projects/ROMS/frontend-v2
npm run dev

# Test API connection
curl https://api.afarzan.com/health

# View orders
curl https://api.afarzan.com/api/v2/orders
```

---

## 🚀 You're Ready!

Everything is configured. Now just:

1. **Ensure service is running on Windows**
2. **Configure Refract webhook to `http://localhost:8001/api/v2/webhooks/orders`**
3. **Open frontend on Mac at `http://localhost:3001`**
4. **Send a test checkout!**

---

**Need help? Run the verification checklist commands above and tell me what you see!** 🎯

