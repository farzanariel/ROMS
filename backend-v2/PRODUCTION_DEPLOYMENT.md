# 🚀 Production Deployment Guide - Windows Server + Custom Domain

## Overview

This guide walks you through deploying ROMS V2 to your **Windows server** with your **custom domain name** for production use.

---

## 📋 Prerequisites

- ✅ Windows Server (with admin access)
- ✅ Custom domain name (e.g., `yourdomain.com`)
- ✅ Domain DNS access (to add A record or CNAME)
- ✅ Port 80 (HTTP) and 443 (HTTPS) open on firewall

---

## 🏗️ Architecture

```
Internet
   ↓
Your Domain (yourdomain.com)
   ↓
Windows Server (Static IP)
   ↓
Nginx/IIS (Reverse Proxy) - Port 80/443
   ↓
Backend V2 (FastAPI) - Port 8001
   ↓
SQLite Database
```

**Webhook URL:** `https://yourdomain.com/api/v2/webhooks/orders`

---

## 🔧 Method 1: Using IIS (Recommended for Windows)

### Step 1: Install Python on Windows Server

1. Download Python 3.9+ from [python.org](https://www.python.org/downloads/windows/)
2. **IMPORTANT**: Check "Add Python to PATH" during installation
3. Verify:
   ```powershell
   python --version
   pip --version
   ```

### Step 2: Transfer Your Project to Server

**Option A: Git Clone**
```powershell
cd C:\inetpub\wwwroot
git clone <your-repo-url> ROMS
cd ROMS\backend-v2
```

**Option B: Manual Transfer**
- Copy entire `backend-v2` folder to `C:\inetpub\wwwroot\ROMS\backend-v2`

### Step 3: Install Dependencies

```powershell
cd C:\inetpub\wwwroot\ROMS\backend-v2
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Configure Backend for Production

Create `.env` file:
```env
# Production Environment
DATABASE_URL=sqlite:///./roms_v2.db
ENVIRONMENT=production
LOG_LEVEL=INFO

# Security (change these!)
SECRET_KEY=your-super-secret-key-change-this
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Server
HOST=127.0.0.1
PORT=8001
```

### Step 5: Test Backend Locally on Server

```powershell
python main.py
```

**Check:** Open browser on server → `http://localhost:8001/health`

If working, press `Ctrl+C` to stop.

### Step 6: Install IIS and Required Modules

**A. Enable IIS:**
1. Open **Server Manager**
2. **Add Roles and Features**
3. Select **Web Server (IIS)**
4. Include **WebSocket Protocol**

**B. Install URL Rewrite Module:**
- Download: [IIS URL Rewrite](https://www.iis.net/downloads/microsoft/url-rewrite)
- Install on server

**C. Install Application Request Routing (ARR):**
- Download: [IIS ARR](https://www.iis.net/downloads/microsoft/application-request-routing)
- Install on server

### Step 7: Configure IIS Reverse Proxy

**A. Open IIS Manager**

**B. Enable Proxy (ARR):**
1. Click server name in left panel
2. Double-click **Application Request Routing Cache**
3. Click **Server Proxy Settings** (right panel)
4. Check **Enable proxy**
5. Click **Apply**

**C. Create Website:**
1. Right-click **Sites** → **Add Website**
   - **Site name:** ROMS-V2
   - **Physical path:** `C:\inetpub\wwwroot\ROMS\backend-v2`
   - **Binding:**
     - Type: `http`
     - IP: `All Unassigned`
     - Port: `80`
     - Hostname: `yourdomain.com`

**D. Add Rewrite Rule:**
1. Click your site (ROMS-V2)
2. Double-click **URL Rewrite**
3. Click **Add Rule** → **Reverse Proxy**
4. Enter: `127.0.0.1:8001`
5. Click **OK**

### Step 8: Run Backend as Windows Service

**Create `run_backend.bat`:**
```batch
@echo off
cd C:\inetpub\wwwroot\ROMS\backend-v2
call venv\Scripts\activate
python main.py
```

**Install NSSM (Non-Sucking Service Manager):**
```powershell
# Download from https://nssm.cc/download
# Or use chocolatey:
choco install nssm

# Create service
nssm install ROMS-V2-Backend "C:\inetpub\wwwroot\ROMS\backend-v2\run_backend.bat"
nssm set ROMS-V2-Backend AppDirectory "C:\inetpub\wwwroot\ROMS\backend-v2"
nssm set ROMS-V2-Backend DisplayName "ROMS V2 Backend Service"
nssm set ROMS-V2-Backend Description "ROMS V2 Order Management Backend"
nssm set ROMS-V2-Backend Start SERVICE_AUTO_START

# Start service
nssm start ROMS-V2-Backend
```

**Verify Service:**
```powershell
nssm status ROMS-V2-Backend
# Should show: SERVICE_RUNNING
```

### Step 9: Configure DNS

**Add A Record (or Update Existing):**
```
Type: A
Name: @ (or subdomain like "orders")
Value: <Your Windows Server Public IP>
TTL: 3600
```

**Example:**
- Main domain: `yourdomain.com` → `123.45.67.89`
- Subdomain: `orders.yourdomain.com` → `123.45.67.89`

**Wait 5-15 minutes for DNS propagation**

### Step 10: Add SSL Certificate (HTTPS)

**Option A: Let's Encrypt (Free)**

1. Install **win-acme**:
   ```powershell
   choco install win-acme
   ```

2. Run setup:
   ```powershell
   wacs.exe
   ```

3. Follow prompts:
   - Choose your IIS site (ROMS-V2)
   - Enter your domain
   - It will automatically configure SSL

**Option B: Paid SSL Certificate**
- Purchase from provider (Namecheap, GoDaddy, etc.)
- Import certificate to IIS
- Bind certificate to your site

**After SSL setup, update IIS binding:**
- Type: `https`
- Port: `443`
- SSL Certificate: (select your certificate)

---

## 🔧 Method 2: Using Nginx on Windows (Alternative)

### Step 1-5: Same as IIS method above

### Step 6: Install Nginx for Windows

```powershell
# Download from nginx.org
cd C:\nginx
```

### Step 7: Configure Nginx

Edit `C:\nginx\conf\nginx.conf`:

```nginx
http {
    upstream backend {
        server 127.0.0.1:8001;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate     C:/certs/yourdomain.crt;
        ssl_certificate_key C:/certs/yourdomain.key;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        # Webhook endpoint
        location /api/v2/webhooks/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # All other API endpoints
        location /api/ {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }

        # WebSocket
        location /ws {
            proxy_pass http://backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }

        # Frontend (optional - if hosting frontend on same domain)
        location / {
            root C:/inetpub/wwwroot/ROMS/frontend-v2/dist;
            try_files $uri $uri/ /index.html;
        }
    }
}
```

### Step 8: Run Nginx as Windows Service

```powershell
# Install Nginx as service
nssm install Nginx "C:\nginx\nginx.exe"
nssm set Nginx AppDirectory "C:\nginx"
nssm start Nginx
```

---

## 🧪 Testing Your Production Setup

### 1. Test Backend Health

```bash
curl https://yourdomain.com/health
# Should return: {"status":"healthy",...}
```

### 2. Test Webhook Endpoint

```bash
curl -X POST https://yourdomain.com/api/v2/webhooks/orders \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

### 3. Update Refract

In Refract settings, update webhook URL to:
```
https://yourdomain.com/api/v2/webhooks/orders
```

### 4. Send Test Checkout

- Trigger a real checkout in Refract
- Check logs: `C:\inetpub\wwwroot\ROMS\backend-v2\backend.log`
- Check database: Orders should appear

---

## 🔒 Security Checklist

- ✅ HTTPS enabled (SSL certificate)
- ✅ Changed default SECRET_KEY in `.env`
- ✅ Firewall allows only ports 80, 443
- ✅ Windows Defender enabled
- ✅ Regular Windows Updates
- ✅ Strong admin passwords
- ✅ Database backups configured
- ✅ Logs monitored

---

## 📊 Monitoring & Logs

### Backend Logs
```
C:\inetpub\wwwroot\ROMS\backend-v2\backend.log
```

### IIS Logs
```
C:\inetpub\logs\LogFiles\W3SVC1\
```

### Service Status
```powershell
# Check backend service
nssm status ROMS-V2-Backend

# Restart if needed
nssm restart ROMS-V2-Backend
```

---

## 🔄 Updating Your Production Server

```powershell
# Stop service
nssm stop ROMS-V2-Backend

# Pull latest code
cd C:\inetpub\wwwroot\ROMS\backend-v2
git pull

# Update dependencies
.\venv\Scripts\activate
pip install -r requirements.txt --upgrade

# Restart service
nssm start ROMS-V2-Backend
```

---

## 🚀 Frontend Deployment (Optional)

If you want to host the frontend on the same server:

### 1. Build Frontend

**On your Mac:**
```bash
cd frontend-v2
npm run build
# Creates: dist/ folder
```

### 2. Transfer to Server

Copy `dist/` folder to:
```
C:\inetpub\wwwroot\ROMS\frontend-v2\dist
```

### 3. Update Frontend Config

Edit `dist/assets/index-*.js` (or rebuild with correct env):
```javascript
VITE_API_BASE_URL=https://yourdomain.com
VITE_WS_URL=wss://yourdomain.com/ws
```

### 4. Access Frontend

```
https://yourdomain.com
```

---

## 🆘 Troubleshooting

### Backend Won't Start

```powershell
# Check logs
Get-Content C:\inetpub\wwwroot\ROMS\backend-v2\backend.log -Tail 50

# Test manually
cd C:\inetpub\wwwroot\ROMS\backend-v2
.\venv\Scripts\activate
python main.py
# Check error messages
```

### Webhooks Not Receiving

1. **Check firewall:**
   ```powershell
   netsh advfirewall firewall show rule name=all | findstr 80
   ```

2. **Test from external:**
   ```bash
   curl -I https://yourdomain.com/health
   ```

3. **Check IIS/Nginx logs**

### SSL Certificate Issues

```powershell
# Verify certificate binding
netsh http show sslcert

# Re-run win-acme if Let's Encrypt
wacs.exe --renew
```

---

## 📈 Performance Tuning

### For High-Volume Webhooks

**Increase worker pool** in `backend-v2/main.py`:
```python
webhook_queue = WebhookQueue(
    max_workers=20,  # Increase from 10
    max_queue_size=50000  # Increase from 10000
)
```

**Add load balancer** (multiple backend instances):
```nginx
upstream backend {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}
```

---

## 🎯 Final Production Webhook URL

```
https://yourdomain.com/api/v2/webhooks/orders
```

Use this URL in Refract for production! 🚀

---

## 📞 Quick Reference

| Component | Location |
|---|---|
| Backend Code | `C:\inetpub\wwwroot\ROMS\backend-v2` |
| Database | `C:\inetpub\wwwroot\ROMS\backend-v2\roms_v2.db` |
| Logs | `C:\inetpub\wwwroot\ROMS\backend-v2\backend.log` |
| Service | ROMS-V2-Backend (Windows Service) |
| Webhook URL | `https://yourdomain.com/api/v2/webhooks/orders` |
| API Docs | `https://yourdomain.com/docs` |
| Frontend | `https://yourdomain.com` |

---

## ✅ Next Steps

1. ✅ Complete Windows Server setup
2. ✅ Configure DNS
3. ✅ Install SSL certificate
4. ✅ Test webhook endpoint
5. ✅ Update Refract with production URL
6. ✅ Monitor first real webhooks
7. ✅ Set up automated backups

---

**Need help with any step? Just ask!** 🚀

