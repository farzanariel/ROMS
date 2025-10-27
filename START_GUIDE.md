./sart# 🚀 Quick Start Guide

## How to Start Your Dashboard Every Time

### Option 1: Start Everything (Recommended)
```bash
./start.sh
```
This will:
- ✅ Start both backend (port 8000) and frontend (port 3000)
- ✅ Auto-install dependencies if needed
- ✅ Test connections before starting frontend
- ✅ Give you a complete dashboard experience

### Option 2: Start Backend Only (for testing)
```bash
./start-backend.sh
```
This will:
- ✅ Start only the FastAPI backend on port 8000
- ✅ Show detailed logs for debugging
- ✅ Perfect for testing Google Sheets connection

### Option 3: Manual Start (if scripts don't work)
```bash
# Terminal 1 - Backend
cd backend
source ../venv/bin/activate
python3 main.py

# Terminal 2 - Frontend
cd frontend
npm run dev
```

## 📋 What You'll See

### When Starting Successfully:
```
🚀 Starting Order Management Dashboard...
✅ Virtual environment found
🔧 Starting FastAPI backend...
⏳ Waiting for backend to start...
🔍 Testing backend connection...
✅ Backend is running
🎨 Starting React frontend...

🎉 Dashboard is ready!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Frontend: http://localhost:3000
🔧 Backend API: http://localhost:8000
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### If Something Goes Wrong:
- ❌ **"Backend failed to start"** → Check your `credentials.json` file
- ❌ **"Permission denied"** → Run `chmod +x start.sh`
- ❌ **"Virtual environment not found"** → Script will create it automatically

## 🔧 Troubleshooting

### No Data Showing?
1. Check your Google Sheets URL in settings
2. Verify your `credentials.json` is in the `backend/` folder
3. Check backend logs for errors

### Backend Won't Start?
```bash
# Check if ports are busy
lsof -i :8000
lsof -i :3000

# Kill existing processes
pkill -f "python3 main.py"
pkill -f "npm run dev"
```

### Cache Issues?
```bash
# Clear cache via API
curl -X POST "http://localhost:8000/api/cache/clear"

# Or restart the server
```

## 🎯 Quick Access

- 📊 **Dashboard**: http://localhost:3000
- ⏳ **Pending Orders**: http://localhost:3000/pending  
- 📋 **All Orders**: http://localhost:3000/orders
- ⚙️ **Settings**: http://localhost:3000/settings
- 🔧 **Backend Health**: http://localhost:8000/api/health

## 💡 Pro Tips

1. **Bookmark** http://localhost:3000 for quick access
2. **Keep terminal open** to see real-time logs
3. **Use Ctrl+C** to stop all servers cleanly
4. **Data syncs every 2 minutes** automatically
5. **Changes in Google Sheets** appear in dashboard instantly

## 🆘 Need Help?

If you see this error pattern:
```
INFO:main:🚀 Starting Order Management Dashboard...
INFO:main:✅ Google Sheets connection verified
```

But no data loads, try the debug endpoint:
```bash
curl "http://localhost:8000/api/debug/test-connection?sheet_url=YOUR_SHEET_URL"
```
