# 🎉 START HERE - ROMS V2 Complete Setup

## ✅ Everything is Ready!

Your complete ROMS V2 system is built and ready to use!

---

## 🚀 Start Everything (One Command!)

```bash
cd /Users/farzan/Documents/Projects/ROMS
./start-v2-full.sh
```

This starts:
- ✅ Backend V2 (port 8001)
- ✅ Frontend V2 (port 3001)
- ✅ WebSocket server
- ✅ SQLite database

Then open: **http://localhost:3001** to see your orders!

---

## 🎯 What You Have

### 1. **Backend V2** (`backend-v2/`)
- ✅ FastAPI server on port 8001
- ✅ SQLite database (`roms_v2.db`)
- ✅ Webhook receiver for Refract
- ✅ Orders API with pagination
- ✅ WebSocket for real-time updates
- ✅ Discord embed parser
- ✅ Automatic order parsing

### 2. **Frontend V2** (`frontend-v2/`)
- ✅ React + TypeScript app on port 3001
- ✅ Real-time orders table
- ✅ Search and filter orders
- ✅ Live WebSocket updates
- ✅ Beautiful modern UI
- ✅ Responsive design

### 3. **Complete Documentation**
- ✅ `V2_FRONTEND_SETUP.md` - Frontend guide
- ✅ `REFRACT_FINAL_SETUP.md` - Webhook setup
- ✅ `FIELD_MAPPING.md` - Data mapping details
- ✅ `V2_ARCHITECTURE.md` - System architecture

---

## 📊 The Flow

```
Refract Webhook
      ↓
http://localhost:8001/api/v2/webhooks/orders
      ↓
Parse Discord Embed
      ↓
Store in SQLite Database
      ↓
Broadcast via WebSocket
      ↓
Frontend Updates Automatically
      ↓
You See Orders Instantly! ⚡
```

---

## 🧪 Test It Right Now!

### Option 1: Automated Test
```bash
cd backend-v2
python test_discord_embed.py
```

### Option 2: Manual Test
```bash
curl -X POST http://localhost:8001/api/v2/webhooks/orders \
  -H "Content-Type: application/json" \
  -d '{
    "embeds": [{
      "author": {"name": "Successful Checkout | Best Buy"},
      "description": "Product\nTest Product\nPrice\n$99.99\nOrder Number\nTEST-123\nEmail\ntest@example.com\nProfile\nProfile1\nProxy Details\nProxy1"
    }]
  }'
```

Then check:
- **Frontend**: http://localhost:3001 (see order in table)
- **API**: http://localhost:8001/api/v2/orders (JSON response)
- **Database**: `cd backend-v2 && sqlite3 roms_v2.db "SELECT * FROM orders;"`

---

## ⚙️ Configure Refract

### Your Webhook URL:
```
http://localhost:8001/api/v2/webhooks/orders
```

### For Production (use ngrok):
```bash
ngrok http 8001
# Use: https://abc123.ngrok.io/api/v2/webhooks/orders
```

### In Refract Settings:
1. Go to **Webhooks** → **Add Webhook**
2. URL: Your webhook URL (localhost or ngrok)
3. Enable: **"Successful Checkout"** event
4. Save
5. ⚠️ Ignore "Test Notification" errors (expected)
6. ✅ Real orders will work perfectly!

---

## 📁 What Got Created

```
ROMS/
├── backend-v2/              ← V2 Backend (NEW!)
│   ├── main.py             ← FastAPI app
│   ├── database/
│   │   ├── models.py       ← SQLite schema
│   │   ├── schemas.py      ← Data validation
│   │   └── database.py     ← DB connection
│   ├── api/
│   │   ├── webhooks.py     ← Webhook endpoints
│   │   └── orders.py       ← Orders API (NEW!)
│   ├── services/
│   │   ├── webhook_parser.py     ← Discord embed parser
│   │   └── order_processor.py   ← Order logic
│   ├── test_discord_embed.py    ← Test script
│   ├── requirements.txt
│   ├── roms_v2.db          ← SQLite database
│   └── README.md
│
├── frontend-v2/             ← V2 Frontend (NEW!)
│   ├── src/
│   │   ├── pages/
│   │   │   └── AllOrders.tsx    ← Main orders page
│   │   ├── services/
│   │   │   └── api.ts          ← API client
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts  ← WebSocket hook
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── .env
│   └── README.md
│
├── start-v2-full.sh         ← ONE-COMMAND STARTUP!
├── V2_FRONTEND_SETUP.md     ← Frontend guide
├── REFRACT_FINAL_SETUP.md   ← Webhook guide
├── V2_ARCHITECTURE.md       ← Architecture
└── START_HERE_V2.md         ← This file!
```

---

## 🌐 URLs & Ports

| Service | URL | Port |
|---|---|---|
| **Frontend V2** | http://localhost:3001 | 3001 |
| **Backend V2 API** | http://localhost:8001 | 8001 |
| **API Docs** | http://localhost:8001/docs | 8001 |
| **WebSocket** | ws://localhost:8001/ws | 8001 |
| **Webhook Endpoint** | http://localhost:8001/api/v2/webhooks/orders | 8001 |
| **V1 Frontend** | http://localhost:3000 | 3000 |
| **V1 Backend** | http://localhost:8000 | 8000 |

---

## 🎨 Frontend Features

✅ **Real-Time Table** - Orders appear instantly
✅ **Search** - Find orders by number, product, email
✅ **Filter by Status** - Pending, Verified, Shipped, etc.
✅ **Pagination** - Handle thousands of orders
✅ **Live Indicator** - Shows WebSocket connection
✅ **Auto-Refresh** - Updates when new orders arrive
✅ **Responsive** - Works on desktop and mobile
✅ **Beautiful UI** - Modern design with Tailwind CSS

---

## 🔧 Useful Commands

### Start Everything
```bash
./start-v2-full.sh
```

### Backend Only
```bash
cd backend-v2
source venv/bin/activate
python main.py
```

### Frontend Only
```bash
cd frontend-v2
npm run dev
```

### View Database
```bash
cd backend-v2
sqlite3 roms_v2.db
SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;
.exit
```

### View Logs
```bash
# Backend logs
tail -f backend-v2/backend.log

# Frontend logs
tail -f frontend-v2/frontend.log

# Webhook logs API
curl http://localhost:8001/api/v2/webhooks/logs
```

### Test Webhook
```bash
cd backend-v2
python test_discord_embed.py
```

---

## 🐛 Troubleshooting

### "Cannot connect to backend"
```bash
# Check if backend is running
curl http://localhost:8001/health

# If not, start it
cd backend-v2
source venv/bin/activate
python main.py
```

### "No orders showing"
```bash
# Check database
cd backend-v2
sqlite3 roms_v2.db "SELECT COUNT(*) FROM orders;"

# Send test order
python test_discord_embed.py
```

### "WebSocket disconnected"
- Backend needs to be running
- Frontend will auto-reconnect
- Check browser console for errors

### "Port already in use"
```bash
# Kill processes and restart
lsof -ti:8001 | xargs kill -9
lsof -ti:3001 | xargs kill -9
./start-v2-full.sh
```

---

## 📚 Read More

- **Frontend Setup**: `V2_FRONTEND_SETUP.md`
- **Webhook Guide**: `REFRACT_FINAL_SETUP.md`
- **Field Mapping**: `FIELD_MAPPING.md`
- **Architecture**: `V2_ARCHITECTURE.md`
- **Backend README**: `backend-v2/README.md`
- **Frontend README**: `frontend-v2/README.md`

---

## ✅ Quick Checklist

- [ ] Run `./start-v2-full.sh`
- [ ] Open http://localhost:3001
- [ ] Send test webhook: `cd backend-v2 && python test_discord_embed.py`
- [ ] See order appear in frontend
- [ ] Configure Refract with webhook URL
- [ ] Make real purchase
- [ ] Watch orders flow in automatically!

---

## 🎉 You're Done!

Everything is ready! Just run:

```bash
./start-v2-full.sh
```

Then open: **http://localhost:3001**

Your automated order management system is live! 🚀

---

**Questions? Check the docs or the code - everything is documented!**

