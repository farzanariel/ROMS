# ROMS V2 Frontend

Real-time order management system frontend for V2 (SQLite + WebSocket).

## Features

- 📊 **Live Orders View** - Real-time updates via WebSocket
- 🔍 **Search & Filter** - Search by order number, product, email
- 📱 **Responsive Design** - Works on mobile and desktop
- 🎨 **Modern UI** - Clean interface with Tailwind CSS
- ⚡ **Fast** - Powered by Vite and React Query

## Quick Start

### 1. Install Dependencies

```bash
cd frontend-v2
npm install
```

### 2. Start Development Server

```bash
npm run dev
```

The frontend will start on **http://localhost:3001**

### 3. Make Sure Backend V2 is Running

```bash
cd ../backend-v2
source venv/bin/activate
python main.py
```

Backend should be running on **http://localhost:8001**

## What You'll See

### All Orders View
- **Real-time table** of all orders from the database
- **Live indicator** showing WebSocket connection status
- **Search bar** for filtering orders
- **Status filter** dropdown
- **Pagination** for large datasets
- **Auto-refresh** when new orders arrive via webhook

## How It Works

```
Refract Webhook
      ↓
V2 Backend (port 8001)
      ↓
SQLite Database
      ↓
WebSocket Broadcast
      ↓
Frontend (port 3001) ← You are here!
```

1. **Refract** sends webhook when order is placed
2. **Backend** parses and stores in SQLite
3. **Backend** broadcasts via WebSocket
4. **Frontend** receives update and refreshes table
5. **You see** the order instantly!

## Environment Variables

Create `.env` file in `frontend-v2/`:

```env
VITE_API_URL=http://localhost:8001
VITE_WS_URL=ws://localhost:8001/ws
```

## Building for Production

```bash
npm run build
```

Output will be in `dist/` directory.

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **Tailwind CSS** - Styling
- **React Query** - Data fetching and caching
- **Heroicons** - Icons

## Project Structure

```
frontend-v2/
├── src/
│   ├── pages/
│   │   └── AllOrders.tsx    # Main orders page
│   ├── services/
│   │   └── api.ts           # API calls to V2 backend
│   ├── hooks/
│   │   └── useWebSocket.ts  # WebSocket connection
│   ├── App.tsx              # Root component
│   └── main.tsx             # Entry point
├── package.json
├── vite.config.ts
└── tailwind.config.js
```

## Ports

- **Frontend**: 3001
- **Backend V2**: 8001
- **Backend V1**: 8000 (runs separately)

## Features Roadmap

- [x] View all orders
- [x] Real-time WebSocket updates
- [x] Search and filter
- [x] Pagination
- [ ] Order details modal
- [ ] Edit order inline
- [ ] Export to CSV
- [ ] Advanced filtering
- [ ] Dashboard with charts
- [ ] Mobile app view

## Troubleshooting

### "Cannot connect to backend"
- Make sure backend-v2 is running: `cd backend-v2 && python main.py`
- Check backend is on port 8001: `curl http://localhost:8001/health`

### "WebSocket disconnected"
- Backend needs to be running
- Check console for WebSocket errors
- Frontend will auto-reconnect

### "No orders showing"
- Send a test webhook to populate database
- Check backend logs: `cd backend-v2 && tail -f backend.log`
- Verify database has orders: `sqlite3 backend-v2/roms_v2.db "SELECT COUNT(*) FROM orders;"`

## Development

```bash
# Run dev server with hot reload
npm run dev

# Type check
npm run lint

# Build for production
npm run build

# Preview production build
npm run preview
```

## Contributing

This is V2 of ROMS - built from scratch for automation!

---

**🚀 Enjoy your automated order management!**

