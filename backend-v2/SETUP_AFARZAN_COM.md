# 🚀 Production Setup for afarzan.com

**Your Configuration:**
- Domain: `afarzan.com`
- Subdomain: `api.afarzan.com` (recommended)
- Server: Windows 11 Server
- DNS: IONOS

**Final Webhook URL:** `https://api.afarzan.com/api/v2/webhooks/orders`

---

## 📋 Complete Setup Checklist

### Phase 1: Find Your Server's Public IP (5 minutes)

**On your Windows Server, open PowerShell and run:**

```powershell
# Get your public IP address
Invoke-RestMethod -Uri "https://api.ipify.org?format=text"
```

**Write down this IP address:** `___.___.___.___`

---

### Phase 2: Configure IONOS DNS (10 minutes)

**1. Log in to IONOS:**
- Go to: https://www.ionos.com/
- Log in to your account
- Navigate to **Domains & SSL** → Click on `afarzan.com`

**2. Go to DNS Settings:**
- Click **DNS Settings** or **Manage DNS**
- You'll see a list of DNS records

**3. Add A Record for API Subdomain:**

Click **Add Record** and enter:

```
Type: A
Hostname: api
Points to: [Your Server IP from Phase 1]
TTL: 3600 (1 hour)
```

**Example:**
```
A    api    123.45.67.89    3600
```

**4. Save Changes**

**5. Wait for DNS Propagation:**
- Takes 5-30 minutes
- Check status at: https://dnschecker.org (enter `api.afarzan.com`)
- When you see green checkmarks worldwide, you're ready!

**Optional - Add www subdomain:**
```
Type: CNAME
Hostname: www.api
Points to: api.afarzan.com
TTL: 3600
```

---

### Phase 3: Transfer Project to Windows Server (15 minutes)

**On Windows Server, open PowerShell as Administrator:**

```powershell
# Create directory (we'll use C:\ROMS for now - simple path)
New-Item -ItemType Directory -Path "C:\ROMS\backend-v2" -Force
cd C:\ROMS
```

**Option A: Manual Transfer (Recommended)**

1. On your Mac, create a zip:
   ```bash
   cd /Users/farzan/Documents/Projects/ROMS
   zip -r backend-v2.zip backend-v2/
   ```

2. Transfer `backend-v2.zip` to Windows Server via:
   - Remote Desktop (copy/paste the zip file)
   - OneDrive/Dropbox
   - USB drive
   - Network share

3. On Windows Server, extract:
   ```powershell
   # Extract to C:\ROMS\
   Expand-Archive -Path "C:\Users\[YourUsername]\Downloads\backend-v2.zip" -DestinationPath "C:\ROMS\"
   ```

**Option B: Using Git (if available)**

```powershell
cd C:\ROMS
git clone [YOUR_REPO_URL] backend-v2
```

**Verify files are there:**
```powershell
dir C:\ROMS\backend-v2
# Should see: main.py, requirements.txt, database/, api/, etc.
```

**Note:** Later when we install IIS, it will create `C:\inetpub\wwwroot\`, but for now we're using the simpler `C:\ROMS\` path.

---

### Phase 4: Run Automated Setup Script (5 minutes)

**On Windows Server (as Administrator):**

```powershell
cd C:\ROMS\backend-v2

# Run setup script
powershell -ExecutionPolicy Bypass -File setup_windows.ps1
```

This will:
- ✅ Check Python installation
- ✅ Create virtual environment
- ✅ Install dependencies
- ✅ Create .env file
- ✅ Test backend
- ✅ Check IIS

**If setup script succeeds, proceed to Phase 5!**

---

### Phase 5: Configure Environment File (5 minutes)

**Edit the .env file:**

```powershell
notepad C:\ROMS\backend-v2\.env
```

**Update these lines:**

```env
# Change from template
CORS_ORIGINS=https://api.afarzan.com,https://afarzan.com

# Generate strong secret keys (use random strings)
SECRET_KEY=afarzan-super-secret-key-change-this-to-random-string-12345
WEBHOOK_SECRET=webhook-secret-key-also-change-this-to-random-67890

# Update webhook base URL
WEBHOOK_BASE_URL=https://api.afarzan.com/api/v2/webhooks
```

**Save and close**

**To generate secure random keys:**
```powershell
# Generate 32-character random string
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

---

### Phase 6: Test Backend Locally (2 minutes)

```powershell
cd C:\ROMS\backend-v2
.\venv\Scripts\Activate.ps1
python main.py
```

**You should see:**
```
🚀 Starting ROMS V2 Backend...
✅ Database initialized successfully
⚡ Webhook queue started with 10 workers
✅ ROMS V2 Backend is ready!
📡 API running on http://0.0.0.0:8001
```

**Open browser on server:**
- Visit: `http://localhost:8001/health`
- Should see: `{"status":"healthy",...}`

**Press Ctrl+C to stop** (we'll run as service next)

---

### Phase 7: Install IIS and Configure Reverse Proxy (20 minutes)

**A. Enable IIS:**

```powershell
# Install IIS with WebSocket support
Install-WindowsFeature -name Web-Server -IncludeManagementTools
Install-WindowsFeature -name Web-WebSockets
```

**Or via GUI:**
1. Open **Settings** → **Apps** → **Optional Features**
2. Click **More Windows features**
3. Check **Internet Information Services**
4. Expand and check **WebSocket Protocol**
5. Click OK and wait for installation

**B. Install URL Rewrite Module:**

```powershell
# Download and install
$url = "https://download.microsoft.com/download/1/2/8/128E2E22-C1B9-44A4-BE2A-5859ED1D4592/rewrite_amd64_en-US.msi"
$output = "$env:TEMP\urlrewrite.msi"
Invoke-WebRequest -Uri $url -OutFile $output
Start-Process msiexec.exe -ArgumentList "/i $output /quiet" -Wait
```

**C. Install Application Request Routing (ARR):**

```powershell
# Download and install ARR
$url = "https://download.microsoft.com/download/E/9/8/E9849D6A-020E-47E4-9FD0-A023E99B54EB/requestRouter_amd64.msi"
$output = "$env:TEMP\arr.msi"
Invoke-WebRequest -Uri $url -OutFile $output
Start-Process msiexec.exe -ArgumentList "/i $output /quiet" -Wait
```

**D. Configure IIS Manager:**

1. Open **IIS Manager** (search in Start menu)

2. **Enable ARR Proxy:**
   - Click your **server name** (top level in left panel)
   - Double-click **Application Request Routing Cache**
   - Click **Server Proxy Settings** (right panel)
   - Check **✓ Enable proxy**
   - Click **Apply**

3. **Create Website:**
   - Right-click **Sites** → **Add Website**
   - **Site name:** `ROMS-V2-API`
   - **Physical path:** `C:\ROMS\backend-v2`
   - **Binding:**
     - Type: `http`
     - IP: `All Unassigned`
     - Port: `80`
     - Host name: `api.afarzan.com`
   - Click **OK**

4. **Add URL Rewrite Rule:**
   - Click your new site **ROMS-V2-API** in left panel
   - Double-click **URL Rewrite**
   - Click **Add Rule(s)** → **Reverse Proxy**
   - If prompted to enable proxy, click **OK**
   - Enter: `127.0.0.1:8001`
   - Click **OK**

**E. Configure Firewall:**

```powershell
# Allow HTTP (port 80)
New-NetFirewallRule -DisplayName "HTTP (Port 80)" -Direction Inbound -Protocol TCP -LocalPort 80 -Action Allow

# Allow HTTPS (port 443) - for later SSL
New-NetFirewallRule -DisplayName "HTTPS (Port 443)" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow
```

---

### Phase 8: Install Backend as Windows Service (5 minutes)

**A. Install NSSM:**

```powershell
# Option 1: Using Chocolatey (if installed)
choco install nssm -y

# Option 2: Manual download
# Download from: https://nssm.cc/download
# Extract and place nssm.exe in C:\Windows\System32\
```

**B. Run Service Installation Script:**

```powershell
cd C:\ROMS\backend-v2
powershell -ExecutionPolicy Bypass -File install_service.ps1
```

**C. Verify Service:**

```powershell
# Check status
nssm status ROMS-V2-Backend
# Should show: SERVICE_RUNNING

# Test health endpoint
Invoke-RestMethod -Uri "http://localhost:8001/health"
```

---

### Phase 9: Install SSL Certificate (15 minutes)

**Using win-acme (Let's Encrypt - FREE):**

**A. Install win-acme:**

```powershell
# Using Chocolatey
choco install win-acme -y

# Or download from: https://www.win-acme.com/
```

**B. Run win-acme:**

```powershell
wacs.exe
```

**C. Follow prompts:**
1. Choose: `N - Create certificate with advanced options`
2. Choose: `2 - Manual input`
3. Enter host: `api.afarzan.com`
4. Choose: `1 - [http-01] Save validation files on (network) path`
5. Enter path: `C:\ROMS\backend-v2`
6. Choose: `2 - IIS Web Site`
7. Select your site: `ROMS-V2-API`
8. Follow remaining prompts (defaults are usually fine)

**D. win-acme will:**
- ✅ Generate SSL certificate
- ✅ Install it in Windows certificate store
- ✅ Bind it to your IIS site
- ✅ Set up auto-renewal

**E. Update IIS Binding:**
- Open IIS Manager
- Click your site **ROMS-V2-API**
- Click **Bindings** (right panel)
- Click **Add**
  - Type: `https`
  - IP: `All Unassigned`
  - Port: `443`
  - Host name: `api.afarzan.com`
  - SSL certificate: Select the certificate created by win-acme
- Click **OK**

**F. Add HTTPS Redirect (Optional but recommended):**
- In IIS Manager, click your site
- Double-click **URL Rewrite**
- Click **Add Rule** → **Blank Rule**
- Name: `Redirect to HTTPS`
- Match URL: `(.*)`
- Conditions: Add condition
  - Input: `{HTTPS}`
  - Pattern: `^OFF$`
- Action type: `Redirect`
- Redirect URL: `https://api.afarzan.com/{R:1}`
- Redirect type: `Permanent (301)`
- Click **Apply**

---

### Phase 10: Test Your Production Setup! (5 minutes)

**A. Test from Windows Server:**

```powershell
# Test HTTP (should redirect to HTTPS)
Invoke-WebRequest -Uri "http://api.afarzan.com/health" -MaximumRedirection 0

# Test HTTPS
Invoke-RestMethod -Uri "https://api.afarzan.com/health"
# Should return: {"status":"healthy",...}
```

**B. Test from External:**

**On your Mac:**
```bash
# Test health endpoint
curl https://api.afarzan.com/health

# Should return:
# {"status":"healthy","version":"2.0.0",...}
```

**If this works, you're ready for webhooks! 🎉**

---

### Phase 11: Update Refract with Production URL (2 minutes)

**1. Log in to Refract**

**2. Go to Webhook Settings**

**3. Update Checkout Success Webhook URL to:**
```
https://api.afarzan.com/api/v2/webhooks/orders
```

**4. Save Settings**

**5. Send Test Checkout**

**6. Monitor:**

**On Windows Server:**
```powershell
# Watch logs
Get-Content C:\ROMS\backend-v2\backend.log -Tail 20 -Wait

# Check queue stats
Invoke-RestMethod -Uri "https://api.afarzan.com/api/v2/webhooks/queue/stats"

# Check recent orders
Invoke-RestMethod -Uri "https://api.afarzan.com/api/v2/orders?page=1&page_size=5"
```

**On your Mac - Frontend:**
- Visit: `http://localhost:3001`
- Update frontend `.env`:
  ```
  VITE_API_BASE_URL=https://api.afarzan.com
  VITE_WS_URL=wss://api.afarzan.com/ws
  ```
- New orders should appear automatically!

---

## 🎉 You're Live!

**Your Production URLs:**

| Endpoint | URL |
|---|---|
| **Webhook** (for Refract) | `https://api.afarzan.com/api/v2/webhooks/orders` |
| Health Check | `https://api.afarzan.com/health` |
| API Docs | `https://api.afarzan.com/docs` |
| Queue Stats | `https://api.afarzan.com/api/v2/webhooks/queue/stats` |
| Orders API | `https://api.afarzan.com/api/v2/orders` |
| WebSocket | `wss://api.afarzan.com/ws` |

---

## 🔧 Useful Management Commands

**Service Management:**
```powershell
# Check status
nssm status ROMS-V2-Backend

# Restart service
nssm restart ROMS-V2-Backend

# Stop service
nssm stop ROMS-V2-Backend

# Start service
nssm start ROMS-V2-Backend
```

**View Logs:**
```powershell
# Application logs
Get-Content C:\ROMS\backend-v2\backend.log -Tail 50

# Service logs
Get-Content C:\ROMS\backend-v2\logs\service-output.log -Tail 50
Get-Content C:\ROMS\backend-v2\logs\service-error.log -Tail 50
```

**Test Endpoints:**
```powershell
# Health check
Invoke-RestMethod -Uri "https://api.afarzan.com/health"

# Queue stats
Invoke-RestMethod -Uri "https://api.afarzan.com/api/v2/webhooks/queue/stats"

# Recent orders
Invoke-RestMethod -Uri "https://api.afarzan.com/api/v2/orders" | ConvertTo-Json -Depth 10
```

**Update Code:**
```powershell
# Stop service
nssm stop ROMS-V2-Backend

# Update code
cd C:\ROMS\backend-v2
git pull  # or copy new files

# Update dependencies
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt --upgrade

# Restart service
nssm start ROMS-V2-Backend
```

---

## 🆘 Troubleshooting

### DNS not resolving
```powershell
# Check DNS propagation
nslookup api.afarzan.com

# If not working, wait 15-30 minutes after IONOS DNS update
```

### Backend not starting
```powershell
# Check logs
Get-Content C:\ROMS\backend-v2\backend.log -Tail 100

# Test manually
cd C:\ROMS\backend-v2
.\venv\Scripts\Activate.ps1
python main.py
# Check for errors
```

### SSL certificate issues
```powershell
# Re-run win-acme
wacs.exe --renew

# Check certificate binding in IIS Manager
```

### Webhooks not receiving
```powershell
# Test from external
curl -X POST https://api.afarzan.com/api/v2/webhooks/orders -H "Content-Type: application/json" -d '{"test":"data"}'

# Check firewall
Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*HTTP*"}

# Check IIS site is running
Get-Website
```

---

## 📊 Monitoring

**Set up monitoring (optional):**

**A. Enable detailed logging in .env:**
```env
LOG_LEVEL=DEBUG
```

**B. Create scheduled task for log rotation:**
```powershell
# Create a task to archive logs weekly
# (Prevents log files from getting too large)
```

**C. Monitor queue health:**
```powershell
# Add to Task Scheduler to run every 5 minutes
Invoke-RestMethod -Uri "https://api.afarzan.com/api/v2/webhooks/queue/stats"
```

---

## ✅ Setup Complete!

**Summary:**
- ✅ Domain: `api.afarzan.com`
- ✅ SSL: Enabled (HTTPS)
- ✅ Backend: Running as Windows service
- ✅ IIS: Configured as reverse proxy
- ✅ Webhook URL: `https://api.afarzan.com/api/v2/webhooks/orders`
- ✅ Auto-start: Enabled (starts with Windows)

**Ready for production webhooks! 🚀**

