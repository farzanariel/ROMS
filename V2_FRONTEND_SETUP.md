# ROMS V2 Frontend - Setup Complete! 🎉

## ✅ What I've Built For You

A complete **real-time frontend** for ROMS V2 that shows live orders from your SQLite database!

### 🎯 Features

- ✅ **Live Orders Table** - See all orders in real-time
- ✅ **WebSocket Integration** - Instant updates when new orders arrive
- ✅ **Search & Filter** - Find orders by number, product, or email
- ✅ **Status Filtering** - Filter by Pending, Verified, Shipped, etc.
- ✅ **Pagination** - Handle thousands of orders efficiently
- ✅ **Responsive Design** - Works on desktop and mobile
- ✅ **Beautiful UI** - Modern design with Tailwind CSS
- ✅ **Auto-Refresh** - Table updates when Refract sends webhooks

---

## 🚀 Quick Start (One Command!)

```bash
cd /Users/farzan/Documents/Projects/ROMS
./start-v2-full.sh
```

This will:
1. ✅ Start Backend V2 on port 8001
2. ✅ Start Frontend V2 on port 3001
3. ✅ Install frontend dependencies if needed
4. ✅ Open everything ready to use!

Then open: **http://localhost:3001**

---

## 🎨 What You'll See

### Main View
```
╔════════════════════════════════════════════════════╗
║  All Orders                        🔄 Refresh      ║
║  Real-time view of all orders from webhooks        ║
║  1 total orders  ● Live                            ║
╠════════════════════════════════════════════════════╣
║  🔍 Search by order number, product, email...      ║
║  Status: [All Statuses ▼]                          ║
╠════════════════════════════════════════════════════╣
║  Order #  │ Product  │ Price │ Email │ Status │.. ║
║───────────┼──────────┼───────┼───────┼────────┼───║
║  BBY01... │ STARLINK │$299.99│woozy..│VERIFIED│.. ║
║  ...                                                ║
╚════════════════════════════════════════════════════╝
```

### Live Indicators
- 🟢 **Green dot** = Connected to WebSocket, receiving live updates
- 🔴 **Gray dot** = Disconnected, will auto-reconnect

---

## 📦 Project Structure

```
frontend-v2/
├── src/
│   ├── pages/
│   │   └── AllOrders.tsx       # 📊 Main orders page (copied from V1)
│   ├── services/
│   │   └── api.ts              # 📡 API calls to V2 backend
│   ├── hooks/
│   │   └── useWebSocket.ts     # 🔌 WebSocket connection
│   ├── App.tsx                 # Root component
│   └── main.tsx                # Entry point
├── package.json                # Dependencies
├── vite.config.ts              # Vite config (port 3001)
├── tailwind.config.js          # Tailwind CSS
├── .env                        # Environment variables
└── README.md                   # Documentation
```

---

## 🔧 Manual Setup (If Needed)

### 1. Install Frontend Dependencies
```bash
cd frontend-v2
npm install
```

### 2. Start Backend V2
```bash
cd backend-v2
source venv/bin/activate
python main.py
```
Backend runs on **http://localhost:8001**

### 3. Start Frontend V2
```bash
cd frontend-v2
npm run dev
```
Frontend runs on **http://localhost:3001**

---

## 🧪 How to Test Real-Time Updates

### Option 1: Send Test Webhook
```bash
cd backend-v2
python test_discord_embed.py
```

### Option 2: Use Real Refract Webhook
1. Configure Refract with: `http://localhost:8001/api/v2/webhooks/orders`
2. Make a test purchase
3. Watch order appear instantly in frontend! ⚡

### Option 3: Use curl
```bash
curl -X POST http://localhost:8001/api/v2/webhooks/orders \
  -H "Content-Type: application/json" \
  -d '{
    "embeds": [{
      "author": {"name": "Successful Checkout | Test Store"},
      "description": "Product\nTest Product\nPrice\n$99.99\nOrder Number\nTEST-123\nEmail\ntest@example.com"
    }]
  }'
```

Then refresh the frontend and you'll see the new order!

---

## 🎯 Key Differences from V1

| Feature | V1 | V2 |
|---|---|---|
| **Data Source** | Google Sheets | SQLite Database |
| **Data Entry** | Manual/Actions page | Automatic via Webhooks |
| **Backend** | Port 8000 | Port 8001 |
| **Frontend** | Port 3000 | Port 3001 |
| **Real-time** | WebSocket to Sheets | WebSocket to Database |
| **Speed** | Slower (API limits) | Instant (local DB) |
| **Offline** | Requires internet | Works offline |

---

## 📊 API Endpoints Available

### Orders API
```bash
# Get all orders (paginated)
GET http://localhost:8001/api/v2/orders?page=1&page_size=100

# Search orders
GET http://localhost:8001/api/v2/orders?search=BBY01

# Filter by status
GET http://localhost:8001/api/v2/orders?status=VERIFIED

# Get single order
GET http://localhost:8001/api/v2/orders/1
```

### Webhooks API
```bash
# Receive webhook (Refract sends here)
POST http://localhost:8001/api/v2/webhooks/orders

# View webhook logs
GET http://localhost:8001/api/v2/webhooks/logs

# Test webhook endpoint
GET http://localhost:8001/api/v2/webhooks/test
```

### Health Check
```bash
GET http://localhost:8001/health
```

---

## 🔌 WebSocket Messages

The frontend automatically subscribes to WebSocket updates:

```javascript
// When new order arrives via webhook:
{
  "type": "new_order",
  "order": {
    "id": 1,
    "order_number": "BBY01-123",
    "product": "Product Name",
    "price": 299.99,
    "status": "verified",
    "created_at": "2025-10-27T..."
  }
}
```

Frontend automatically refetches the order list when this is received!

---

## 🐛 Troubleshooting

### Frontend shows "No orders found"
**Solution:**
- Make sure backend has orders: `curl http://localhost:8001/api/v2/orders`
- Check database: `cd backend-v2 && sqlite3 roms_v2.db "SELECT COUNT(*) FROM orders;"`
- Send a test webhook to populate data

### "Connection failed" / WebSocket not connected
**Solution:**
- Backend must be running on port 8001
- Check: `curl http://localhost:8001/health`
- Restart backend: `cd backend-v2 && python main.py`
- Frontend will auto-reconnect once backend is up

### Frontend won't start / Port 3001 in use
**Solution:**
```bash
lsof -ti:3001 | xargs kill -9
cd frontend-v2
npm run dev
```

### "Cannot find module" errors
**Solution:**
```bash
cd frontend-v2
rm -rf node_modules package-lock.json
npm install
```

---

## 🎨 Customization

### Change Ports

**Frontend** (in `vite.config.ts`):
```typescript
server: {
  port: 3001, // Change this
}
```

**Backend** (in `backend-v2/.env`):
```
API_V2_HOST=0.0.0.0
API_V2_PORT=8001  # Change this
```

### Add More Columns

Edit `frontend-v2/src/pages/AllOrders.tsx`:
```tsx
<th>Your New Column</th>
// ...
<td>{order.your_field}</td>
```

---

## 📚 Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Lightning-fast builds
- **Tailwind CSS** - Utility-first CSS
- **React Query** - Data fetching & caching
- **WebSocket API** - Real-time updates
- **Heroicons** - Beautiful icons

---

## 🚀 Production Deployment

### Build Frontend
```bash
cd frontend-v2
npm run build
```

Output in `dist/` folder. Deploy to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- Your own server

### Update API URL
For production, update `frontend-v2/.env`:
```env
VITE_API_URL=https://your-api-domain.com
VITE_WS_URL=wss://your-api-domain.com/ws
```

---

## ✅ What's Working Right Now

✅ Backend V2 running on port 8001
✅ Orders API endpoint responding
✅ WebSocket server ready
✅ Test order in database
✅ Frontend code ready to start

---

## 🎉 You're All Set!

### Start Everything:
```bash
cd /Users/farzan/Documents/Projects/ROMS
./start-v2-full.sh
```

### Then Open:
**http://localhost:3001**

You'll see your orders in real-time!

### Send Test Order:
```bash
cd backend-v2
python test_discord_embed.py
```

Watch it appear instantly! ⚡

---

## 📝 Next Steps

1. ✅ Start the frontend: `./start-v2-full.sh`
2. ✅ Open http://localhost:3001
3. ✅ Configure Refract with webhook URL
4. ✅ Make a test purchase
5. ✅ Watch orders flow in real-time!

**Your automated order management system is ready! 🚀**

